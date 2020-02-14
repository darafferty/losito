#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 15:10:06 2020

@author: p1uy068
"""
import os
import logging as log
import numpy as np
from losoto.h5parm import h5parm

log.debug('Loading CLOCK module.')

def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename', )
    # TODO seed, maybe add amplitude options       
    parser.checkSpelling( step, ['h5parmFilename'])  
    return run(obs, h5parmFilename, step)

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


def run(obs, h5parmFilename, stepname='rm'): 
    '''
    Add rotation measure Soltab to a TEC h5parm.
    '''
    stations = obs.stations    
    times = obs.get_times()
    ras, decs = obs.get_patch_coords()
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
    #np.save('delays.npy', delays)
    #if os.path.exists(h5parmFilename):
    #    log.info(h5parmFilename +' already exists. Overwriting file...')
    #    os.remove(h5parmFilename)        
    
    # Write clock values to h5parm file as DPPP input    
    ho = h5parm(h5parmFilename, readonly=False)
    print(ho.getSolsetNames())
    if 'sol000' in ho.getSolsetNames():   
        solset = ho.getSolset('sol000')
    else:
        solset = ho.makeSolset(solsetName = 'sol000')
        
    if 'clock000' in solset.getSoltabNames(): 
        log.info('''Solution-table clock000 is already present in
                 {}. It will be overwritten.'''.format(h5parmFilename + '/sol000'))  
        solset.getSoltab('clock000').delete()
        
    delays = delays[..., np.newaxis]
    weights = np.ones_like(delays)

    st = solset.makeSoltab('clock', 'clock000', axesNames = ['time','ant','dir'],
                           axesVals = [times, stations, ['[pointing]']], vals = delays,
                           weights = weights)   
    
    antennaTable = solset.obj._f_get_child('antenna')
    antennaTable.append(list(zip(*(stations, obs.stationpositions))))
    sourceTable = solset.obj._f_get_child('source')
    vals = [obs.ra, obs.dec]
    sourceTable.append([('[pointing]', vals)])

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
        
    if 'predict.applycal.correction' not in obs.parset_parameters:
        obs.parset_parameters['predict.applycal.correction'] = 'clock000' 
        
    obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'clock000'
    obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename

    return 0


