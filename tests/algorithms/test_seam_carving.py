import unittest
from maskgen.algorithms.seam_carving import SeamCarver, HogEnergyFunc, SobelFunc,saveEnergy, ScharrEnergyFunc,\
    createHorizontalSeamMask,createVerticalSeamMask, foward_base_energy_function
from tests.test_support import TestSupport
import os
from maskgen.image_wrap import ImageWrapper, openImageFile,deleteImage
import numpy as np
import random


class TestToolSet(TestSupport):

    def xtest_Sobel(self):
        filename = self.locateFile('tests/algorithms/arch_sunset.resized.jpg')
        map = SobelFunc()(np.asarray(openImageFile(filename)))
        saveEnergy(map,os.path.join(os.path.dirname(filename), 'arch_e.png'))

    def xtest_Scharr(self):
        filename = self.locateFile('tests/algorithms/arch_sunset.resized.jpg')
        map = ScharrEnergyFunc()(np.asarray(openImageFile(filename)))
        saveEnergy(map,os.path.join(os.path.dirname(filename), 'arch_e.png'))

    def xtest_Hog(self):
        filename = self.locateFile('tests/algorithms/arch_sunset.resized.jpg')
        map = HogEnergyFunc()(np.asarray(openImageFile(filename)))
        saveEnergy(map,os.path.join(os.path.dirname(filename), 'arch_e.png'))

    def test_mask_withsame_size(self):
        filename = self.locateFile('tests/algorithms/cat.png')
        img = openImageFile(filename)
        somemask = np.random.randint(0,255,(img.to_array().shape))
        sc = SeamCarver(filename,
                        shape=somemask.shape,
                        mask_filename=self.locateFile('tests/algorithms/cat_mask.png'))
        image, mask = sc.remove_seams()
        somemask = sc.mask_tracker.move_pixels(somemask.astype('uint8'))
        self.assertTrue(image.shape == somemask.shape)
        self.assertTrue((image.shape[0],image.shape[1]) == sc.mask_tracker.neighbors_mask.shape)
        #ImageWrapper(image).save(os.path.join(os.path.dirname(filename), 'cat_f.png'))
        #ImageWrapper(mask).save(os.path.join(os.path.dirname(filename), 'cat_m.png'))
        #ImageWrapper(somemask).save(os.path.join(os.path.dirname(filename), 'twins_sm.png'))
        #sc.mask_tracker.save_neighbors_mask(os.path.join(os.path.dirname(filename), 'twins_rm.png'))

    def test_shrink(self):
        filename = self.locateFile('tests/algorithms/twins.jpg')
        img = openImageFile(filename)

        #img = openImageFile(filename, False, None)

        somemask = img.to_array()
        somemaskcopy = somemask
        sc = SeamCarver(filename, shape=(
        350, 450),energy_function=SobelFunc())  # mask_filename=self.locateFile('tests/algorithms/cat_mask.png'))
        image, mask = sc.remove_seams()

        #ImageWrapper(image).save(os.path.join(os.path.dirname(filename), 'twins_f.png'))
        #ImageWrapper(mask).save(os.path.join(os.path.dirname(filename), 'twins_m.png'))
        radj, cadj = sc.mask_tracker.save_adjusters('adjusters.png')
        sc.mask_tracker.read_adjusters( radj, cadj )
        sc.mask_tracker.save_neighbors_mask('twins_m.png')
        os.remove(radj)
        os.remove(cadj)
        os.remove('twins_m.png')
        somemask = sc.mask_tracker.move_pixels(somemask)
        #ImageWrapper(somemask).save(os.path.join(os.path.dirname(filename), 'twins_sm.png'))
        self.assertTrue(image.shape == somemask.shape)
        self.assertTrue(np.all(image == somemask))
        self.assertTrue((image.shape[0], image.shape[1]) == sc.mask_tracker.neighbors_mask.shape)
        originalmask = sc.mask_tracker.invert_move_pixels(somemask)
        self.assertTrue(somemaskcopy.shape == originalmask.shape)
        #ImageWrapper(somemaskcopy).save(os.path.join(os.path.dirname(filename), 'twins_om.png'))
        #ImageWrapper(originalmask).save(os.path.join(os.path.dirname(filename), 'twins_om2.png'))
        self.assertTrue(np.all(somemaskcopy[mask==0] == originalmask[mask==0]))


    def test_shrink_forward_energy(self):
        filename = self.locateFile('tests/algorithms/twins.jpg')
        img = openImageFile(filename)
        somemask = img.to_array()
        somemaskcopy = somemask
        sc = SeamCarver(filename, shape=(
        350, 450),energy_function=SobelFunc(),
                        seam_function=foward_base_energy_function)
        image, mask = sc.remove_seams()
        #ImageWrapper(image).save(os.path.join(os.path.dirname(filename), 'twins_f.png'))
        #ImageWrapper(mask).save(os.path.join(os.path.dirname(filename), 'twins_m.png'))
        radj, cadj = sc.mask_tracker.save_adjusters('adjusters.png')
        deleteImage(radj)
        deleteImage(cadj)
        foo = np.copy(sc.mask_tracker.dropped_adjuster)
        sc.mask_tracker.read_adjusters( radj, cadj )
        self.assertTrue(np.all(foo == sc.mask_tracker.dropped_adjuster))

        sc.mask_tracker.save_neighbors_mask('twins_m.png')
        #os.remove(radj)
        #os.remove(cadj)
        #os.remove('twins_m.png')
        somemask = sc.mask_tracker.move_pixels(somemask)
        #ImageWrapper(somemask).save(os.path.join(os.path.dirname(filename), 'twins_sm.png'))
        self.assertTrue(image.shape == somemask.shape)
        self.assertTrue(np.all(image == somemask))
        self.assertTrue((image.shape[0], image.shape[1]) == sc.mask_tracker.neighbors_mask.shape)
        originalmask = sc.mask_tracker.invert_move_pixels(somemask)
        self.assertTrue(somemaskcopy.shape == originalmask.shape)
        #ImageWrapper(somemaskcopy).save(os.path.join(os.path.dirname(filename), 'twins_om.png'))
        #ImageWrapper(originalmask).save(os.path.join(os.path.dirname(filename), 'twins_om2.png'))
        self.assertTrue(np.all(somemaskcopy[mask==0] == originalmask[mask==0]))

    def test_shrink_forward_energy_arch(self):
        #filename = self.locateFile('tests/algorithms/arch_sunset.jpg')
        #newshape = (470, 250)

        filename = self.locateFile('tests/algorithms/pexels-photo-746683.jpg')
        newshape = (1450, 1950)
        img = openImageFile(filename)
        imgcopy = img.to_array()
        sc = SeamCarver(filename, shape=newshape,energy_function=SobelFunc(),
                        seam_function=foward_base_energy_function,keep_size=True)
        image, mask = sc.remove_seams()
        #ImageWrapper(image).save(os.path.join(os.path.dirname(filename), 'as_f.png'))
        #ImageWrapper(mask).save(os.path.join(os.path.dirname(filename), 'as_m.png'))
        #radj, cadj = sc.mask_tracker.save_adjusters('adjusters.png')
        #sc.mask_tracker.read_adjusters( radj, cadj )
        sc.mask_tracker.save_neighbors_mask('as_m.png')
        imgcopymoved = sc.mask_tracker.move_pixels(imgcopy)
        #ImageWrapper(somemask).save(os.path.join(os.path.dirname(filename), 'as_sm.png'))
        self.assertTrue(image.shape == imgcopymoved.shape)
        self.assertTrue(np.all(image == imgcopymoved))
        self.assertTrue((image.shape[0], image.shape[1]) == sc.mask_tracker.neighbors_mask.shape)
        originalmask = sc.mask_tracker.invert_move_pixels(imgcopymoved)
        self.assertTrue(imgcopy.shape == originalmask.shape)
        #ImageWrapper(imgcopymoved).save(os.path.join(os.path.dirname(filename), 'as_om.png'))
        #ImageWrapper(originalmask).save(os.path.join(os.path.dirname(filename), 'as_om2.png'))
        self.assertTrue(np.all(imgcopy[mask==0] == originalmask[mask==0]))

    def extendRemoveSet(self, removeset,dim):
        newset = []
        for x in removeset:
            while True:
                newx =  min(max(0, x + random.randint(-1,1)), dim-1)
                if newx not in newset:
                    newset.append(newx)
                    break
        self.assertEqual(len(removeset),len(newset))
        return sorted(newset)


    def createHorizontal(self, basis, dimx, dimy):
        import random
        m = np.zeros((dimx, dimy))
        for y in range(dimy):
            unuseditems = [x for x in range(255) if x not in basis[:, y].tolist()]
            for x in range(dimx):
                m[x, y] = random.choice(unuseditems)
        return m


    def createVertical(self, basis, dimx, dimy):
        import random
        m = np.zeros((dimx, dimy))
        for x in range(dimx):
            unuseditems = [y for y in range(255) if y not in basis[x, :].tolist()]
            for y in range(dimy):
                m[x, y] = random.choice(unuseditems)
        return m

