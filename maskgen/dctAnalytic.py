# adapted from https://github.com/enmasse/jpeg_read

import sys
from math import *
from Tkinter import *
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def memoize (function):
    # http://programmingzen.com/2009/05/18/memoization-in-ruby-and-python/
    cache = {}

    def decorated_function (*args):
        try:
            return cache[args]
        except KeyError:
            val = function (*args)
            cache[args] = val
            return val

    return decorated_function


@memoize
def decodeBits (len, val):
    """ Calculate the value from the "additional" bits in the huffman data. """

    return val if (val & (1 << len - 1)) else val - ((1 << len) - 1)


def extractCoeffs (data):
    dclum = []
    dcchr1 = []
    dcchr2 = []
    aclum = []
    acchr1 = []
    acchr2 = []
    for MCU in data:
        lum = MCU[0]
        chr1 = MCU[1]
        chr2 = MCU[2]
        for MCU_component in lum:
            if len (MCU_component):
                dclum.append (MCU_component[0])
                aclum.extend (MCU_component[1:])
        for MCU_component in chr1:
            if len (MCU_component):
                dcchr1.append (MCU_component[0])
                acchr1.extend (MCU_component[1:])
        for MCU_component in chr2:
            if len (MCU_component):
                dcchr2.append (MCU_component[0])
                acchr2.extend (MCU_component[1:])

    return (dclum, dcchr1, dcchr2, aclum, acchr1, acchr2)
    

def generateHuffmanCodes (huffsize):
    """ Calculate the huffman code of each length. """
    huffcode = []
    k = 0
    code = 0

    # Magic
    for i in range (len (huffsize)):
        si = huffsize[i]
        for k in range (si):
            huffcode.append ((i + 1, code))
            code += 1

        code <<= 1

    return huffcode


def getBits (num, gen):
    """ Get "num" bits from gen. """
    out = 0
    for i in range (num):
        out <<= 1
        val = gen.next ()
        if val != []:
            out += val & 0x01
        else:
            return []

    return out


def mapHuffmanCodes (codes, values):
    """ Map the huffman code to the right value. """
    out = {}

    for i in range (len (codes)):
        out[codes[i]] = values[i]

    return out


def readAPP (type, file):
    """ Read APP marker. """
    Lp = readWord (file)
    Lp -= 2

    # If APP0 try to read the JFIF header
    # Not really necessary
    if type == 0:
        identifier = file.read (5)
        Lp -= 5
        version = file.read (2)
        Lp -= 2
        units = ord (file.read (1))
        Lp -= 1
        Xdensity = ord (file.read (1)) << 8
        Xdensity |= ord (file.read (1))
        Lp -= 2
        Ydensity = ord (file.read (1)) << 8
        Ydensity |= ord (file.read (1))
        Lp -= 2

    file.seek (Lp, 1)


def readByte (file):
    """ Read a byte from file. """
    return ord (file.read (1))


def readWord (file):
    """ Read a 16 bit word from file. """
    return ord (file.read (1)) << 8 | ord (file.read (1))


def restoreDC (data):
    """ Restore the DC values.  They are coded as the difference from the
        previous DC value of the same component.
    """

    out = []
    dc_prev = [0 for x in range (len (data[0]))]

    # For each MCU
    for mcu in data:
        # For each component
        for comp_num in range (len (mcu)):
            # For each DU
            for du in range (len (mcu[comp_num])):
                if mcu[comp_num][du]:
                    mcu[comp_num][du][0] += dc_prev[comp_num]
                    dc_prev[comp_num] = mcu[comp_num][du][0]

        out.append (mcu)

    return out


