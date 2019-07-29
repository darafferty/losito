"""
Definition of the Observation class
set
"""
import os
import sys
import logging
try:
    import casacore.tables as pt
    has_casacore = True
except ImportError:
    has_casacore = False
import numpy as np
from astropy.time import Time


class Observation(object):
    """
    The Observation object contains various MS-related parameters, a DPPP parset, etc.

    Parameters
    ----------
    ms_filename : str
        Filename of the MS file
    skymodel_filename : str
        Filename of the sky model file
    starttime : float, optional
        The start time of the observation (in MJD seconds). If None, the start time
        is the start of the MS file
    endtime : float, optional
        The end time of the observation (in MJD seconds). If None, the end time
        is the end of the MS file
    """
    def __init__(self, ms_filename, skymodel_filename, starttime=None, endtime=None):
        self.ms_filename = str(ms_filename)
        self.skymodel_filename = str(skymodel_filename)
        self.parset_filename = self.ms_filename+'.parset'
        self.name = os.path.basename(self.ms_filename)
        self.log = logging.getLogger('simobs:{}'.format(self.name))
        self.starttime = starttime
        self.endtime = endtime
        self.parset_parameters = {}
        self.scan_ms()

    def scan_ms(self):
        """
        Scans input MS and stores info
        """
        if not has_casacore:
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
        self.numsamples = int(np.ceil((self.endtime - self.starttime) / self.timepersample)) + 1
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

        # Get station names and diameter
        ant = pt.table(self.ms_filename+'::ANTENNA', ack=False)
        self.stations = ant.col('NAME')[:]
        self.diam = float(ant.col('DISH_DIAMETER')[0])
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
        Sets basic DPPP parset parameters for predict
        """
        self.parset_parameters['predict.type'] = 'h5parmpredict'
        self.parset_parameters['predict.sourcedb'] = self.skymodel_filename
        self.parset_parameters['predict.operation'] = 'replace'

    def write_parset(self):
        """
        Writes the DPPP parset parameters to a text file
        """
        pass

    def get_coords(self):
        """
        Returns (RA, Dec) in degrees for patches in the sky model
        """
        pass
