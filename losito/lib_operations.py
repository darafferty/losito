# -*- coding: utf-8 -*-
"""
Libraries for operations
"""
import logging
import glob
import multiprocessing
import numpy as np
from astropy.io import fits as pyfits
import casacore.tables as pt
import os
import sys
from configparser import ConfigParser
if (sys.version_info > (3, 0)):
    from io import StringIO
else:
    from StringIO import StringIO


class ParsetParser(ConfigParser):
    """
    A parser for losito parset files.

    Parameters
    ----------
    parsetFile : str
        Name of the parset file.
    """

    def __init__(self, parsetFile):
        ConfigParser.__init__(self, inline_comment_prefixes=('#', ';'))

        config = StringIO()
        # add [_global] fake section at beginning
        config.write('[_global]\n'+open(parsetFile).read())
        config.seek(0, os.SEEK_SET)
        self.read_file(config)

    def checkSpelling(self, s, availValues=[]):
        """
        check if any value in the step is missing from a value list and return a warning
        """
        entries = [x.lower() for x in list(dict(self.items(s)).keys())]
        availValues = ['soltab', 'operation'] + availValues
        availValues = [x.lower() for x in availValues]
        for e in entries:
            if e not in availValues:
                logging.warning('Mispelled option: %s - Ignoring!' % e)

    def getstr(self, s, v, default=None):
        if self.has_option(s, v):
            return str(self.get(s, v).replace('\'', '').replace('"', ''))  # remove apex
        elif default is None:
            logging.error('Section: %s - Values: %s: required (expected string).' % (s, v))
        else:
            return default

    def getbool(self, s, v, default=None):
        if self.has_option(s, v):
            return ConfigParser.getboolean(self, s, v)
        elif default is None:
            logging.error('Section: %s - Values: %s: required (expected bool).' % (s, v))
        else:
            return default

    def getfloat(self, s, v, default=None):
        if self.has_option(s, v):
            return ConfigParser.getfloat(self, s, v)
        elif default is None:
            logging.error('Section: %s - Values: %s: required (expected float).' % (s, v))
        else:
            return default

    def getint(self, s, v, default=None):
        if self.has_option(s, v):
            return ConfigParser.getint(self, s, v)
        elif default is None:
            logging.error('Section: %s - Values: %s: required (expected int).' % (s, v))
        else:
            return default

    def getarray(self, s, v, default=None):
        if self.has_option(s, v):
            try:
                return self.getstr(s, v).replace(' ', '').replace('[', '').replace(']', '').split(',')  # split also turns str into 1-element lists
            except:
                logging.error('Error interpreting section: %s - values: %s (should be a list as [xxx,yyy,zzz...])' % (s, v))
        elif default is None:
            logging.error('Section: %s - Values: %s: required.' % (s, v))
        else:
            return default

    def getarraystr(self, s, v, default=None):
        try:
            return [str(x) for x in self.getarray(s, v, default)]
        except:
            logging.error('Error interpreting section: %s - values: %s (expected array of str.)' % (s, v))

    def getarraybool(self, s, v, default=None):
        try:
            return [bool(x) for x in self.getarray(s, v, default)]
        except:
            logging.error('Error interpreting section: %s - values: %s (expected array of bool.)' % (s, v))

    def getarrayfloat(self, s, v, default=None):
        try:
            return [float(x) for x in self.getarray(s, v, default)]
        except:
            logging.error('Error interpreting section: %s - values: %s (expected array of float.)' % (s, v))

    def getarrayint(self, s, v, default=None):
        try:
            return [int(x) for x in self.getarray(s, v, default)]
        except:
            logging.error('Error interpreting section: %s - values: %s (expected array of int.)' % (s, v))

    def getfilename(self, s, v, default=None):
        "Unix-style filename matching including regex"
        regstring = self.getstr(s, v, default)
        regstring = regstring.split(' ')
        filenames = []
        for split in regstring:
            filenames += glob.glob(split)
        if len(filenames) == 0:
            logging.error('No matching files found for expression '.format(s))
        return filenames