class JPEG_Reader:
    """ Class for reading DCT coefficients from JPEG files. """

    def __init__ (self):
        self.huffman_ac_tables = [{}, {}, {}, {}]
        self.huffman_dc_tables = [{}, {}, {}, {}]
        self.q_table = [[], [], [], []]

        self.XYP = 0, 0, 0
        self.component = {}
        self.num_components = 0
        self.mcus_read = 0
        self.dc = []
        self.inline_dc = 0
        self.bit_stream = []
        self.EOI = False
    	
    def readDCT_Coeffs (self, filename):
        """ Reads and returns DCT coefficients from the supplied JPEG file. """

        self.__init__ ()
	data = []

        with open (filename, "rb") as inputFile:
            in_char = inputFile.read (1)
            while in_char:
                if in_char == chr (0xff):
                    in_char = inputFile.read (1)
                    in_num = ord (in_char)
                    if 0xe0 <= in_num <= 0xef:
                        readAPP (in_num - 0xe0, inputFile)
                    elif in_num == 0xdb:
                        self.__readDQT (inputFile)
                    elif in_num == 0xdc:
                        self.__readDNL (inputFile)
                    elif in_num == 0xc4:
                        self.__readDHT (inputFile)
                    elif in_num == 0xc8:
                        print "JPG"
                    elif 0xc0 <= in_num <= 0xcf:
                        self.__readSOF (in_num - 0xc0, inputFile)
                    elif in_num == 0xda:
                        self.__readSOS (inputFile)
                        self.bit_stream = self.__readBit (inputFile)
                        while not self.EOI:
                            data.append (self.__readMCU ())
                in_char = inputFile.read (1)

        return extractCoeffs (data if self.inline_dc else restoreDC (data))

    def __readBit (self, file):
        """ A generator that reads one bit from file and handles markers and
            byte stuffing.
        """

        input = file.read (1)
        while input and not self.EOI:
            if input == chr (0xFF):
                cmd = file.read (1)
                if cmd:
                    # Byte stuffing
                    if cmd == chr (0x00):
                        input = chr (0xFF)
                    # End of image marker
                    elif cmd == chr (0xD9):
                        self.EOI = True
                    # Restart markers
                    elif 0xD0 <= ord (cmd) <= 0xD7 and self.inline_dc:
                        # Reset dc value
                        self.dc = [0 for i in range (self.num_components + 1)]
                        input = file.read (1)
                    else:
                        input = file.read (1)
                        #print "CMD: %x" % ord(cmd)

            if not self.EOI:
                for i in range (7, -1, -1):
                    # Output next bit
                    yield (ord (input) >> i) & 0x01

                input = file.read (1)

        while True:
            yield []

    def __readDHT (self, file):
        """ Read and compute the huffman tables. """

        # Read the marker length
        Lh = readWord (file)
        Lh -= 2
        while Lh > 0:
            huffsize = []
            huffval = []
            T = readByte (file)
            Th = T & 0x0F
            Tc = (T >> 4) & 0x0F
            #print "Lh: %d  Th: %d  Tc: %d" % (Lh, Th, Tc)
            Lh -= 1

            # Read how many symbols of each length
            # up to 16 bits
            for i in range (16):
                huffsize.append (readByte (file))
                Lh -= 1

            # Generate the huffman codes
            huffcode = generateHuffmanCodes (huffsize)
            #print "Huffcode", huffcode

            # Read the values that should be mapped to huffman codes
            for i in huffcode:
                #print i
                try:
                    huffval.append (readByte (file))
                    Lh -= 1
                except TypeError:
                    continue

            # Generate lookup tables
            if Tc == 0:
                self.huffman_dc_tables[Th] = mapHuffmanCodes (huffcode, huffval)
            else:
                self.huffman_ac_tables[Th] = mapHuffmanCodes (huffcode, huffval)

    def __readDNL (self, file):
        """ Read the DNL marker.  Changes the number of lines. """

        Ld = readWord (file)
        Ld -= 2
        NL = readWord (file)
        Ld -= 2

        X, Y, P = self.XYP

        if Y == 0:
            self.XYP = X, NL, P

    def __readDQT (self, file):
        """ Read the quantization table.  The table is in zigzag order. """

        Lq = readWord (file)
        Lq -= 2
        while Lq > 0:
            table = []
            Tq = readByte (file)
            Pq = Tq >> 4
            Tq &= 0xF
            Lq -= 1

            if Pq == 0:
                for i in range (64):
                    table.append (readByte (file))
                    Lq -= 1
            else:
                for i in range (64):
                    val = readWord (file)
                    table.append (val)
                    Lq -= 2

            self.q_table[Tq] = table

    def __readDU (self, comp_num):
        """ Read one data unit with component index comp_num. """

        data = []    
        comp = self.component[comp_num]
        huff_tbl = self.huffman_dc_tables[comp['Td']]

        # Fill data with 64 coefficients
        while len (data) < 64:
            key = 0

            for bits in range (1, 17):
                key_len = []
                key <<= 1
                # Get one bit from bit_stream
                val = getBits (1, self.bit_stream)
                if val == []:
                    break
                key |= val
                # If huffman code exists
                if huff_tbl.has_key ((bits, key)):
                    key_len = huff_tbl[(bits, key)]
                    break

            # After getting the DC value switch to the AC table
            huff_tbl = self.huffman_ac_tables[comp['Ta']]

            if key_len == []:
                #print (bits, key, bin(key)), "key not found"
                break
            # If ZRL fill with 16 zero coefficients
            elif key_len == 0xF0:
                for i in range (16):
                    data.append (0)
                continue

            # If not DC coefficient
            if len (data) != 0:
                # If End of block
                if key_len == 0x00:
                    # Fill the rest of the DU with zeros
                    while len (data) < 64:
                        data.append (0)
                    break

                # The first part of the AC key_len is the number of leading
                # zeros
                for i in range (key_len >> 4):
                    if len (data) < 64:
                        data.append (0)
                key_len &= 0x0F

            if len (data) >= 64:
                break

            if key_len != 0:
                # The rest of key_len is the number of "additional" bits
                val = getBits (key_len, self.bit_stream)
                if val == []:
                    break
                # Decode the additional bits
                num = decodeBits (key_len, val)

                # Experimental, doesn't work right
                if len (data) == 0 and self.inline_dc:
                    # The DC coefficient value is added to the DC value from
                    # the corresponding DU in the previous MCU
                    num += dc[comp_num]
                    self.dc[comp_num] = num

                data.append (num)
            else:
                data.append (0)

        #if len(data) != 64:
            #print "Wrong size", len(data)

        return data

    def __readMCU (self):
        """ Read an MCU. """

        comp_num = mcu = range (self.num_components)

        # For each component
        for i in comp_num:
            comp = self.component[i + 1]
            mcu[i] = []
            # For each DU
            for j in range (comp['H'] * comp['V']):
                if not self.EOI:
                    mcu[i].append (self.__readDU (i + 1))

        self.mcus_read += 1

        return mcu

    def __readSOF (self, type, file):
        """ Read the start of frame marker. """

        Lf = readWord (file)            # Read the marker length
        Lf -= 2
        P = readByte (file)             # Read the sample precision
        Lf -= 1
        Y = readWord (file)             # Read number of lines
        Lf -= 2
        X = readWord (file)             # Read the number of samples per line
        Lf -= 2
        Nf = readByte (file)            # Read number of components
        Lf -= 1

        self.XYP = X, Y, P
        #print self.XYP

        while Lf > 0:
            C = readByte (file)         # Read component identifier
            V = readByte (file)         # Read sampling factors
            Tq = readByte (file)
            Lf -= 3
            H = V >> 4
            V &= 0xF
            # Assign horizontal & vertical sampling factors and qtable
            self.component[C] = { 'H' : H, 'V' : V, 'Tq' : Tq }

    def __readSOS (self, file):
        """ Read the start of scan marker. """

        Ls = readWord (file)
        Ls -= 2

        Ns = readByte (file)            # Read number of components in scan
        Ls -= 1

        for i in range (Ns):
            Cs = readByte (file)        # Read the scan component selector
            Ls -= 1
            Ta = readByte (file)        # Read the huffman table selectors
            Ls -= 1
            Td = Ta >> 4
            Ta &= 0xF
            # Assign the DC huffman table
            self.component[Cs]['Td'] = Td
            # Assign the AC huffman table
            self.component[Cs]['Ta'] = Ta

        Ss = readByte (file)            # Should be zero if baseline DCT
        Ls -= 1
        Se = readByte (file)            # Should be 63 if baseline DCT
        Ls -= 1
        A = readByte (file)             # Should be zero if baseline DCT
        Ls -= 1

        #print "Ns:%d Ss:%d Se:%d A:%02X" % (Ns, Ss, Se, A)
        self.num_components = Ns
        self.dc = [0 for i in range (self.num_components + 1)]

    def dequantize (self, mcu):
        """ Dequantize an MCU. """

        out = mcu

        # For each coefficient in each DU in each component, multiply by the
        # corresponding value in the quantization table.
        for c in range (len (out)):
            for du in range (len (out[c])):
                for i in range (len (out[c][du])):
                    out[c][du][i] *= self.q_table[self.component[c + 1]['Tq']][i]

        return out


