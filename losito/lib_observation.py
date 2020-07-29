"""
Definition of the Observation and MS classes
"""
import os
import subprocess
import casacore.tables as pt
import numpy as np
from astropy.time import Time
import lsmtool
from .lib_io import logger


class MS:
    """
      Class to store the information of a single measurement set. Use this
      class to interact with MS tables or get metadata like the observation-
      time, stationpositions and frequency informations.

      Parameters
      ----------
      ms_filename : str
        Filename of the MS file
      """

    def __init__(self, ms_filename, starttime=None, endtime=None):
        self.ms_filename = ms_filename
        # Scan the MS and store various observation parameters
        self.scan_ms()

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

        # Get time info
        self.times = np.unique(tab.getcol('TIME'))
        assert (np.diff(self.times) >= 0).all(), self.ms_filename+" contains unordered timestamps."
        self.starttime = np.min(self.times)
        self.endtime = np.max(self.times)
        self.timepersample = tab.getcell('EXPOSURE', 0)
        self.numsamples = len(self.times)

        # Get frequency info
        self.freq = tab.SPECTRAL_WINDOW.getcol('CHAN_FREQ')[0]
        assert (np.diff(self.freq) >= 0).all(), self.ms_filename+" contains unordered frequencies."
        self.referencefreq = tab.SPECTRAL_WINDOW.getcol('REF_FREQUENCY')[0]
        self.startfreq = np.min(self.freq)
        self.endfreq = np.max(self.freq)
        self.numchannels = len(self.freq)
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
            logger.error('Antenna type not recognized (only LBA and HBA data '
                             'are supported)')
        tab.close()

        # Find mean elevation and FOV
        el_values = pt.taql("SELECT mscal.azel1()[1] AS el from "
                            + self.ms_filename + " limit ::10000").getcol("el")
        self.mean_el_rad = np.mean(el_values)
        sec_el = 1.0 / np.sin(self.mean_el_rad)
        self.fwhm_deg = 1.1 * ((3.0e8 / self.referencefreq) / self.diam) * 180. / np.pi * sec_el

    def get_times(self):
        """ Return array of times (ordered, with duplicates excluded) """
        return self.times

    def get_frequencies(self):
        """ Return array of channel frequencies (ordered, with duplicates excluded) """
        return self.freq


