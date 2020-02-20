#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Add an existing solution-table to the DPPP prediction step.
"""
import logging as log
log.debug('Loading USE_H5 module.')

R_earth = 6364.62e3

def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename')
    corruption = parser.getstr(step, 'corruption')
    parser.checkSpelling( step, ['h5parmFilename', 'corruption'])
    return run(obs, h5parmFilename, corruption, step)


def include_soltab(obs, h5parmFilename, soltab, step):    
     # Update predict parset parameters for the obs
    obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
    if 'predict.applycal.steps' in obs.parset_parameters:
        obs.parset_parameters['predict.applycal.steps'].append(step)
    else:
        obs.parset_parameters['predict.applycal.steps'] = [step]
    obs.parset_parameters['predict.applycal.correction'] = soltab 
    obs.parset_parameters['predict.applycal.{}.correction'.format(step)] = soltab
    obs.parset_parameters['predict.applycal.{}.parmdb'.format(step)] = h5parmFilename
    log.info('Including solution-table {} in {} in simulation.'.format(soltab, 
      h5parmFilename))
    
def run(obs, h5parmFilename, corruption, step='use_h5'): 
    '''
    Add either a clock000 (for clock delay), clock001 (for polarization
    misalignment), tec000 or rotationmeasure000 from a matching .h5 
    file to the simulation.
    '''
    corruption = corruption.lower()
    if corruption == 'clock':
        step = 'clock'
        soltab = 'clock000'
        # Add soltab to DPPP parset
        include_soltab(obs, h5parmFilename, soltab, step)
        return 0
    
    elif corruption == 'polmisalign':
        step = 'polmisalign'
        soltab = 'clock001' 
        # Add soltab to DPPP parset
        include_soltab(obs, h5parmFilename, soltab, step)
        return 0   
    
    elif (corruption == 'rm') or (corruption == 'rotationmeasure'):
        step = 'rm'
        soltab = 'rotationmeasure000'
        # Add soltab to DPPP parset
        include_soltab(obs, h5parmFilename, soltab, step)
        return 0
    
    elif corruption == 'tec': 
        step = 'tec'
        soltab = 'tec000'
        # Add soltab to DPPP parset
        include_soltab(obs, h5parmFilename, soltab, step)
        return 0
        
    else: 
        log.warning('''Corruption {} is not supported. Please choose <clock>,
                    <polmisalign>, <tec> or <rm>.'''.format(corruption))
        return 1
        

