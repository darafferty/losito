#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Add an existing solution-table to the DP3 prediction step.
"""
from ..lib_io import logger
logger.debug('Loading USE_H5 module.')

R_earth = 6364.62e3

def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename')
    corruption = parser.getstr(step, 'corruption')
    parser.checkSpelling( step, ['h5parmFilename', 'corruption'])
    return run(obs, h5parmFilename, corruption, step)


def run(obs, h5parmFilename, corruption, step='use_h5'): 
    '''
    Add either a clock000 (clock delay), clock001 (polarization
    misalignment), amplitude000 (bandpass), tec000 (iono 1st order) 
    or rotationmeasure000 (iono 2nd order) from a matching h5parm 
    file to the simulation.
    '''
    corruption = corruption.lower()
    if corruption == 'clock':
        # Add soltab to DP3 parset
        if not 'applycal' in obs.parset_parameters['steps']:
            obs.parset_parameters['steps'].append('applycal')
        obs.add_to_parset(step, 'clock000', h5parmFilename, DDE=False)
        return 0
    elif corruption == 'polmisalign':
        if not 'applycal' in obs.parset_parameters['steps']:
            obs.parset_parameters['steps'].append('applycal')
        obs.add_to_parset(step, 'clock001', h5parmFilename, DDE=False)
        return 0
    elif corruption == 'bandpass':
        if not 'applycal' in obs.parset_parameters['steps']:
            obs.parset_parameters['steps'].append('applycal')
        obs.add_to_parset(step, 'amplitude000', h5parmFilename, DDE=False)
        return 0
    elif (corruption == 'rm') or (corruption == 'rotationmeasure'):
        obs.add_to_parset(step, 'rotationmeasure000', h5parmFilename)
        return 0
    elif corruption == 'tec':
        obs.add_to_parset(step, 'tec000', h5parmFilename)
        return 0
    else:
        logger.warning('''Corruption {} is not supported. Please choose <clock>,
                    <polmisalign>, <bandpass>, <tec> or <rm>.'''.format(corruption))
        return 1
        
