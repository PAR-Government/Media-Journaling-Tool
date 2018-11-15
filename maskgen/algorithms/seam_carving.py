import numpy as np
from maskgen import cv2api, tool_set, image_wrap
import cv2
try:
    from numba import jit
except:
    def jit(original_function):
        return original_function


maxdisplacementvalue = np.iinfo(np.uint16).max

def _image_rotate( image, direction=0):
    if direction > 0:
        return np.rot90(image, 1)
    else:
        return np.rot90(image, 3)

def base_energy_function(base_energy,i,j,quad):
    return base_energy[i, j]


def foward_base_energy_function(base_energy, i, j, quad):
    if i == 0:
        return base_energy[i,j]
    if quad == 'L':
        if j == base_energy.shape[1] - 1:
            return abs(base_energy[i - 1, j] - base_energy[i, j - 1])
        return abs(base_energy[i, j + 1] - base_energy[i, j - 1]) + abs(base_energy[i - 1, j] - base_energy[i, j - 1])
    elif quad == 'R':
        if j == 0:
            return abs(base_energy[i - 1, j] - base_energy[i, j + 1])
        return abs(base_energy[i, j + 1] - base_energy[i, j - 1]) + abs(base_energy[i - 1, j] - base_energy[i, j + 1])
    else:
        if j== 0:
            return abs(base_energy[i, j + 1] - base_energy[i, j]) + abs(base_energy[i-1, j] - base_energy[i, j])
        elif j == base_energy.shape[1] - 1:
            return abs(base_energy[i-1, j] - base_energy[i, j])
        return abs(base_energy[i, j + 1] - base_energy[i, j - 1])



def _create_offsets(m):
    u = np.roll(m,  1, axis=0)
    ru = np.roll(u, 1, axis=1)
    ru[:,-1] = 10000000
    lu = np.roll(u, -1, axis=1)
    lu[-1,:] = 10000000
    mu = u
    mu[0,:] = 0
    return lu,mu,ru


def _accumulate_energy_old(base_energy, energy_function=base_energy_function):
    """
    Converts energy values to cumulative energy values
    """
    min_energy = np.copy(base_energy)
    width = base_energy.shape[1]

    for i in range(base_energy.shape[0]):
        for j in range(base_energy.shape[1]):
            if i == 0:
                min_energy[i, j] = energy_function(base_energy,i,j,'R')
            elif j == 0:
                min_energy[i, j] =  min(
                    min_energy[i - 1, j]+ energy_function(base_energy,i,j,'U'),
                    min_energy[i - 1, j + 1] + energy_function(base_energy,i,j,'R'))
            elif j == width - 1:
                min_energy[i, j] = min(
                    min_energy[i - 1, j - 1] + energy_function(base_energy,i,j,'L'),
                    min_energy[i - 1, j] + energy_function(base_energy,i,j,'U'))
            else:
                min_energy[i, j] =  min(
                    min_energy[i - 1, j - 1] + energy_function(base_energy,i,j,'L'),
                    min_energy[i - 1, j] + energy_function(base_energy,i,j,'U'),
                    min_energy[i - 1, j + 1] + energy_function(base_energy,i,j,'R'))
    return min_energy

@jit()
def _accumulate_energy(energy,energy_function=base_energy_function):
    """
    https://en.wikipedia.org/wiki/Seam_carving#Dynamic_programming

    Parameters
    ==========
    energy: 2-D numpy.array(uint8)
        Produced by energy_map

    Returns
    =======
        tuple of 2 2-D numpy.array(int64) with shape (height, width).
        paths has the x-offset of the previous seam element for each pixel.
        path_energies has the cumulative energy at each pixel.
    """
    height, width = energy.shape
    #paths = np.zeros((height, width), dtype=np.int64)
    path_energies = np.zeros((height, width), dtype=np.int64)
    path_energies[0] = energy[0]
    #paths[0] = np.arange(width) * np.nan

    for i in range(1, height):
        for j in range(width):
            # Note that indexing past the right edge of a row, as will happen if j == width-1, will
            # simply return the part of the slice that exists
            prev_energies = path_energies[i-1, max(j-1, 0):j+2]
            least_energy = prev_energies.min()
            path_energies[i][j] = energy[i][j] + least_energy
            #paths[i][j] = np.where(prev_energies == least_energy)[0][0] - (1*(j != 0))
    return  path_energies

def _find_seam_what(paths, end_x):
    """
    Parameters
    ==========
    paths: 2-D numpy.array(int64)
        Output of cumulative_energy_map. Each element of the matrix is the offset of the index to
        the previous pixel in the seam
    end_x: int
        The x-coordinate of the end of the seam

    Returns
    =======
        1-D numpy.array(int64) with length == height of the image
        Each element is the x-coordinate of the pixel to be removed at that y-coordinate. e.g.
        [4,4,3,2] means "remove pixels (0,4), (1,4), (2,3), and (3,2)"
    """
    height, width = paths.shape[:2]
    seam = [end_x]
    for i in range(height-1, 0, -1):
        cur_x = seam[-1]
        offset_of_prev_x = paths[i][cur_x]
        seam.append(cur_x + offset_of_prev_x)
    seam.reverse()
    return seam,sum([paths[r,seam[r]] for r in range(height)])

