#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Noise operation for losito: adds Gaussian noise to a data column
"""
import os, argparse
import pkg_resources
import numpy as np
from scipy.interpolate import interp1d
from losito.lib_io import progress, logger
from losito.lib_observation import MS

logger.debug('Loading NOISE module.')


def _run_parser(obs, parser, step):
    column = parser.getstr(step, 'outputColumn', 'DATA')
    factor = parser.getfloat(step, 'factor', 1.0)
    parser.checkSpelling( step, ['outputColumn','factor'])
    return run(obs, column, factor)

def SEFD(ms, station1, station2, freq):
    '''
    Return the system equivalent flux density (SEFD) for all rows and a
    single fequency channel.
    The values for the SEFD were derived from van Haarlem
    et al. (2013).

    Parameters
    ----------
    ms : MS-object
    station1 : (n,) ndarray, dtype = int
        ANTENNA1 indices.
    station2 : (n,) ndarray, dtpe = int
        ANTENNA2 indices.
    freq : float
        Channel frequency in Hz.
    Returns
    -------
    SEFD : (n,) ndarray
        SEFD in Jansky.
    '''

    def interp_sefd(freq, antennamode):
        # Load antennatype datapoints and interpolate, then reevaluate at freq.
        sefd_pth = pkg_resources.resource_filename('losito', 'data/noise/SEFD_{}.csv'.format(antennamode))
        points = np.loadtxt(sefd_pth, dtype=float, delimiter=',')
        # Lin. extrapolation, so edge band noise is not very accurate.
        fun = interp1d(points[:, 0], points[:, 1], fill_value='extrapolate',
                        kind='linear')
        return fun(freq)

    if ms.antennatype in ['LBA_INNER', 'LBA_OUTER', 'LBA_ALL']:
        SEFD = interp_sefd(freq, ms.antennatype)
        return np.repeat(SEFD, len(station1))  # SEFD same for all BL
    elif 'HBA' in ms.antennatype:
        # For HBA, the SEFD differs between core and remote stations
        names = np.array([_n[0:2] for _n in ms.stations])
        CSids = ms.stationids[np.where(names =='CS')]
        lim = np.max(CSids)  # this id separates the core/remote stations

        # The SEFD for 1 BL is the sqrt of the products of the SEFD per station
        SEFD_cs = interp_sefd(freq, 'HBA_CS')
        SEFD_rs = interp_sefd(freq, 'HBA_RS')
        SEFD_s1 = np.where(station1 <= lim, SEFD_cs, SEFD_rs)
        SEFD_s2 = np.where(station2 <= lim, SEFD_cs, SEFD_rs)
        return np.sqrt(SEFD_s1 * SEFD_s2)
    else:
        logger.error('Stationtype "{}" unknown.'.format(ms.stationtype))
        return 1

def add_noise_to_ms(ms, column='DATA', factor=1.0):
    # TODO: ensure eta = 1 is appropriate
    tab = ms.table(readonly=False)
    eta = 0.95  # system efficiency. Roughly 1.0

    chan_width = ms.channelwidth
    freq = ms.get_frequencies()
    ant1 = tab.getcol('ANTENNA1')
    ant2 = tab.getcol('ANTENNA2')
    exposure = ms.timepersample
    # std = eta * SEFD(ms, ant1, ant2, freq) #TODO
    # Iterate over frequency channels to save memory.
    for i, nu in enumerate(freq):
        # find correct standard deviation from SEFD
        std = factor * eta * SEFD(ms, ant1, ant2, nu)
        std /= np.sqrt(2 * exposure * chan_width[i])
        # draw complex valued samples of shape (row, corr_pol)
        noise = np.random.normal(loc=0, scale=std, size=[4, *np.shape(std)]).T
        noise = noise + 1.j * np.random.normal(loc=0, scale=std, size=[4, *np.shape(std)]).T
        noise = noise[:, np.newaxis, :]
        prediction = tab.getcolslice(column, blc=[i, -1], trc=[i, -1])
        tab.putcolslice(column, prediction + noise, blc=[i, -1], trc=[i, -1])
    tab.close()

    return 0

def run(obs, column='DATA', factor=1.0):
    """
    Adds Gaussian noise to a data column. Scale of the noise, frequency-
    and station-dependency are calculated according to 'Synthesis Imaging
    in Radio Astronomy II' (1999) by Taylor et al., page 175.

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    column : str, optional. Default = DATA
        Name of column to which noise is added
    factor : float, optional. Default = 1.0
        Scaling factor to change the noise level.
    """
    s = obs.scheduler
    if s.qsub: # add noise in parallel on multiple nodes
        for i, ms in enumerate(obs):
            progress(i, len(obs), status='Estimating noise')  # progress bar
            thisfile = os.path.abspath(__file__)
            cmd = 'python {} --msin={} --start={} --end={} --column={} --factor={}'.format(thisfile,
                                 ms.ms_filename, ms.starttime, ms.endtime, column, factor)
            s.add(cmd, commandType='python', log='losito_add_noise', processors=1)
        result = s.run(check=True)
        return result
    else: # add noise linear on one cpu
        results = []
        for i, ms in enumerate(obs):
            progress(i, len(obs), status='Estimating noise')  # progress bar
            results.append(add_noise_to_ms(ms, column, factor))
        return sum(results)

if __name__ == '__main__':
    # This file can also be executed directly for a single MS.
    parser = argparse.ArgumentParser(description='Executable of the LoSiTo-noise operation')
    parser.add_argument('--msin', help='MS file prefix', type=str)
    parser.add_argument('--starttime', help='MJDs starttime', type=float)
    parser.add_argument('--endtime', help='MJDs endtime', type=float)
    parser.add_argument('--column', help='Column', default='DATA', type=str)
    parser.add_argument('--factor', help='Factor', default=1.0, type=float)
    # Parse parset
    args = parser.parse_args()
    ms = MS(args.msin, args.starttime, args.endtime)
    add_noise_to_ms(ms, args.column, args.factor)
