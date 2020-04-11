"""
Definition of the Observation class
"""
import os
import sys
import logging
import subprocess
import casacore.tables as pt
import numpy as np
from astropy.time import Time
import lsmtool


class MS(object):
    """
      Class to store the information of a single measurement set. Use this
      class to interact with MS tables or get metadata like the observation-
      time, stationpositions and frequency informations.

      Parameters
      ----------
      ms_filename : str
        Filename of the MS file
      log : logger object
      starttime : float, optional
      endtime : float, optional
      """

    def __init__(self, ms_filename, log, starttime=None, endtime=None):
        self.ms_filename = ms_filename
        self.log = log
        self.starttime = starttime
        self.endtime = endtime
        self.parset_filename = self.ms_filename + '.parset'
        self.parset_parameters = {}

        # Scan the MS and store various observation parameters
        self.scan_ms()
        # Initialize the parset
        self.initialize_parset_parameters()

    def table(self, readonly=True):
        """
        Open and return the corresponding table. Don't forget to close.

        Returns
        -------
        table : table-object
        """
        return pt.table(self.ms_filename, ack=False, readonly=readonly)

    def scan_ms(self):
        """
        Scan input ms for time, freq, pointing and station info

        ## TIME
          * starttime
          * endtime
          * timepersample
          * numsample

        ## Frequency
          * referencefreq
          * startfreq
          * endfreq
          * numchannels
          * channelwidth

        ## Pointing
          * ra
          * dec

        ## Station
          * stations
          * numstations
          * stationpositions
          * antennatype
        """
        tab = self.table()

        if self.starttime is None:
            self.starttime = np.min(tab.getcol('TIME'))
        else:
            valid_times = np.where(tab.getcol('TIME') >= self.starttime)[0]
            if len(valid_times) == 0:
                self.log.critical('Start time of {0} is greater than the last time in the MS! '
                                  'Exiting!'.format(self.starttime))
                sys.exit(1)
            self.starttime = tab.getcol('TIME')[valid_times[0]]
        if self.starttime > np.min(tab.getcol('TIME')):
            self.startsat_startofms = False
        else:
            self.startsat_startofms = True
        if self.endtime is None:
            self.endtime = np.max(tab.getcol('TIME'))
        else:
            valid_times = np.where(tab.getcol('TIME') <= self.endtime)[0]
            if len(valid_times) == 0:
                self.log.critical('End time of {0} is less than the first time in the MS! '
                                  'Exiting!'.format(self.endtime))
                sys.exit(1)
            self.endtime = tab.getcol('TIME')[valid_times[-1]]
        if self.endtime < np.max(tab.getcol('TIME')):
            self.goesto_endofms = False
        else:
            self.goesto_endofms = True
        self.timepersample = tab.getcell('EXPOSURE', 0)
        self.numsamples = int(np.ceil((self.endtime - self.starttime) / self.timepersample))

        # Get frequency info
        self.referencefreq = tab.SPECTRAL_WINDOW.getcol('REF_FREQUENCY')
        self.startfreq = np.min(tab.SPECTRAL_WINDOW.getcol('CHAN_FREQ'))
        self.endfreq = np.max(tab.SPECTRAL_WINDOW.getcol('CHAN_FREQ'))
        self.numchannels = tab.SPECTRAL_WINDOW.getcol('NUM_CHAN')[0]
        self.channelwidth = tab.SPECTRAL_WINDOW.getcol('CHAN_WIDTH')[0]

        # Get pointing info
        self.ra = np.degrees(float(tab.FIELD.getcol('REFERENCE_DIR')[0][0,0]))
        if self.ra < 0.:
            self.ra = 360.0 + (self.ra)
        self.dec = np.degrees(float(tab.FIELD.getcol('REFERENCE_DIR')[0][0,1]))

        # Get station names, positions, and diameter
        self.stations = tab.ANTENNA.getcol('NAME')
        self.stationids = tab.ANTENNA.getcol('LOFAR_STATION_ID')

        self.numstations = len(self.stations)
        self.diam = float(tab.ANTENNA.getcol('DISH_DIAMETER')[0])
        self.stationpositions = tab.ANTENNA.getcol('POSITION')
        self.antennatype = tab.OBSERVATION.getcol('LOFAR_ANTENNA_SET')[0]
        if self.antennatype not in ['LBA_OUTER', 'LBA_INNER', 'LBA_ALL',
                                    'HBA_DUAL_INNER']:
            self.log.error('Antenna type not recognized (only LBA and HBA data '
                             'are supported)')
        tab.close()

        # Find mean elevation and FOV
        el_values = pt.taql("SELECT mscal.azel1()[1] AS el from "
                            + self.ms_filename + " limit ::10000").getcol("el")
        self.mean_el_rad = np.mean(el_values)
        sec_el = 1.0 / np.sin(self.mean_el_rad)
        self.fwhm_deg = 1.1 * ((3.0e8 / self.referencefreq) / self.diam) * 180. / np.pi * sec_el

    def initialize_parset_parameters(self):
        """
        Sets basic DPPP parset parameters. These are adjusted and added to
        by the operations that are run.
        """
        self.parset_parameters['msin'] = self.ms_filename
        self.parset_parameters['msout'] = '.'
        self.parset_parameters['numthreads'] = 0
        self.parset_parameters['msin.datacolumn'] = 'DATA'
        if not self.startsat_startofms:
            self.parset_parameters['msin.starttime'] = self.convert_mjd(self.starttime)
        if not self.goesto_endofms:
            self.parset_parameters['msin.ntimes'] = self.numsamples
        self.parset_parameters['steps'] = []

    def make_parset(self):
        """
        Writes the DPPP parset parameters to a text file
        """
        with open(self.parset_filename, 'w') as f:
            for k, v in self.parset_parameters.items():
                f.write('{0} = {1}\n'.format(k, v))

    def get_times(self):
        """
        Returns array of times (ordered, with duplicates excluded)
        """
        times = np.array([self.starttime+i*self.timepersample for i in range(self.numsamples)])
        return times

    def get_frequencies(self):
        """
        Returns array of channel frequencies (ordered, with duplicates excluded)
        """
        freqs = self.startfreq + self.channelwidth * np.arange(self.numchannels)
        return freqs

    def reset_beam_keyword(self, colname='DATA'):
        """
        Unsets the LOFAR_APPLIED_BEAM_MODE keyword for the given column

        Parameters
        ----------
        colname : str, optional
            Name of column
        """
        with self.table(readonly=False) as t:
            if colname in t.colnames() and 'LOFAR_APPLIED_BEAM_MODE' in t.getcolkeywords(colname):
                t.putcolkeyword(colname, 'LOFAR_APPLIED_BEAM_MODE', 'None')