def _find_seam(cumulative_map, bounds=None):
        m, n = cumulative_map.shape
        output = np.zeros((m,), dtype=np.uint32)
        if bounds is not None:
            output[-1] = np.argmin(cumulative_map[-1,bounds[0]:bounds[1]]) + bounds[0]
        else:
            output[-1] = np.argmin(cumulative_map[-1])
        for row in range(m - 2, -1, -1):
            previous_x = output[row + 1]
            if previous_x == 0:
                output[row] = np.argmin(cumulative_map[row, :2])
            elif cumulative_map[row, previous_x - 1] == cumulative_map[row, previous_x]:
                output[row] = np.argmin(cumulative_map[row, previous_x: previous_x + 2]) + previous_x
            else:
                output[row] = np.argmin(cumulative_map[row, previous_x - 1: previous_x + 2]) + previous_x - 1
        return output, sum([cumulative_map[r,output[r]] for r in range(m)])


def _find_k_seams(cumulative_map, bounds=None):
    bounded_cumulative_map = cumulative_map[:, bounds[0]:bounds[1]] if bounds is not None else cumulative_map
    m, n = bounded_cumulative_map.shape
    output = np.zeros((m,n), dtype=np.int)
    output[-1] = np.argsort(bounded_cumulative_map[-1])
    for row in range(m - 2, -1, -1):
        previous_x = output[row + 1]
        allpositions= [(previous_x - 1).clip(min=0),previous_x, (previous_x + 1).clip(max=(n-1))]
        positionvalues = [ bounded_cumulative_map[row, allpositions[0]],
                         bounded_cumulative_map[row, allpositions[1]],
                         bounded_cumulative_map[row, allpositions[2]]]
        minrow = np.argmin(positionvalues,axis=0)
        output[row] = np.asarray(allpositions)[minrow,np.arange(n)] + (bounds[0] if bounds is not None else 0)
    output = output.transpose()
    diffs = np.diff(output,axis=0)
    return output[np.setdiff1d(np.arange(n), np.where(diffs == 0)[0] + 1),:]


def _remove_seam(images, seam_idx):
    m, n = images[0].shape[: 2]
    outputs = []
    for image in images:
        output =  np.zeros((m, n - 1)+ image.shape[2:]).astype(image.dtype)
        for row in range(m):
            col = seam_idx[row]
            output[row,] = np.delete(image[row, :], col, 0)
        outputs.append(output)
    return outputs


def _add_seam(images_and_value, seam_idx):
    import random
    m, n = images_and_value[0][0].shape[: 2]
    outputs = []
    for image,value in images_and_value:
        output = np.zeros((m, n + 1) + image.shape[2:]).astype(image.dtype)
        for row in range(m):
            col = seam_idx[row]
            if len(image.shape) > 2:
                for channel in range(image.shape[2]):
                    p = np.average(image[row, max(col - 1,0): col + 2, channel]) if value is None else value
                    output[row, : col, channel] = image[row, : col, channel]
                    output[row, col, channel] = min(max(0,p + random.randint(-1,1)),255)
                    output[row, col + 1:, channel] = image[row, col:, channel]
            else:
                if col == 0:
                    p = np.average(image[row, col: col + 2]) if value is None else value
                    output[row,: col] = image[row, :col]
                    output[row, col] = p
                    output[row, col + 1:] = image[row, col:]
                else:
                    p = np.average(image[row, col - 1: col + 1]) if value is None else value
                    output[row, : col] = image[row, : col]
                    output[row, col] = p
                    output[row, col + 1:] = image[row, col:]
        outputs.append(output)
    return outputs

def _seam_end(energy_totals):
    """
    Parameters
    ==========
    energy_totals: 2-D numpy.array(int64)
        Cumulative energy of each pixel in the image

    Returns
    =======
        numpy.int64
        the x-coordinate of the bottom of the seam for the image with these
        cumulative energies
    """
    return list(energy_totals[-1]).index(min(energy_totals[-1]))


