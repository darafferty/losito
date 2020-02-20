#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Clock-operation: Creat soltab for clock-delay corruption.
"""
import logging as log
import numpy as np
from losoto.h5parm import h5parm

log.debug('Loading CLOCK module.')

def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename', )
    seed = parser.getint(step, 'seed', default = 0)
    
    parser.checkSpelling( step, ['h5parmFilename', 'seed'])  
    return run(obs, h5parmFilename, seed, step)

def remote_station_delay(times):
    '''
    Get clock delay for one station. Only the remote and international 
    stations have an indipendent clock.
    
    Parameters
    ----------
    times : (n,) ndarray

    Returns
    -------
    delay : (n,) ndarray
        Time delay w.r.t. central stations in seconds.
    '''
    time_delta = times - np.min(times)       
    amp = np.random.normal(0.0, 0.7e-8) 
    const = np.random.normal(0, 2e-8)
    omega = np.random.normal(loc = 1.0, scale = 0.15)
    t0 = 28800*np.random.random()
    delay = amp*np.sin(omega*np.pi*(time_delta - t0)/7200) + const
    return delay


def run(obs, h5parmFilename, seed = 0, stepname='clock'): 
    '''
    Add clock delay Soltab to h5parm.
    
    Parameters
    ----------
    seed : unsigned int, optional. default = 0
        Set the random seed. Seed = 0 (default) will set no seed.
    '''
    # If provided, set random seed:
    if seed != 0:
        np.random.seed(int(seed))
    stations = obs.stations    
    times = obs.get_times()
    ras, decs = obs.get_patch_coords()
    source_names = obs.get_patch_names()
    is_rs_list = [False if 'CS' in st else True for st in stations]
    delays = np.zeros((len(times), len(stations)))
    
    # Get the delay for all of the CS to substract from the RS.
    # This will make the TS delays partially correlated.
    cs_delay = remote_station_delay(times)
    
    # Get delay for each individual RS:
    for i, is_rs in enumerate(is_rs_list):
        if is_rs:
            delays[:,i] = remote_station_delay(times) - cs_delay            
        else:
            continue
    
    # Write clock values to h5parm file as DPPP input    
    ho = h5parm(h5parmFilename, readonly=False)
    if 'sol000' in ho.getSolsetNames():   
        solset = ho.getSolset('sol000')
    else:
        solset = ho.makeSolset(solsetName = 'sol000')
        
    # Definition: clock000 is delay, clock001 is pol misalignment
    if 'clock000' in solset.getSoltabNames(): 
        log.info('''Solution-table clock000 is already present in
                 {}. It will be overwritten.'''.format(h5parmFilename + '/sol000'))  
        solset.getSoltab('clock000').delete()
        
    # h5parmpredict needs direction axis with directions from sky model.
    delays = np.repeat(delays[...,np.newaxis], len(source_names), axis = -1)
    weights = np.ones_like(delays)    
    st = solset.makeSoltab('clock', 'clock000', axesNames = ['time','ant','dir'],
                          axesVals = [times, stations, source_names], vals = delays,
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

    # Update predict parset parameters for the obs
    obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
    if 'predict.applycal.steps' in obs.parset_parameters:
        obs.parset_parameters['predict.applycal.steps'].append(stepname)
    else:
        obs.parset_parameters['predict.applycal.steps'] = [stepname]    
    obs.parset_parameters['predict.applycal.correction'] = 'clock000'         
    obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'clock000'
    obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename

    return 0


