#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Clock-operation: Creat soltab for clock-delay corruption.
"""
import numpy as np
from losoto.h5parm import h5parm
from ..lib_io import logger

logger.debug('Loading CLOCK module.')

def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename', 'corruptions.h5')
    seed = parser.getint(step, 'seed', default = 0)
    mode = parser.getstr(step, 'mode', default='lofar1')
    clockAmp = parser.getfloat(step, 'clockAmp', default = -1.) # neg. val : use default for lofar1/2
    clockOffset = parser.getfloat(step, 'clockOffset', default = -1.)
    clockOmega = parser.getfloat(step, 'clockOmega', default = 1.)
    parser.checkSpelling( step, ['h5parmFilename', 'seed', 'mode','clockAmp',
                                 'clockOffset', 'clockOmega'])
    return run(obs, h5parmFilename, seed, mode, clockAmp, clockOffset,
               clockOmega, step)

def get_station_delay(times, clockAmp, clockOffset, clockOmega):
    '''
    Get clock delay for one station. Only the remote and international 
    stations have an independent clock.
    
    Parameters
    ----------
    times : (n,) ndarray
    clockAmp : float, default = 7e-9 s
        Standard deviation of clock delay amplitude.
    clockOffset : float, default = 20e-9 s
        Standard deviation of clock delay offset.
    clockOmega: float, default = 1
        Frequency factor for clock drift oscillation.
    Returns
    -------
    delay : (n,) ndarray
        Time delay in seconds.
    '''
    time_delta = times - np.min(times)       
    clockAmp = np.random.normal(0.0, clockAmp)
    clockOffset = np.random.normal(0.0, clockOffset)
    clockOmega = np.random.normal(loc = clockOmega, scale = 0.15 * clockOmega)
    t0 = 57600*np.random.random()
    delay = clockAmp*np.sin(clockOmega*np.pi*(time_delta - t0)/7200) + clockOffset
    return delay


def run(obs, h5parmFilename, seed= 0, mode='lofar1', clockAmp=None,
        clockOffset=None, clockOmega=1.0, stepname='clock'):
    """
    Add clock delay Soltab to h5parm.
    
    Parameters
    ----------
    seed : unsigned int, optional. default = 0
        Set the random seed. Seed = 0 (default) will set no seed.
    mode : string, optional. default = lofar1
        Possible options are >lofar1< and >lofar2<. For lofar1, the clock delay will only be simulated for the remote
        stations. For lofar 2, the clock delay will be applied to all stations, but with a different amplitude depending
        on the distance of the station. If mode=lofar2, the values for clockAmp and clockOffset will be applied to the
         remote stations, while half of the given amplitude and offset is applied to the central stations.
    """
    # If provided, set random seed:
    if seed != 0:
        np.random.seed(int(seed))

    times = obs.get_times()
    ras, decs = obs.get_patch_coords()
    source_names = obs.get_patch_names()
    stations = obs.stations

    delays = np.zeros((len(times), len(stations)))

    if mode == 'lofar1':
        if clockAmp == -1.0:
            logger.info('clockAmp not specified. Using default value for lofar1.')
            clockAmp = 0.7e-9
        if clockOffset == -1.0:
            clockOffset = 2e-8
            logger.info('clockOffset not specified. Using default value for lofar1.')
        is_rs_list = [False if 'CS' in st else True for st in stations]
        # Get the delay for all of the CS to substract from the RS.
        cs_delay = get_station_delay(times, clockAmp, clockOffset, clockOmega)
        # Get delay for each individual RS:
        for i, is_rs in enumerate(is_rs_list):
            if is_rs:
                delays[:,i] = (get_station_delay(times, clockAmp, clockOffset,
                                                    clockOmega) - cs_delay )
            else:
                continue

    elif mode == 'lofar2':
        # make sure that LBA = HBA at the same station get the same delay!
        if clockAmp == -1.0:
            logger.info('clockAmp not specified. Using default value for lofar2.')
            clockAmp = 0.0825e-9 # for RS
        if clockOffset == -1.0:
            clockOffset = 0.117e-9 # for RS
            logger.info('clockOffset not specified. Using default value for lofar2.')
        # find hba + lba substations which are at the same staton, e.g. CS001HBA0 and CS001LBA
        superstations = np.sort(np.unique([st[:5] for st in stations]))

        for i, superstationname in enumerate(superstations):
            scalef = (0.2/0.35) if 'CS' in superstationname else 1.0 # use smaller delay for core stations
            temp_delay = get_station_delay(times, scalef*clockAmp, scalef*clockOffset,
                                                    clockOmega)
            for j, substationname in enumerate(stations):
                if substationname[:5] == superstationname:
                    delays[:,j] = temp_delay
    else:
        logger.error('Only \'lofar1\' and \'lofar2\' are valid options for option \'mode\'.')
        return 1
    # Write clock values to h5parm file as DP3 input
    ho = h5parm(h5parmFilename, readonly=False)
    if 'sol000' in ho.getSolsetNames():   
        solset = ho.getSolset('sol000')
    else:
        solset = ho.makeSolset(solsetName = 'sol000')

    # Definition: clock000 is delay, clock001 is pol misalignment
    if 'clock000' in solset.getSoltabNames(): 
        logger.info('''Solution-table clock000 is already present in
                 {}. It will be overwritten.'''.format(h5parmFilename + '/sol000'))  
        solset.getSoltab('clock000').delete()
        
    # h5parmpredict needs direction axis with directions from sky model.
    weights = np.ones_like(delays)
    st = solset.makeSoltab('clock', 'clock000', axesNames = ['time','ant'],
                           axesVals = [times, stations], vals = delays,
                           weights = weights)
    
    antennaTable = solset.obj._f_get_child('antenna')
    antennaTable.append(list(zip(*(stations, obs.stationpositions))))
    sourceTable = solset.obj._f_get_child('source')
    vals = [[ra, dec] for ra, dec in zip(ras, decs)]
    sourceTable.append(list(zip(*(source_names, vals))))

    soltabs = solset.getSoltabs()
    for st in soltabs:
        st.addHistory('CREATE (by CLOCK operation of LoSiTo from obs {0})'.format(h5parmFilename))
    ho.close()

    # Update DP3 predict parset
    obs.add_to_parset(stepname, 'clock000', h5parmFilename, DDE=False)

    return 0