class MaskTracker:

    def __init__(self, shape, final_shape=None):
        """

        :param shape: shape of original image
        :param final_shape: shape of final image, if drop_seam() is not used.
        """
        #initially, the shape is the same between the below artifacts, using the drop_seam to alter
        # the shape of neighbors_mask and dropped_adjuster.

        # the mask in the space of the original image highlighting the pixels removed (value of 1)
        self.dropped_mask = np.zeros(shape, dtype=np.uint8)
        # two channel array that describes the mapping row,col of new space into old space
        # for row and column respectively
        self.dropped_adjuster = np.indices(shape if final_shape is None else final_shape)
        # a single channel mask that describes the number of times a pixel has had neighbors
        # removed
        self.neighbors_mask = np.zeros(shape if final_shape is None else final_shape, dtype=np.uint16)
        self.inverter = None

    def rotate(self,direction):
        self.dropped_adjuster = np.asarray([_image_rotate(self.dropped_adjuster[0], direction),
                                            _image_rotate(self.dropped_adjuster[1], direction)])
        self.neighbors_mask = _image_rotate(self.neighbors_mask,direction)

    def move_pixels(self, image):
        type_var = image.dtype
        image = image.astype(np.float32)
        if len(image.shape) == 3:
            output = np.zeros((self.dropped_adjuster[0].shape[0],
                               self.dropped_adjuster[0].shape[1],
                               image.shape[2]), dtype=type_var)
            for channel in range(image.shape[2]):
                self._move_pixels(output[:,:,channel],image[:,:,channel],self.dropped_adjuster)
        else:
            output = np.zeros(self.dropped_adjuster[0].shape, dtype=type_var)
            self._move_pixels(output,image,self.dropped_adjuster)
        output.astype(type_var)
        return output

    def invert_move_pixels(self, image):
        type_var = image.dtype
        image = image.astype(np.float32)
        if len(image.shape) == 3:
            output = np.zeros((self.dropped_mask.shape[0],
                               self.dropped_mask.shape[1],
                               image.shape[2]), dtype=type_var)
            for channel in range(image.shape[2]):
                self._invert_move_pixels(output[:,:,channel],image[:,:,channel])
        else:
            output = np.zeros(self.dropped_mask.shape, dtype=type_var)
            self._invert_move_pixels(output, image)
        output.astype(type_var)
        return output


    def __set_neighbors(self,row,col):
        if row > 0:
            self.neighbors_mask[row - 1, col] += 1
        elif row < self.neighbors_mask.shape[0] - 1:
            self.neighbors_mask[row + 1, col] += 1
        if col > 0:
            self.neighbors_mask[row, col - 1] += 1
        elif col < self.neighbors_mask.shape[1] - 1:
            self.neighbors_mask[row, col + 1] += 1

    def drop_pixel(self, oldrow, oldcol, newrow, newcol):
        if newrow < self.dropped_adjuster.shape[1] and \
            newcol < self.dropped_adjuster.shape[2]:
            self.dropped_adjuster[0, newrow, newcol] = oldrow
            self.dropped_adjuster[1, newrow, newcol] = oldcol
            self.__set_neighbors(newrow, newcol)
       # else:
        #    print 'foo'
        self.dropped_mask[oldrow, oldcol] = 1


    def keep_pixel(self, oldrow, oldcol, newrow, newcol):
        self.dropped_adjuster[0, newrow, newcol] = oldrow
        self.dropped_adjuster[1, newrow, newcol] = oldcol

    def drop_seams(self,seam):
        self.inverter = None
        for row in range(len(seam)):
            col = seam[row]
            adjusted_row = self.dropped_adjuster[0, row, col]
            adjusted_col = self.dropped_adjuster[1, row, col]
            self.dropped_mask[adjusted_row, adjusted_col] = 1
            self.__set_neighbors(row,col)
        output = _remove_seam([self.dropped_adjuster[0],self.dropped_adjuster[1],self.neighbors_mask],seam)
        self.dropped_adjuster = np.indices((self.dropped_adjuster.shape[1],self.dropped_adjuster.shape[2]-1))
        self.dropped_adjuster[0] = output[0]
        self.dropped_adjuster[1] = output[1]
        self.neighbors_mask = output[2]

    def add_seams(self,seam):
        self.inverter = None
        for row in range(len(seam)):
            self.__set_neighbors(row,seam[row])
        output = _add_seam([(self.dropped_adjuster[0],maxdisplacementvalue),
                            (self.dropped_adjuster[1],maxdisplacementvalue),
                            (self.neighbors_mask,0)],
                              seam)
        self.dropped_adjuster = np.indices((self.dropped_adjuster.shape[1],self.dropped_adjuster.shape[2]+1))
        self.dropped_adjuster[0] = output[0]
        self.dropped_adjuster[1] = output[1]
        self.neighbors_mask = output[2]

    def read_adjusters(self,row_adjust, col_adjust):
        self.dropped_adjuster[0] = image_wrap.openImageFile(row_adjust).to_array()
        self.dropped_adjuster[1] = image_wrap.openImageFile(col_adjust).to_array()
        self.inverter = None

    def save_adjusters(self,filename):
        """
        :param filename:
        :return: row and column uint16 PNG files
        """
        f1 = filename[:filename.find('.')] + '_adjr.png'
        f2 = filename[:filename.find('.')] + '_adjc.png'
        image_wrap.ImageWrapper(self.dropped_adjuster[0].astype('uint16')).save(f1)
        image_wrap.ImageWrapper(self.dropped_adjuster[1].astype('uint16')).save(f2)
        return f1,f2

    def save_neighbors_mask(self,filename):
        mask =np.copy(self.neighbors_mask)
        mask[mask>0] = 255
        image_wrap.ImageWrapper(mask.astype('uint8')).save(filename)

    def set_dropped_mask(self,filename):
        self.dropped_mask = filename

    def read_dropped_mask(self,filename):
        self.dropped_mask = tool_set.openImageFile(filename).to_array()/255

    def save_dropped_mask(self, filename):
        image_wrap.ImageWrapper(self.dropped_mask * 255).save(filename)

    def _move_pixels(self, output, input, adjuster):
        adjuster_cp = np.copy(adjuster)
        da = np.indices((adjuster_cp.shape[1],adjuster_cp.shape[2]))
        adjuster_cp[adjuster_cp==maxdisplacementvalue] = da[adjuster_cp==maxdisplacementvalue]
        #remap wants float 32
        adjuster_cp = adjuster_cp.astype(np.float32)
        output[:] = cv2.remap(input, adjuster_cp[1], adjuster_cp[0], cv2.INTER_NEAREST)

    def _rebuildInverter(self):
        self.inverter = np.array([
            np.zeros(self.dropped_mask.shape, dtype=np.int64),
            np.zeros(self.dropped_mask.shape, dtype=np.int64)])
        for row in range(self.dropped_adjuster[0].shape[0]):
            for col in range(self.dropped_adjuster[0].shape[1]):
                irow = self.dropped_adjuster[0, row, col]
                icol = self.dropped_adjuster[1, row, col]
                self.inverter[0, irow, icol] = row
                self.inverter[1, irow, icol] = col

    def _invert_move_pixels(self, output, input):
        if self.inverter is None:
            self._rebuildInverter()
        self._move_pixels(output,input,self.inverter)