class multiprocManager(object):

    class multiThread(multiprocessing.Process):
        """
        This class is a working thread which load parameters from a queue and
        return in the output queue
        """

        def __init__(self, inQueue, outQueue, funct):
            multiprocessing.Process.__init__(self)
            self.inQueue = inQueue
            self.outQueue = outQueue
            self.funct = funct

        def run(self):

            while True:
                parms = self.inQueue.get()

                # poison pill
                if parms is None:
                    self.inQueue.task_done()
                    break

                self.funct(*parms, outQueue=self.outQueue)
                self.inQueue.task_done()

    def __init__(self, procs=0, funct=None):
        """
        Manager for multiprocessing
        procs: number of processors, if 0 use all available
        funct: function to parallelize / note that the last parameter of this function must be the outQueue
        and it will be linked to the output queue
        """
        if procs == 0:
            procs = multiprocessing.cpu_count()
        self.procs = procs
        self._threads = []
        self.inQueue = multiprocessing.JoinableQueue()
        manager = multiprocessing.Manager()
        self.outQueue = manager.Queue()
        self.runs = 0

        logging.debug('Spawning %i threads...' % self.procs)
        for proc in range(self.procs):
            t = self.multiThread(self.inQueue, self.outQueue, funct)
            self._threads.append(t)
            t.start()

    def put(self, args):
        """
        Parameters to give to the next jobs sent into queue
        """
        self.inQueue.put(args)
        self.runs += 1

    def get(self):
        """
        Return all the results as an iterator
        """
        # NOTE: do not use queue.empty() check which is unreliable
        # https://docs.python.org/2/library/multiprocessing.html
        for run in range(self.runs):
            yield self.outQueue.get()

    def wait(self):
        """
        Send poison pills to jobs and wait for them to finish
        The join() should kill all the processes
        """
        for t in self._threads:
            self.inQueue.put(None)

        # wait for all jobs to finish
        self.inQueue.join()