class JPEG_View:
    def appliesTo (self, filename):
        return filename.lower ().endswith (('jpg', 'jpeg'))

    def draw (self, frame, filename):

        DC = JPEG_Reader ().readDCT_Coeffs (filename)[0]
        minDC = min (DC)
        maxDC = max (DC)
        binCount = maxDC - minDC + 1

        fig = plt.figure ();
        self._plotHistogram (fig, np.histogram (DC, bins=binCount,
                                                range=(minDC, maxDC + 1)))
        canvas = FigureCanvasTkAgg (fig, frame)
        canvas.show ()
        canvas.get_tk_widget ().pack (side=BOTTOM, fill=BOTH, expand=True)

    def _labelSigma (self, figure, sigma):
        """ Add a label of the value of sigma to the histogram plot. """

        props = dict (boxstyle='round', facecolor='wheat', alpha=0.5)
        figure.text (0.25, 0.85, '$\sigma=%.2f$' % (sigma),
                     fontsize=14, verticalalignment='top', bbox=props)


class DCTView (JPEG_View):
    def screenName (self):
        return 'JPG DCT Histogram'

    def _plotHistogram (self, figure, histogram):

        ordinates, abscissae = histogram

#         plt.plot (abscissae[:-1], ordinates)
        plt.bar (abscissae[:-1], ordinates, 1);
        self._labelSigma (figure, ordinates.std ())


class FFT_DCTView (JPEG_View):
    def screenName (self):
        return 'FFT(JPG DCT Histogram)'

    def _plotHistogram (self, figure, histogram):

        # Calculate the DFT of the zero-meaned histogram values.  The n/2+1
        # positive frequencies are returned by rfft.  Mirror the result back
        # into ordinates.
        #
        mean = histogram[0].mean ()
        posFreqs = abs (np.fft.rfft ([i - mean for i in histogram[0]]))
        ordinates = list (reversed (posFreqs))
        ordinates.extend (posFreqs[1:])
        n = len (posFreqs)
        abscissae = range (1 - n, n)

        plt.plot (abscissae, ordinates, 'k')
        plt.plot (abscissae, self.__hat (ordinates), 'r')
        self._labelSigma (figure, np.std (ordinates))

    def __hat (self, data):
        length = len (data)
        intercept1 = int (length * 0.425)
        intercept2 = int (length * 0.575)
        amp = max (data)
        threshold = amp * 0.15

        arr = np.full (length, threshold)
        arr[intercept1:intercept2] = amp

        return arr


if __name__ == "__main__":
    DCTView ().draw (None, sys.argv[1])
    FFT_DCTView ().draw (None, sys.argv[1])