def hog(img):
    gx = cv2.Sobel(img, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(img, cv2.CV_32F, 0, 1)
    mag, ang = cv2.cartToPolar(gx, gy)
    bin_n = 16 # Number of bins
    bin = np.int32(bin_n*ang/(2*np.pi))

    bin_cells = []
    mag_cells = []

    cellx = celly = 8

    for i in range(0,img.shape[0]/celly):
        for j in range(0,img.shape[1]/cellx):
            bin_cells.append(bin[i*celly : i*celly+celly, j*cellx : j*cellx+cellx])
            mag_cells.append(mag[i*celly : i*celly+celly, j*cellx : j*cellx+cellx])

    hists = [np.bincount(b.ravel(), m.ravel(), bin_n) for b, m in zip(bin_cells, mag_cells)]
    hist = np.hstack(hists)

    # transform to Hellinger kernel
    eps = 1e-7
    hist /= hist.sum() + eps
    hist = np.sqrt(hist)
    hist /= np.linalg.norm(hist) + eps

    return hist

class EnergyFunc:
    def energy(self, image):
        pass

class SobelFunc(EnergyFunc):

    def __init__(self):
        pass

    def __call__(self, image):
        bw = cv2.cvtColor(image.astype('uint8'), cv2.COLOR_BGR2GRAY)
        gx = cv2.Sobel(bw, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(bw, cv2.CV_32F, 0, 1)
        mag, ang = cv2.cartToPolar(gx, gy)
        return mag

class HogEnergyFunc(EnergyFunc):

    def __init__(self):
        pass

    def __call__(self, image, multipliers=[]):
        bw = cv2.cvtColor(image.astype('uint8'), cv2.COLOR_BGR2GRAY)
        return hog(bw)


class ScharrEnergyFunc(EnergyFunc):
    def __init__(self):
        pass

    def __call__(self, image, multipliers=[]):
        splits = cv2.split(image)
        if len(splits) > 2:
            b, g, r = splits[0],splits[1],splits[2]
            b_energy = np.hypot(cv2.Scharr(b, cv2.CV_64F, 1, 0), cv2.Scharr(b, cv2.CV_64F, 0, 1))
            g_energy = np.hypot(cv2.Scharr(g, cv2.CV_64F, 1, 0), cv2.Scharr(g, cv2.CV_64F, 0, 1))
            r_energy = np.hypot(cv2.Scharr(r, cv2.CV_64F, 1, 0), cv2.Scharr(r, cv2.CV_64F, 0, 1))
            # abs ?
            result = np.linalg.norm([b_energy, g_energy, r_energy],axis=0)
        else:
            result = np.hypot(cv2.Scharr(splits[0], cv2.CV_64F, 1, 0), cv2.Scharr(splits[0], cv2.CV_64F, 0, 1))
        return result

def saveEnergy(map,filename):
    minv = np.min(map)
    maxv = np.max(map)
    map = ((map-minv)/(maxv-minv))
    map = cv2.cvtColor((map*255).astype('uint8'), cv2.COLOR_GRAY2RGB)
    image_wrap.ImageWrapper(map).save(filename)


class ImageState:

    def __init__(self, image, multipliers=[], energy_function = ScharrEnergyFunc()):
        self.image = image
        self.multiplier = np.ones((image.shape[0],image.shape[1]))
        for mult in multipliers:
            self.multiplier *= mult
        self.energy_function = energy_function

    def energy(self):
        E = self.energy_function(self.image)
        return E + (E * self.multiplier)

class SeamCarver:
    bounds_expansion = 5
    def __init__(self, filename, shape=None, mask_filename=None,
                 energy_function= ScharrEnergyFunc(),
                 keep_size = False,
                 seam_function=base_energy_function):
        # initialize parameter
        self.filename = filename
        self.keep_size = keep_size

        # read in image and store as np.float64 format
        img = tool_set.openImageFile(filename).to_array()
        self.img_type = img.dtype
        self.image = img.astype(np.float64)
        if shape is None:
            self.shape = (self.image.shape[0], self.image.shape[1])
        else:
            self.shape = shape
        self.energy_function = energy_function
        self.seam_function = seam_function

        self.protected = np.ones((self.image.shape[0], self.image.shape[1])).astype(np.float64)
        self.removal = np.ones((self.image.shape[0], self.image.shape[1])).astype(np.float64)
        self.mask_tracker = MaskTracker((self.image.shape[0], self.image.shape[1]))

        if mask_filename is not None:
            mask = tool_set.openImageFile(mask_filename).to_array()
            self.protected[mask[:, :, 1] > 2] = 1000.0
            self.removal[mask[:, :, 0] > 2] = -1000.0

        self.narrow_bounds = True

        # kernel for forward energy map calculation
        self.kernel_x = np.array([[0., 0., 0.], [-1., 0., 1.], [0., 0., 0.]], dtype=np.float64)
        self.kernel_y_left = np.array([[0., 0., 0.], [0., 0., 1.], [0., -1., 0.]], dtype=np.float64)
        self.kernel_y_right = np.array([[0., 0., 0.], [1., 0., 0.], [0., -1., 0.]], dtype=np.float64)


    def remove_seams(self):
        removal = self.removal
        protected = self.protected
        current_image = ImageState(self.image,multipliers=[self.protected, self.removal],
                                   energy_function=self.energy_function)
        iterations = 0
        while np.any((removal)<0):
            base_energy = current_image.energy()
            row_energy=_accumulate_energy(base_energy,energy_function=self.seam_function)#,multiplier=current_image.multiplier)
            column_energy = _accumulate_energy(_image_rotate(base_energy, 1),energy_function=self.seam_function)#,
                                               #multiplier=_image_rotate(current_image.multiplier,1))
            if self.narrow_bounds:
                options = np.where(removal==-1000.0)
                min_row = min(options[0])
                max_row = max(options[0])
                min_row = max(0,min_row-self.bounds_expansion)
                max_row = min(removal.shape[0], max_row + self.bounds_expansion)
                min_col = min(options[1])
                max_col = max(options[1])
                min_col = max(0, min_col - self.bounds_expansion)
                max_col = min(removal.shape[1], max_col + self.bounds_expansion)
                row_bounds = (min_row,max_row)
                col_bounds = (min_col,max_col)
            else:
                row_bounds = None
                col_bounds = None
            seam_row_idx, row_cost = _find_seam(row_energy, bounds=col_bounds)
            seam_col_idx, col_cost = _find_seam(column_energy, bounds=row_bounds)
            if col_cost < row_cost:
                self.mask_tracker.rotate(1)
                results = _remove_seam([_image_rotate(current_image.image,1),
                                        _image_rotate(protected, 1),
                                        _image_rotate(removal,1)],
                                        seam_col_idx)
                self.mask_tracker.drop_seams(seam_col_idx)
                removal = _image_rotate(results[2],0)
                protected = _image_rotate(results[1], 0)
                current_image = ImageState(_image_rotate(results[0], 0),
                                           multipliers=[removal,protected],
                                           energy_function=self.energy_function)
                self.mask_tracker.rotate(0)
            else:
                results = _remove_seam([current_image.image,
                                        protected,
                                        removal],
                                        seam_row_idx)
                self.mask_tracker.drop_seams(seam_row_idx)
                removal = results[2]
                protected = results[1]
                current_image =  ImageState(results[0],multipliers=[removal,protected],
                                            energy_function=self.energy_function)
            iterations+=1


        # REMOVE ROWS
        if self.shape[1] < current_image.image.shape[1]:
            while self.shape[1] < current_image.image.shape[1]:
                base_energy = current_image.energy()
                row_energy = _accumulate_energy(base_energy,energy_function=self.seam_function)#,multiplier=current_image.multiplier)
                seam_row_idx, row_cost = _find_seam(row_energy)
                results = _remove_seam([current_image.image,
                                        protected],
                                        seam_row_idx)
                self.mask_tracker.drop_seams(seam_row_idx)
                protected = results[1]
                current_image = ImageState(results[0],
                                           multipliers=[protected],
                                           energy_function=self.energy_function)

        # REMOVE COLUMNS
        if self.shape[0] < current_image.image.shape[0]:
            self.mask_tracker.rotate(1)
            protected = _image_rotate(protected, 1)
            current_image  = ImageState(_image_rotate(current_image.image, 1),
                                        multipliers=[protected],
                                        energy_function=self.energy_function)
            #rotated so compare to shape[1]
            while self.shape[0] < current_image.image.shape[1]:
                base_energy = current_image.energy()
                column_energy = _accumulate_energy(base_energy,energy_function=self.seam_function)#,multiplier=current_image.multiplier)
                seam_col_idx, col_cost = _find_seam(column_energy)
                results = _remove_seam([current_image.image,protected],
                                   seam_col_idx)
                self.mask_tracker.drop_seams(seam_col_idx)
                protected = results[1]
                current_image = ImageState(results[0],
                                       multipliers=[protected],
                                           energy_function=self.energy_function)
            self.mask_tracker.rotate(0)
            protected = _image_rotate(protected,0)
            current_image = ImageState(_image_rotate(current_image.image, 0),
                                       multipliers=[protected],
                                       energy_function=self.energy_function)

        if self.keep_size:
            return current_image.image, self.mask_tracker.dropped_mask*255

        # ADD ROWS
        if self.shape[1] > current_image.image.shape[1]:
            base_energy = current_image.energy()
            row_energy = _accumulate_energy(base_energy,energy_function=self.seam_function)#,multiplier=current_image.multiplier)
            seam_row_idx = _find_k_seams(row_energy)
            column_idx = 0
            while self.shape[1] > current_image.image.shape[1]:
                results = _add_seam([(current_image.image,None),
                                     (protected,10000.0)],
                                      seam_row_idx[column_idx])
                self.mask_tracker.add_seams(seam_row_idx[column_idx])
                column_idx+=1
                protected = results[1]
                current_image = ImageState(results[0],
                                           multipliers=[protected],
                                           energy_function=self.energy_function)
                if column_idx % 50 == 0 or column_idx == seam_row_idx.shape[0]:
                    base_energy = current_image.energy()
                    row_energy = _accumulate_energy(base_energy,
                                                    energy_function=self.seam_function)  # ,multiplier=current_image.multiplier)
                    seam_row_idx = _find_k_seams(row_energy)
                    column_idx = 0

        # ADD COLUMNS
        if self.shape[0] > current_image.image.shape[0]:
            self.mask_tracker.rotate(1)
            protected = _image_rotate(protected, 1)
            current_image = ImageState(_image_rotate(current_image.image, 1),
                                           multipliers=[protected],
                                           energy_function=self.energy_function)
            # rotated so compare to shape[1]

            base_energy = current_image.energy()
            column_energy = _accumulate_energy(base_energy,energy_function=self.seam_function)
            seam_col_idx = _find_k_seams(column_energy)
            row_idx = 0
            while self.shape[0] > current_image.image.shape[1]:
                results = _add_seam([(current_image.image,None),
                                    (protected,10000.0)],
                                    seam_col_idx[row_idx])
                self.mask_tracker.add_seams(seam_col_idx[row_idx])
                row_idx+=1
                protected = results[1]
                current_image = ImageState(results[0],
                                               multipliers=[protected],
                                               energy_function=self.energy_function)
                if row_idx % 50 ==0 or row_idx == seam_col_idx.shape[0]:
                    base_energy = current_image.energy()
                    column_energy = _accumulate_energy(base_energy, energy_function=self.seam_function)
                    seam_col_idx = _find_k_seams(column_energy)
                    row_idx = 0

            self.mask_tracker.rotate(0)
            protected = _image_rotate(protected, 0)
            current_image = ImageState(_image_rotate(current_image.image, 0),
                                           multipliers=[protected],
                                           energy_function=self.energy_function)

        return current_image.image.astype(self.img_type), self.mask_tracker.dropped_mask*255




    def calc_neighbor_matrix(self, kernel):
        b, g, r = cv2.split(self.image)
        output = np.absolute(cv2.filter2D(b, -1, kernel=kernel)) + \
                 np.absolute(cv2.filter2D(g, -1, kernel=kernel)) + \
                 np.absolute(cv2.filter2D(r, -1, kernel=kernel))
        return output

    def delete_seam(self, seam_idx):
        m, n = self.out_image.shape[: 2]
        output = np.zeros((m, n - 1, 3))
        for row in range(m):
            col = seam_idx[row]
            output[row, :, 0] = np.delete(self.out_image[row, :, 0], [col])
            output[row, :, 1] = np.delete(self.out_image[row, :, 1], [col])
            output[row, :, 2] = np.delete(self.out_image[row, :, 2], [col])
        self.out_image = np.copy(output)



    def update_seams(self, remaining_seams, current_seam):
        output = []
        for seam in remaining_seams:
            seam[np.where(seam >= current_seam)] += 2
            output.append(seam)
        return output

    def rotate_image(self, image, ccw):
        m, n, ch = image.shape
        output = np.zeros((n, m, ch))
        if ccw:
            image_flip = np.fliplr(image)
            for c in range(ch):
                for row in range(m):
                    output[:, row, c] = image_flip[row, :, c]
        else:
            for c in range(ch):
                for row in range(m):
                    output[:, m - 1 - row, c] = image[row, :, c]
        return output

    def rotate_mask(self, mask, ccw):
        m, n = mask.shape
        output = np.zeros((n, m))
        if ccw > 0:
            image_flip = np.fliplr(mask)
            for row in range(m):
                output[:, row] = image_flip[row, :]
        else:
            for row in range(m):
                output[:, m - 1 - row] = mask[row, :]
        return output

    def delete_seam_on_mask(self, seam_idx):
        m, n = self.mask.shape
        output = np.zeros((m, n - 1))
        for row in range(m):
            col = seam_idx[row]
            output[row, :] = np.delete(self.mask[row, :], [col])
        self.mask = np.copy(output)

    def add_seam_on_mask(self, seam_idx):
        m, n = self.mask.shape
        output = np.zeros((m, n + 1))
        for row in range(m):
            col = seam_idx[row]
            if col == 0:
                p = np.average(self.mask[row, col: col + 2])
                output[row, col] = self.mask[row, col]
                output[row, col + 1] = p
                output[row, col + 1:] = self.mask[row, col:]
            else:
                p = np.average(self.mask[row, col - 1: col + 1])
                output[row, : col] = self.mask[row, : col]
                output[row, col] = p
                output[row, col + 1:] = self.mask[row, col:]
        self.mask = np.copy(output)

    def get_object_dimension(self):
        rows, cols = np.where(self.mask > 0)
        height = np.amax(rows) - np.amin(rows) + 1
        width = np.amax(cols) - np.amin(cols) + 1
        return height, width

def __composeArguments(mask_tracker, arguments={}):
    import os
    source = arguments['source filename']
    adjusternames = os.path.join(os.path.dirname(source),
                                 tool_set.shortenName(os.path.basename(source), '.png', identifier=tool_set.uniqueId()))
    finalmaskname = os.path.join(os.path.dirname(source),
                                 tool_set.shortenName(os.path.basename(source), '_final_mask.png',
                                                      identifier=tool_set.uniqueId()))
    args = {}
    args.update(arguments)
    if 'row adjuster' not in arguments or ('mask interpolated' in arguments and arguments['mask interpolated'] == 'yes'):
        adjusternames_row, adjusternames_col = mask_tracker.save_adjusters(adjusternames)
        args.update({
            'column adjuster': os.path.basename(adjusternames_col),
            'row adjuster': os.path.basename(adjusternames_row),
            'mask interpolated': 'yes'})
    if 'neighbor mask' not in arguments or ('mask interpolated' in arguments and arguments['mask interpolated'] == 'yes'):
        mask_tracker.save_neighbors_mask(finalmaskname)
        args.update({
            'neighbor mask': os.path.basename(finalmaskname),
            'mask interpolated': 'yes'
        })
    return {'arguments': args}

def seamCompare(img1, img2,  arguments=dict()):
    if (sum(img1.shape) != sum(img2.shape) and (img1.shape[0] == img2.shape[0] or img1.shape[1] == img2.shape[1])):
        # seams can only be calculated in one dimension--only one dimension can change in size
        mask_tracker = __composeSeamMask(img1, img2)
        return (255-(mask_tracker.dropped_mask*255)),__composeArguments(mask_tracker,arguments=arguments)
    elif (img1.shape[0] != img2.shape[0] and img1.shape[1] != img2.shape[1]):
        return tool_set.composeCropImageMask(img1, img2)
    return None,{}


def createHorizontalSeamMask(old, new):
    """
    new is smaller than old in the first dimsension
       :param old:
       :param new:
       :return:
       @type old: numpy.ndarray
       @type new: numpy.ndarray
       @rtype: MaskTracker
    """
    return __slideAcrossSeams(old,
                              new,
                              range(old.shape[1]),
                              range(old.shape[1]),
                              old.shape[1],
                              old.shape[0]
                              )


def createVerticalSeamMask(old, new):
    """
       new is smaller than old in the second dimsension
          :param old:
          :param new:
          :return:
          @type old: numpy.ndarray
          @type new: numpy.ndarray
          @rtype: MaskTracker
    """
    return __slideAcrossSeams(old,
                              new,
                              [x * old.shape[1] for x in range(old.shape[0])],
                              [x * new.shape[1] for x in range(old.shape[0])],
                              1,
                              old.shape[1])


def __slideAcrossSeams(old, new, oldmatchchecks, newmatchchecks, increment, count):
    """

    :param old:
    :param new:
    :param oldmatchchecks:
    :param newmatchchecks:
    :param increment: the increment along the row or skip a row: 1 or the length of a row.
    :param count:  the amount or rows or columns,
    :return:
    """
    from functools import partial
    ho, wo = old.shape
    hn, wn = new.shape
    mask_tacker = MaskTracker(old.shape, final_shape=new.shape)
    remove_action = partial(__setRemoveMask, mask_tacker)
    keep_action = partial(__setKeepMask, mask_tacker)
    for pos in range(count):
        oldmatchchecks, newmatchchecks = __findSeam(old,
                                                    new,
                                                    oldmatchchecks,
                                                    newmatchchecks,
                                                    increment,
                                                    lambda old_pos, new_pos: remove_action(old_pos / wo, old_pos % wo,
                                                                                           new_pos / wn, new_pos % wn),
                                                    lambda old_pos, new_pos: keep_action(old_pos / wo, old_pos % wo,
                                                                                           new_pos / wn, new_pos % wn)
                                                    )
    return mask_tacker


def __findSeam(old, new, oldmatchchecks, newmatchchecks, increment, remove_action, keep_action):
    replacement_oldmatchchecks = []
    replacement_newmatchchecks = []
    newmaxlen = reduce(lambda x, y: x * y, new.shape, 1)
    for pos in range(len(oldmatchchecks)):
        old_pixel = old.item(oldmatchchecks[pos])
        if newmatchchecks[pos] >= newmaxlen:
            remove_action(oldmatchchecks[pos], newmatchchecks[pos])
            continue
        new_pixel = new.item(newmatchchecks[pos])
        if old_pixel != new_pixel:
            remove_action(oldmatchchecks[pos], newmatchchecks[pos])
            replacement_newmatchchecks.append(newmatchchecks[pos])
        else:
            keep_action(oldmatchchecks[pos], newmatchchecks[pos])
            replacement_newmatchchecks.append(newmatchchecks[pos] + increment)
        replacement_oldmatchchecks.append(oldmatchchecks[pos] + increment)
    return replacement_oldmatchchecks, replacement_newmatchchecks

def __composeSeamMask(img1, img2):
    """

    :param img1:
    :param img2:
    :return:
    @type img1: numpy.ndarray
    @type img2: numpy.ndarray
    @rtype: MaskTracker
    """
    if img1.shape[0] < img2.shape[0]:
        return createHorizontalSeamMask(img1, img2)
    else:
        return createVerticalSeamMask(img1, img2)


def __findNeighbors(paths, next_pixels):
    newpaths = list()
    s = set()
    for path in paths:
        x = path[len(path) - 1]
        for i in np.intersect1d(np.array([x - 1, x, x + 1]), next_pixels):
            if i not in s:
                newpaths.append(path + [i])
                s.add(i)
    return newpaths


def __setRemoveMask(mask_tracker, oldx, oldy, newx, newy):
    """

    :param mask_tracker:
    :param x:
    :param y:
    :return:
    @type mask_tracker: MaskTracker
    """
    mask_tracker.drop_pixel(oldx, oldy, newx, newy)


def __setKeepMask(mask_tracker, oldx, oldy, newx, newy):
    """

    :param mask_tracker:
    :param x:
    :param y:
    :return:
    @type mask_tracker: MaskTracker
    """
    mask_tracker.keep_pixel(oldx, oldy, newx, newy)

        # def __findVerticalSeam(mask):
#    paths = list()
##    for candidate in np.where(mask[0, :] > 0)[0]:
#       paths.append([candidate])
#   for x in range(1, mask.shape[0]):
#       paths = __findNeighbors(paths, np.where(mask[x, :] > 0)[0])
#   return paths
# def __findHorizontalSeam(mask):
#    paths = list()
#    for candidate in np.where(mask[:, 0] > 0)[0]:
#        paths.append([candidate])
#    for y in range(1, mask.shape[1]):
#        paths = __findNeighbors(paths, np.where(mask[:, y] > 0)[0])
#    return paths
# def __seamMask(mask):
#    seams = __findVerticalSeams(mask)
##    if len(seams) > 0:
#        first = seams[0]
#        # should compare to seams[-1].  this would be accomplished by
#        # looking at the region size of the seam. We want one of the first or last seam that is most
#        # centered
#        mask = np.zeros(mask.shape)
#        for i in range(len(first)):
#            mask[i, first[i]] = 255
#        return mask
#    else:
#        seams = __findHorizontalSeam(mask)
#        if len(seams) == 0:
#            return mask
#        first = seams[0]
#        # should compare to seams[-1]
#        mask = np.zeros(mask.shape)
#        for i in range(len(first)):
#            mask[first[i], i] = 255
#        return mask