class Observation(object):
    """
    The Observation object holds info on the observation and its processing parameters.
    E.g.:
        - associated MS files
        - various observation parameters
        - DPPP parset parameters
        - sky model file
        - etc.

    Parameters
    ----------
    ms_filenames : list of strings
        Filenames of the MS files.
    skymodel_filename : str
        Filename of the sky model file.
    starttime : float, optional
        The start time of the observation (in MJD seconds) to be used during processing.
        If None, the start time is the start of the MS file.
    endtime : float, optional
        The end time of the observation (in MJD seconds) to be used during processing.
        If None, the end time is the end of the MS file.
    """
    def __init__(self, ms_filenames, skymodel_filename=None, starttime=None, endtime=None):
        if isinstance(ms_filenames, str):
            self.ms_filenames = [ms_filenames]
        else:
            self.ms_filenames = ms_filenames

        self.input_skymodel_filename = skymodel_filename
        self.output_skymodel_filename = skymodel_filename+'.losito'
        self.sourcedb_filename = self.output_skymodel_filename + '.sourcedb'

        self.name = os.path.basename(self.ms_filenames[0][0:-9])
        self.log = logging.getLogger('losito:{}'.format(self.name))
        self.starttime = starttime
        self.endtime = endtime

        # Load the sky model
        if skymodel_filename is not None:
            self.load_skymodel()
        self.ms_list = [MS(_file, self.log, starttime, endtime) for _file in
                        self.ms_filenames]
        #Todo loop all
    # TODO write test to check if all ms are actually part of the same observation

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        try:
            nextms = self.ms_list[self.index]
        except IndexError:
            raise StopIteration
        self.index += 1
        return nextms

    def make_sourcedb(self):
        """
        Makes the sourcedb for DPPP from the sky model
        """
        self.save_skymodel()
        cmd = ['makesourcedb', 'in={}'.format(self.output_skymodel_filename),
               'out={}'.format(self.sourcedb_filename),
               'format=<', 'outtype=blob', 'append=False']
        subprocess.call(cmd)

    def load_skymodel(self):
        """
        Loads the sky model
        """
        # Set logging level to suppress confusing output from lsmtool
        old_level = logging.root.getEffectiveLevel()
        logging.root.setLevel(logging.WARNING)
        skymodel = lsmtool.load(self.input_skymodel_filename)
        if not skymodel.hasPatches:
            skymodel.group('single')
        skymodel.setPatchPositions(method='wmean')
        logging.root.setLevel(old_level)
        self.skymodel = skymodel

    def save_skymodel(self, filename=None, format='makesourcedb'):
        """
        Saves the sky model

        Parameters
        ----------
        filename : str, optional
            Name of output file. If None, self.output_skymodel_filename is used
        format: str, optional
            Format of the output file. Allowed formats are:
                - 'makesourcedb' (BBS format)
                - 'fits'
                - 'votable'
                - 'hdf5'
                - 'ds9'
                - 'kvis'
                - 'casa'
                - 'factor'
                - plus all other formats supported by the astropy.table package
        """
        if filename is None:
            filename = self.output_skymodel_filename
        self.skymodel.write(filename, format=format, clobber=True)

    def get_patch_coords(self):
        """
        Returns arrays of flux-weighted mean RA, Dec in degrees for patches in the
        sky model
        """
        return self.skymodel.getPatchPositions(asArray=True)

    def get_patch_names(self):
        """
        Returns list of DPPP-compatible patch names
        """
        patch_names = ['[{}]'.format(p) for p in self.skymodel.getPatchNames()]
        return patch_names

    def get_times(self):
        """
        Returns array of times (ordered, with duplicates excluded)
        """
        # TODO: Ensure times for all MS are the same
        return self.ms_list[0].get_times()

    def get_frequencies(self):
        """
        Returns array of channel frequencies (ordered, with duplicates excluded)
        """
        sb_freq = np.array([ms.get_frequencies() for ms in self]).flatten()
        if len(sb_freq) != len(np.unique(sb_freq)):
            self.log.warning('Some channels share the same frequency!')
        return sb_freq.sort()

    # def run(self, command, log, commandType='', maxThreads=None):
    #     """
    #     Run command 'command' of type 'commandType', and use 'log' for logger,
    #     for each MS of AllMSs.
    #     The command and log file path can be customised for each MS using keywords (see: 'MS.concretiseString()').
    #     Beware: depending on the value of 'Scheduler.max_threads' (see: lib_util.py), the commands are run in parallel.
    #     """
    #     # add max num of threads given the total jobs to run
    #     # e.g. in a 64 processors machine running on 16 MSs, would result in numthreads=4
    #     if commandType == 'DPPP': command += ' numthreads='+str(self.getNThreads())
    #
    #     for MSObject in self.mssListObj:
    #         commandCurrent = MSObject.concretiseString(command)
    #         logCurrent     = MSObject.concretiseString(log)
    #
    #         self.scheduler.add(cmd = commandCurrent, log = logCurrent, commandType = commandType)
    #
    #         # Provide debug output.
    #         #lib_util.printLineBold("commandCurrent:")
    #         #print (commandCurrent)
    #         #lib_util.printLineBold("logCurrent:")
    #         #print (logCurrent)
    #
    #     self.scheduler.run(check = True, maxThreads = maxThreads)

    @staticmethod
    def convert_mjd(mjd_sec):
        """
        Converts MJD to casacore MVTime

        Parameters
        ----------
        mjd_sec : float
            MJD time in seconds

        Returns
        -------
        mvtime : str
            Casacore MVTime string
        """
        t = Time(mjd_sec / 3600 / 24, format='mjd', scale='utc')
        date, hour = t.iso.split(' ')
        year, month, day = date.split('-')
        d = t.datetime
        month = d.ctime().split(' ')[1]

        return '{0}{1}{2}/{3}'.format(day, month, year, hour)
