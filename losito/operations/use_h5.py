#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 14:01:05 2020
"""
import logging as log
log.debug('Loading USE_H5 module.')

R_earth = 6364.62e3

def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename')
    corruption = parser.getstr(step, 'corruption')
    parser.checkSpelling( step, ['h5parmFilename', 'corruption'])
    return run(obs, h5parmFilename, corruption, step)


def run(obs, h5parmFilename, corruption, stepname='use_h5'): 
    '''
    Add either a clock000, tec000 or rotationmeasure000 from a matching .h5 
    file to the simulation.
    '''
    corruption = corruption.lower()
    if corruption == 'clock':
        # Update predict parset parameters for the obs
        obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
        if 'predict.applycal.steps' in obs.parset_parameters:
            obs.parset_parameters['predict.applycal.steps'].append(stepname)
        else:
            obs.parset_parameters['predict.applycal.steps'] = [stepname]
        obs.parset_parameters['predict.applycal.correction'] = 'clock000'
        obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'clock000'
        obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename
        log.info('Including solution-table clock000 in {} in simulation.'.format(
                  h5parmFilename))
        return 0
    elif corruption == 'tec':
        # Update predict parset parameters for the obs
        obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
        if 'predict.applycal.steps' in obs.parset_parameters:
            obs.parset_parameters['predict.applycal.steps'].append(stepname)
        else:
            obs.parset_parameters['predict.applycal.steps'] = [stepname]
        obs.parset_parameters['predict.applycal.correction'] = 'tec000'
        obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'tec000'
        obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename
        log.info('Including solution-table tec000 in {} in simulation.'.format(
                  h5parmFilename))
        return 0
    
    elif corruption == 'rm': 
          # Update predict parset parameters for the obs
        obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
        if 'predict.applycal.steps' in obs.parset_parameters:
            obs.parset_parameters['predict.applycal.steps'].append(stepname)
        else:
            obs.parset_parameters['predict.applycal.steps'] = [stepname]
        obs.parset_parameters['predict.applycal.correction'] = 'rotationmeasure000'
        obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'rotationmeasure000'
        obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename
        log.info('Including solution-table rotationmeasurem000 in {} in simulation.'.format(
          h5parmFilename))
        return 0
        
    else: 
        log.warning('''Corruption {} is not supported. Please choose <clock>,
                    <tec> or <rm>.'''.format(corruption))
        return 1
        
