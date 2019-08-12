# -*- coding: utf-8 -*-

# Some utilities for operations

import sys
import math
import logging
import multiprocessing
import numpy as np
import os
import sys
from configparser import ConfigParser
if (sys.version_info > (3, 0)):
    #from configparser import ConfigParser
    from io import StringIO
else:
    #from ConfigParser import ConfigParser
    from StringIO import StringIO


class ParsetParser(ConfigParser):
    """
    A parser for losoto parset files.

    Parameters
    ----------
    parsetFile : str
        Name of the parset file.
    """

    def __init__(self, parsetFile):
        ConfigParser.__init__(self, inline_comment_prefixes=('#',';'))

        config = StringIO()
        # add [_global] fake section at beginning
        config.write('[_global]\n'+open(parsetFile).read())
        config.seek(0, os.SEEK_SET)
        self.readfp(config)

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
            return str(self.get(s, v).replace('\'','').replace('"','')) # remove apex
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
                return self.getstr(s, v).replace(' ','').replace('[','').replace(']','').split(',') # split also turns str into 1-element lists
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


def reorderAxes( a, oldAxes, newAxes ):
    """
    Reorder axis of an array to match a new name pattern.

    Parameters
    ----------
    a : np array
        The array to transpose.
    oldAxes : list of str
        A list like ['time','freq','pol'].
        It can contain more axes than the new list, those are ignored.
        This is to pass to oldAxis the soltab.getAxesNames() directly even on an array from getValuesIter()
    newAxes : list of str
        A list like ['time','pol','freq'].

    Returns
    -------
    np array
        With axis transposed to match the newAxes list.
    """
    oldAxes = [ax for ax in oldAxes if ax in newAxes]
    idx = [ oldAxes.index(ax) for ax in newAxes ]
    return np.transpose(a, idx)


def removeKeys( dic, keys = [] ):
    """
    Remove a list of keys from a dict and return a new one.

    Parameters
    ----------
    dic : dcit
        The input dictionary.
    keys : list of str
        A list of arguments to remove or a string for single argument.

    Returns
    -------
    dict
        Dictionary with removed keys.
    """
    dicCopy = dict(dic)
    if type(keys) is str: keys = [keys]
    for key in keys:
        del dicCopy[key]
    return dicCopy


def normalize_phase(phase):
    """
    Normalize phase to the range [-pi, pi].

    Parameters
    ----------
    phase : array of float
        Phase to normalize.

    Returns
    -------
    array of float
        Normalized phases.
    """

    # Convert to range [-2*pi, 2*pi].
    out = np.fmod(phase, 2.0 * np.pi)
    # Remove nans
    nans = np.isnan(out)
    np.putmask(out, nans, 0)
    # Convert to range [-pi, pi]
    out[out < -np.pi] += 2.0 * np.pi
    out[out > np.pi] -= 2.0 * np.pi
    # Put nans back
    np.putmask(out, nans, np.nan)
    return out
