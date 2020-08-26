# -*- coding: utf-8 -*-
"""
Library for Logger, ParsetParser and progressbar
"""
import os, logging, glob, sys, time
from configparser import ConfigParser
from io import StringIO


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
                logger.warning('Mispelled option: %s - Ignoring!' % e)

    def getstr(self, s, v, default=None):
        if self.has_option(s, v):
            return str(self.get(s, v).replace('\'', '').replace('"', ''))  # remove apex
        elif default is None:
            logger.error('Section: %s - Values: %s: required (expected string).' % (s, v))
        else:
            return default

    def getbool(self, s, v, default=None):
        if self.has_option(s, v):
            return ConfigParser.getboolean(self, s, v)
        elif default is None:
            logger.error('Section: %s - Values: %s: required (expected bool).' % (s, v))
        else:
            return default

    def getfloat(self, s, v, default=None):
        if self.has_option(s, v):
            return ConfigParser.getfloat(self, s, v)
        elif default is None:
            logger.error('Section: %s - Values: %s: required (expected float).' % (s, v))
        else:
            return default

    def getint(self, s, v, default=None):
        if self.has_option(s, v):
            return ConfigParser.getint(self, s, v)
        elif default is None:
            logger.error('Section: %s - Values: %s: required (expected int).' % (s, v))
        else:
            return default

    def getarray(self, s, v, default=None):
        if self.has_option(s, v):
            try:
                return self.getstr(s, v).replace(' ', '').replace('[', '').replace(']', '').split(',')  # split also turns str into 1-element lists
            except:
                logger.error('Error interpreting section: %s - values: %s (should be a list as [xxx,yyy,zzz...])' % (s, v))
        elif default is None:
            logger.error('Section: %s - Values: %s: required.' % (s, v))
        else:
            return default

    def getarraystr(self, s, v, default=None):
        try:
            return [str(x) for x in self.getarray(s, v, default)]
        except:
            logger.error('Error interpreting section: %s - values: %s (expected array of str.)' % (s, v))

    def getarraybool(self, s, v, default=None):
        try:
            return [bool(x) for x in self.getarray(s, v, default)]
        except:
            logger.error('Error interpreting section: %s - values: %s (expected array of bool.)' % (s, v))

    def getarrayfloat(self, s, v, default=None):
        try:
            return [float(x) for x in self.getarray(s, v, default)]
        except:
            logger.error('Error interpreting section: %s - values: %s (expected array of float.)' % (s, v))

    def getarrayint(self, s, v, default=None):
        try:
            return [int(x) for x in self.getarray(s, v, default)]
        except:
            logger.error('Error interpreting section: %s - values: %s (expected array of int.)' % (s, v))

    def getfilename(self, s, v, default=None):
        "Unix-style filename matching including regex"
        regstring = self.getstr(s, v, default)
        regstring = regstring.split(' ')
        filenames = []
        for split in regstring:
            files_matching_split = glob.glob(split)
            if len(files_matching_split) == 0:
                logger.warning('No matching files found for {}.'.format(split))
            filenames += files_matching_split
        if len(filenames) == 0:
            logger.error('No matching files found')
        return filenames


class Logger():
    def __init__(self, logfile="pipeline.logging", log_dir="logs"):

        # hopefully kill other loggers
        logger = logging.getLogger('LoSiTo')
        logger.propagate = False
        logger.handlers = []

        self.logfile = logfile
        self.log_dir = log_dir
        self.backup(logfile, log_dir)
        self.set_logger(logfile, log_dir)

    def backup(self, logfile, log_dir):

        # bkp old log dir
        if os.path.isdir(log_dir):
            # os.system('rm -r {}'.format(log_dir))
            if not os.path.isdir(log_dir + '_bkp'):
                os.mkdir(log_dir + '_bkp')
            current_time = time.localtime()
            log_dir_old = time.strftime(log_dir + '_bkp_%Y-%m-%d_%H:%M', current_time)
            os.system('mv %s %s' % (log_dir, log_dir + '_bkp/' + log_dir_old))
        os.makedirs(log_dir)

        # bkp old log file
        if os.path.exists(logfile):
            current_time = time.localtime()
            logfile_old = time.strftime(logfile + '_bkp_%Y-%m-%d_%H:%M', current_time)
            log_dir_old = time.strftime(log_dir + '_bkp_%Y-%m-%d_%H:%M', current_time)
            os.system('mv %s %s' % (logfile, log_dir+'_bkp/'+log_dir_old+'/'+logfile_old))
            # os.system('rm {}'.format(logfile))

    def set_logger(self, logfile, log_dir):

        logger = logging.getLogger("LoSiTo")
        logger.setLevel(logging.INFO)

        # create file handler which logs even debug messages
        handlerFile = logging.FileHandler(logfile)
        handlerFile.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        handlerConsole = _ColorStreamHandler(stream=sys.stdout)
        handlerConsole.setLevel(logging.INFO)

        # create formatter and add it to the handlers
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        handlerFile.setFormatter(formatter)
        handlerConsole.setFormatter(formatter)

        # add the handlers to the logger
        logger.addHandler(handlerFile)
        logger.addHandler(handlerConsole)

logger = logging.getLogger("LoSiTo")


class _ColorStreamHandler(logging.StreamHandler):

    DEFAULT = '\x1b[0m'
    RED     = '\x1b[31m'
    GREEN   = '\x1b[32m'
    YELLOW  = '\x1b[33m'
    CYAN    = '\x1b[36m'

    CRITICAL = RED
    ERROR    = RED
    WARNING  = YELLOW
    INFO     = GREEN
    DEBUG    = CYAN

    @classmethod
    def _get_color(cls, level):
        if level >= logging.CRITICAL:  return cls.CRITICAL
        elif level >= logging.ERROR:   return cls.ERROR
        elif level >= logging.WARNING: return cls.WARNING
        elif level >= logging.INFO:    return cls.INFO
        elif level >= logging.DEBUG:   return cls.DEBUG
        else:                          return cls.DEFAULT

    def __init__(self, stream=None):
        logging.StreamHandler.__init__(self, stream)

    def format(self, record):
        color = self._get_color(record.levelno)
        record.msg = color + record.msg + self.DEFAULT
        return logging.StreamHandler.format(self, record)

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

""" Use this simple script as progressbar for now, since the old progressbar
library is python 2 and not supported anymore. In the future, it might be
usefull to use the tqdm library for this: https://github.com/tqdm/tqdm """


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
