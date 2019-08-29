"""
Definition of the Observation class
set
"""
import os
import sys
import logging
import subprocess
try:
    import casacore.tables as pt
    has_casacore = True
except ImportError:
    has_casacore = False
import numpy as np
from astropy.time import Time
import lsmtool


class Observation(object):
    """
    The Observation object holds info on the observation and its processing parameters.
    E.g.:
        - various observation parameters
        - DPPP parset parameters
        - sky model file
        - etc.

    Parameters
    ----------
    ms_filename : str
        Filename of the MS file.
    skymodel_filename : str
        Filename of the sky model file.
    starttime : float, optional
        The start time of the observation (in MJD seconds) to be used during processing.
        If None, the start time is the start of the MS file.
    endtime : float, optional
        The end time of the observation (in MJD seconds) to be used during processing.
        If None, the end time is the end of the MS file.
    """
    def __init__(self, ms_filename, skymodel_filename, starttime=None, endtime=None):
        self.ms_filename = str(ms_filename)
        self.skymodel_filename = str(skymodel_filename)
        self.sourcedb_filename = self.skymodel_filename + '.sourcedb'
        self.parset_filename = self.ms_filename + '.parset'
        self.name = os.path.basename(self.ms_filename)
        self.log = logging.getLogger('losito:{}'.format(self.name))
        self.starttime = starttime
        self.endtime = endtime
        self.parset_parameters = {}

        # Scan the MS and store various observation parameters
        self.scan_ms()

        # Load the sky model
        self.load_skymodel()

        # Initialize the parset
        self.initialize_parset_parameters()

    def scan_ms(self):
        """
        Scans input MS and stores info
        """
        if not has_casacore:
            self.goesto_endofms = True
            return

        # Get time info
        tab = pt.table(self.ms_filename, ack=False)
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
        tab.close()

        # Get frequency info
        sw = pt.table(self.ms_filename+'::SPECTRAL_WINDOW', ack=False)
        self.referencefreq = sw.col('REF_FREQUENCY')[0]
        self.startfreq = np.min(sw.col('CHAN_FREQ')[0])
        self.endfreq = np.max(sw.col('CHAN_FREQ')[0])
        self.numchannels = sw.col('NUM_CHAN')[0]
        self.channelwidth = sw.col('CHAN_WIDTH')[0][0]
        sw.close()

        # Get pointing info
        obs = pt.table(self.ms_filename+'::FIELD', ack=False)
        self.ra = np.degrees(float(obs.col('REFERENCE_DIR')[0][0][0]))
        if self.ra < 0.:
            self.ra = 360.0 + (self.ra)
        self.dec = np.degrees(float(obs.col('REFERENCE_DIR')[0][0][1]))
        obs.close()

        # Get station names, positions, and diameter
        ant = pt.table(self.ms_filename+'::ANTENNA', ack=False)
        self.stations = ant.col('NAME')[:]
        self.diam = float(ant.col('DISH_DIAMETER')[0])
        self.stationpositions = ant.getcol('POSITION')
        if 'HBA' in self.stations[0]:
            self.antenna = 'HBA'
        elif 'LBA' in self.stations[0]:
            self.antenna = 'LBA'
        else:
            self.log.warning('Antenna type not recognized (only LBA and HBA data '
                             'are supported at this time)')
        ant.close()

        # Find mean elevation and FOV
        el_values = pt.taql("SELECT mscal.azel1()[1] AS el from "
                            + self.ms_filename + " limit ::10000").getcol("el")
        self.mean_el_rad = np.mean(el_values)

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

    def make_sourcedb(self):
        """
        Makes the sourcedb for DPPP from the sky model
        """
        cmd = ['makesourcedb', 'in={}'.format(self.skymodel_filename),
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
        skymodel = lsmtool.load(self.skymodel_filename)
        if not skymodel.hasPatches:
            skymodel.group('every')
        skymodel.setPatchPositions(method='wmean')
        logging.root.setLevel(old_level)
        self.skymodel = skymodel

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

    def convert_mjd(self, mjd_sec):
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