# need to fix the two tests: horizontal and vertical
# the random generator sometimes generates matrices that have the same
# value unintentionally, causing the test to fail
# The solution is to not fail the test in this case.
# it is a legitimate case, so the final assertion must change.

    def test_createHorizontalSeamMask(self):
        dim = 25
        #random.seed = 10
        old = [] #np.random.randint(180, 255, size=(dim, dim+1))

        f = open(self.locateFile("tests/algorithms/inputImages.txt"), "r")
        for line in f:
            for num in line.split(" "):
                old.append(int(num))
        f.close()
        old = np.array(old)
        old.resize((dim, dim+1))

        #old = np.random.randint(255, size=(dim, dim+1))  # can change this to make it so that this is static values

        new = []
        n = open(self.locateFile("tests/algorithms/newHorizontal.txt"), "r")
        for line in n:
            for num in line.split(" "):
                num = num.strip('.')
                num = num.strip('\n')
                num = num.strip('.\n')
                new.append(int(num))
        n.close()
        new = np.array(new)
        new.resize((dim-3, dim+1))
        #new = self.createHorizontal(old, dim-3, dim+1)  # creates a new image from the old one with 3 rows cut out

        mask = np.zeros((dim, dim+1)).astype('uint8')
        random.seed(10)
        removeset = sorted([x for x in random.sample(range(0, dim), 3)])
        for y in range(dim+1):
            for x in range(dim):
                mask[x, y] = (x in removeset)
            removeset = self.extendRemoveSet(removeset,dim)
        newx = [0 for y in range(dim+1)]
        for y in range(dim+1):
            for x in range(dim):
                if mask[x, y] == 0:
                    new[newx[y], y] = old[x, y]
                    newx[y] = newx[y]+1

        print old
        print new
        newmask_tracker = createHorizontalSeamMask(old,new)
        newmask = newmask_tracker.dropped_mask*255
        print mask * 255
        print newmask
        if not np.all(newmask==mask*255):
            self.assertTrue(sum(sum(newmask != mask * 255)) < 4)
        #new_rebuilt = carveMask(old, 255-(mask * 255), new.shape)
        #self.assertTrue(np.all(new==new_rebuilt))


    def test_createVerticalSeamMask(self):
        dim = 25
        old = []

        f = open(self.locateFile("tests/algorithms/inputImages.txt"), "r")
        for line in f:
            for num in line.split(" "):
                old.append(int(num))
        f.close()
        old = np.array(old)
        old.resize((dim, dim), refcheck=False)

        #old = np.random.randint(255, size=(dim, dim))
        new = []
        n = open(self.locateFile("tests/algorithms/newImage.txt"), "r")
        for line in n:
            for num in line.split(" "):
                num = num.strip('.')
                num = num.strip('\n')
                num = num.strip('.\n')
                new.append(int(num))
        n.close()
        new = np.array(new)
        new.resize((dim, dim-3))
        # new = self.createVertical(old, dim, dim-3)

        mask = np.zeros((dim, dim)).astype('uint8')
        random.seed(10)
        removeset = sorted([x for x in random.sample(range(0, dim-1), 3)])
        for x in range(dim):
            for y in range(dim):
                mask[x, y] = (y in removeset)
            removeset = self.extendRemoveSet(removeset, dim-1)
        newy = [0 for y in range(dim)]
        for y in range(dim):
            for x in range (dim):
                if mask[x,y] == 0:
                    new[x, newy[x]] = old[x, y]
                    newy[x] = newy[x]+1
        print old
        print new
        newmask_tracker = createVerticalSeamMask(old,new)
        newmask = newmask_tracker.dropped_mask*255
        print mask * 255
        print newmask
        if not np.all(newmask == mask*255):
            self.assertTrue(sum(sum(newmask != mask * 255)) < 4)


        somemask = newmask_tracker.move_pixels(old)


        self.assertTrue(old.dtype == somemask.dtype)
        self.assertTrue(np.all(new == somemask))
            # ImageWrapper(somemask).save(os.path.join(os.path.dirname(filename), 'twins_sm.png'))
        originalmask = newmask_tracker.invert_move_pixels(somemask)
        self.assertTrue(old.shape == originalmask.shape)
        # ImageWrapper(somemaskcopy).save(os.path.join(os.path.dirname(filename), 'twins_om.png'))
        # ImageWrapper(originalmask).save(os.path.join(os.path.dirname(filename), 'twins_om2.png'))
        self.assertTrue(np.all(old[mask == 0] == originalmask[mask == 0]))


if __name__ == '__main__':
    unittest.main()
