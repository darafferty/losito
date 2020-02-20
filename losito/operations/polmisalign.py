#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging as log
import numpy as np
from losoto.h5parm import h5parm
"""
Polarization misalignment operation for losito: simulate a constant station-
and polarization-dependent delay."""
log.debug('Loading POLMISALIGN module.')

def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename', )
    seed = parser.getint(step, 'seed', default = 0)

    parser.checkSpelling( step, ['h5parmFilename', 'seed'])  
    return run(obs, h5parmFilename, seed, step)


def run(obs, h5parmFilename, seed = 0, stepname='pol_misalign'): 
    '''
    Simulate polarization misalignment.
    
    Parameters
    ----------
    seed : unsigned int, optional. default = 0
        Set the random seed. Seed = 0 (default) will set no seed.
    '''
    if seed != 0: # Set random seed if provided.
        np.random.seed(int(seed))
        
    stations = obs.stations    
    ras, decs = obs.get_patch_coords()
    source_names = obs.get_patch_names()
    pol = np.array(['XX', 'YY'])
    
    # draw time delays and reference them w.r.t. station 1.
    # Polarization Y is delayed w.r.t. X
    delays = np.zeros((2, len(stations)))  
    delays[1] = np.random.normal(0, 1e-9, len(stations))    
    delays[1] -= delays[1,0]
    delays = np.repeat(delays[...,np.newaxis], len(source_names), axis = -1)    
    weights = np.ones_like(delays)

    # Write polarization misalignment values to h5parm file as DPPP input.
    ho = h5parm(h5parmFilename, readonly=False)
    if 'sol000' in ho.getSolsetNames():   
        solset = ho.getSolset('sol000')
    else:
        solset = ho.makeSolset(solsetName = 'sol000')
    
    # Definition: clock001 is pol misalignment, clock000 is clock delay.
    if 'clock001' in solset.getSoltabNames(): 
        log.info('''Solution-table clock001 is already present in
                 {}. It will be overwritten.'''.format(h5parmFilename + '/clock001'))  
        solset.getSoltab('clock001').delete()

    st = solset.makeSoltab('clock', 'clock001', axesNames = ['pol','ant', 'dir'],
                           axesVals = [pol, stations, source_names], 
                           vals = delays, weights = weights)   
    
    antennaTable = solset.obj._f_get_child('antenna')
    antennaTable.append(list(zip(*(stations, obs.stationpositions))))
    sourceTable = solset.obj._f_get_child('source')
    vals = [obs.ra, obs.dec]
    sourceTable.append([('[pointing]', vals)])

    soltabs = solset.getSoltabs()
    for st in soltabs:
        st.addHistory('CREATE (by POLMISALIGN operation of LoSiTo from obs {0})'.format(h5parmFilename))
    ho.close()

    # Update predict parset parameters for the obs
    obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
    if 'predict.applycal.steps' in obs.parset_parameters:
        obs.parset_parameters['predict.applycal.steps'].append(stepname)
    else:
        obs.parset_parameters['predict.applycal.steps'] = [stepname]    
        
    obs.parset_parameters['predict.applycal.correction'] = 'clock001'         
    obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'clock001'
    obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename

    return 0



    
   