class Observation:
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
    """
    def __init__(self, ms_filenames, skymodel_filename=None, scheduler=None):
        if isinstance(ms_filenames, str):
            self.ms_filenames = [ms_filenames]
        else:
            self.ms_filenames = ms_filenames

        self.input_skymodel_filename = skymodel_filename
        self.output_skymodel_filename = skymodel_filename+'.losito'
        self.sourcedb_filename = self.output_skymodel_filename + '.sourcedb'
        self.name = os.path.basename(self.ms_filenames[0][0:-9])

        self.scheduler = scheduler

        # Load the sky model
        if skymodel_filename is not None:
            self.load_skymodel()
        logger.info('Checking MS files')
        self.ms_list = [MS(_file) for _file in
                        self.ms_filenames]
        self.set_time() # Set and test time information from MSs
        self.set_stations() # Set station information from MSs
        # Initialize the parset
        self.parset_filename = 'DPPP_predict.parset'
        self.parset_parameters = {}
        self.initialize_parset_parameters()

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

    def __len__(self):
        return len(self.ms_list)

    def make_sourcedb(self):
        """
        Makes the sourcedb for DPPP from the sky model
        """
        self.save_skymodel()
        cmd = ['makesourcedb', 'in={}'.format(self.output_skymodel_filename),
               'out={}'.format(self.sourcedb_filename),
               'format=<', 'outtype=blob', 'append=False']
        subprocess.call(cmd)
        # logger.debug('Copy sourcedb to all MS.')
        # for ms in self:
        #     subprocess.call('cp {} {}'.format(self.sourcedb_filename, ms.ms_filename))

    def load_skymodel(self):
        """
        Loads the sky model
        """
        # Set logging level to suppress confusing output from lsmtool
        old_level = logger.root.getEffectiveLevel()
        logger.root.setLevel('WARNING')
        skymodel = lsmtool.load(self.input_skymodel_filename)
        if not skymodel.hasPatches:
            logger.info('No patches present in skymodel. Assigning every source an individual patch.')
            skymodel.group('every')
            skymodel.setPatchPositions(method='mid')
        logger.root.setLevel(old_level)
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

    def initialize_parset_parameters(self):
        """
        Sets basic DPPP parset parameters. These are adjusted and added to
        by the operations that are run.
        """
        self.parset_parameters['msout'] = '.'
        self.parset_parameters['numthreads'] = -1
        self.parset_parameters['msin.datacolumn'] = 'DATA'
        self.parset_parameters['steps'] = []

    def make_parset(self):
        """ Write the DPPP parset parameters to a text file """
        with open(self.parset_filename, 'w') as f:
            for k, v in self.parset_parameters.items():
                f.write('{0} = {1}\n'.format(k, v))

    def add_to_parset(self, stepname, soltabname, h5parmFilename = 'corruptions.h5', DDE=True):
        """
        Add the corruptions of a h5parm to a applycal step in the DP3 parset.

        Parameters
        ----------
        stepname: string, name of the step
        soltabname: string, name of the solutiontable, e.g. "tec000"
        h5parmFilename: string, default=corruptions.h5. Name of the h5parm file.
        DDE: bool, default = True. Whether this corruption should be applied
             during the h5parmpredict for all directions or in a applycal step.
        """

        applyprefix = 'predict.applycal' if DDE else 'applycal'
        if DDE:
            self.parset_parameters[applyprefix + '.parmdb'] = h5parmFilename
            self.parset_parameters[applyprefix + '.correction'] = soltabname
        else:
            if not 'applycal' in self.parset_parameters['steps']:
                self.parset_parameters['steps'].append('applycal')
            self.parset_parameters[applyprefix + '.invert'] = 'false'
            self.parset_parameters['applycal.type'] = 'applycal'
        if applyprefix+'.steps' in self.parset_parameters:
                self.parset_parameters[applyprefix+'.steps'].append(stepname)
        else:
            self.parset_parameters[applyprefix+'.steps'] = [stepname]
        self.parset_parameters[applyprefix+'.{}.correction'.format(stepname)] = soltabname
        self.parset_parameters[applyprefix+'.{}.parmdb'.format(stepname)] = h5parmFilename


    def set_time(self):
        """ Set the time information. Also check wheter all the MS have
        matching time information."""
        starttime, endtime, timepersample, numsamples = [], [], [], []
        for ms in self:
            starttime.append(ms.starttime)
            endtime.append(ms.endtime)
            timepersample.append(ms.timepersample)
            numsamples.append(ms.numsamples)
        if np.any([len(np.unique(_tms)) > 1 for _tms in [starttime, endtime,
                                                timepersample, numsamples]]):
            logger.critical("Time information of MS {} does not match!".format(
                             ms.ms_filename))
        else:
            self.starttime = starttime[0]
            self.endtime = endtime[0]
            self.timepersample = timepersample[0]
            self.numsamples = numsamples[0]

    def get_times(self):
        """ Return array of times (ordered, with duplicates excluded). """
        return self.starttime + np.arange(self.numsamples) * self.timepersample

    def get_frequencies(self):
        """ Return array of frequencies (ordered, duplicates excluded). """
        sb_freq = np.array([ms.get_frequencies() for ms in self]).flatten()
        if len(sb_freq) != len(np.unique(sb_freq)):
            logger.warning('Some channels share the same frequency!')
        return np.sort(sb_freq)

    def set_stations(self):
        """ Set the station names and positions """
        stations, stationpositions = [], []
        for ms in self:
            for _sn, _sp in zip(ms.stations, ms.stationpositions):
                if _sn not in stations:
                    stations.append(_sn)
                    stationpositions.append(_sp)
        self.stations = np.array(stations)
        self.stationpositions = np.array(stationpositions)


    def reset_beam_keyword(self, colname='DATA'):
        """
        Unsets the LOFAR_APPLIED_BEAM_MODE keyword for the given column

        Parameters
        ----------
        colname : str, optional
            Name of column
        """
        for ms in self:
            with ms.table(readonly=False) as t:
                if colname in t.colnames() and 'LOFAR_APPLIED_BEAM_MODE' in t.getcolkeywords(colname):
                    t.putcolkeyword(colname, 'LOFAR_APPLIED_BEAM_MODE', 'None')

    #def make_dirty_image(self):

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