def make_template_image(image_name, reference_ra_deg, reference_dec_deg,
                        ximsize=512, yimsize=512, cellsize_deg=0.000417, freqs=None,
                        times=None, antennas=None, aterm_type='tec', fill_val=0):
    """
    Make a blank image and save it to disk

    Parameters
    ----------
    image_name : str
        Filename of output image
    reference_ra_deg : float, optional
        RA for center of output mask image
    reference_dec_deg : float, optional
        Dec for center of output mask image
    imsize : int, optional
        Size of output image
    cellsize_deg : float, optional
        Size of a pixel in degrees
    freqs : list
        Frequencies to use to construct extra axes (for IDG a-term images)
    times : list
        Times to use to construct extra axes (for IDG a-term images)
    antennas : list
        Antennas to use to construct extra axes (for IDG a-term images)
    aterm_type : str
        One of 'tec' or 'gain'
    fill_val : int
        Value with which to fill the data
    """
    if freqs is not None and times is not None and antennas is not None:
        nants = len(antennas)
        ntimes = len(times)
        nfreqs = len(freqs)
        if aterm_type == 'tec':
            # TEC solutions
            # data is [RA, DEC, ANTENNA, FREQ, TIME].T
            shape_out = [ntimes, nfreqs, nants, yimsize, ximsize]
        else:
            # Gain solutions
            # data is [RA, DEC, MATRIX, ANTENNA, FREQ, TIME].T
            shape_out = [ntimes, nfreqs, nants, 4, yimsize, ximsize]
    else:
        # Normal FITS image
        # data is [STOKES, FREQ, DEC, RA]
        shape_out = [1, 1, yimsize, ximsize]
        nfreqs = 1
        freqs = [150e6]

    hdu = pyfits.PrimaryHDU(np.ones(shape_out, dtype=np.float32)*fill_val)
    hdulist = pyfits.HDUList([hdu])
    header = hdulist[0].header

    # Add RA, Dec info
    i = 1
    header['CRVAL{}'.format(i)] = reference_ra_deg
    header['CDELT{}'.format(i)] = -cellsize_deg
    header['CRPIX{}'.format(i)] = ximsize / 2.0
    header['CUNIT{}'.format(i)] = 'deg'
    header['CTYPE{}'.format(i)] = 'RA---SIN'
    i += 1
    header['CRVAL{}'.format(i)] = reference_dec_deg
    header['CDELT{}'.format(i)] = cellsize_deg
    header['CRPIX{}'.format(i)] = yimsize / 2.0
    header['CUNIT{}'.format(i)] = 'deg'
    header['CTYPE{}'.format(i)] = 'DEC--SIN'
    i += 1

    # Add STOKES info or ANTENNA (+MATRIX) info
    if antennas is None:
        # basic image
        header['CRVAL{}'.format(i)] = 1.0
        header['CDELT{}'.format(i)] = 1.0
        header['CRPIX{}'.format(i)] = 1.0
        header['CUNIT{}'.format(i)] = ''
        header['CTYPE{}'.format(i)] = 'STOKES'
        i += 1
    else:
        if aterm_type == 'gain':
            # gain aterm images: add MATRIX info
            header['CRVAL{}'.format(i)] = 0.0
            header['CDELT{}'.format(i)] = 1.0
            header['CRPIX{}'.format(i)] = 1.0
            header['CUNIT{}'.format(i)] = ''
            header['CTYPE{}'.format(i)] = 'MATRIX'
            i += 1

        # dTEC or gain: add ANTENNA info
        header['CRVAL{}'.format(i)] = 0.0
        header['CDELT{}'.format(i)] = 1.0
        header['CRPIX{}'.format(i)] = 1.0
        header['CUNIT{}'.format(i)] = ''
        header['CTYPE{}'.format(i)] = 'ANTENNA'
        i += 1

    # Add frequency info
    ref_freq = freqs[0]
    if nfreqs > 1:
        deltas = freqs[1:] - freqs[:-1]
        del_freq = np.min(deltas)
    else:
        del_freq = 1e8
    header['RESTFRQ'] = ref_freq
    header['CRVAL{}'.format(i)] = ref_freq
    header['CDELT{}'.format(i)] = del_freq
    header['CRPIX{}'.format(i)] = 1.0
    header['CUNIT{}'.format(i)] = 'Hz'
    header['CTYPE{}'.format(i)] = 'FREQ'
    i += 1

    # Add time info
    if times is not None:
        ref_time = times[0]
        if ntimes > 1:
            deltas = times[1:] - times[:-1]
            del_time = np.min(deltas)
        else:
            del_time = 1.0
        header['CRVAL{}'.format(i)] = ref_time
        header['CDELT{}'.format(i)] = del_time
        header['CRPIX{}'.format(i)] = 1.0
        header['CUNIT{}'.format(i)] = 's'
        header['CTYPE{}'.format(i)] = 'TIME'
        i += 1

    # Add equinox
    header['EQUINOX'] = 2000.0

    # Add telescope
    header['TELESCOP'] = 'LOFAR'

    hdulist[0].header = header
    hdulist.writeto(image_name, overwrite=True)
    hdulist.close()

# The MIT License (MIT)
# Copyright (c) 2016 Vladimir Ignatev
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT
# OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''
Use this simple script as progressbar for now, since the old progressbar
library is python 2 and not supported anymore. In the future, it might be
usefull to use the tqdm library for this: https://github.com/tqdm/tqdm 
'''
def progress(count, total, status=''):
    '''Usage: place in for-loop like:
        for i, val in enumerate(vals):
            progress(i, len(vals), somestringcomment)
            ...
    '''
    bar_len = 40
    filled_len = round(bar_len * count / float(total))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
    sys.stdout.flush()
