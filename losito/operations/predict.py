#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Predict operation for losito: runs DPPP to predict a sky model with corruptions
"""
import logging
import subprocess
from losito.lib_operations import *
import multiprocessing

logging.debug('Loading PREDICT module.')


def _run_parser(obs, parser, step):
    outputColumn = parser.getstr( step, 'outputColumn', 'DATA')
    predictType = parser.getstr( step, 'predictType', 'h5parmpredict')    
    ncpu = parser.getint( '_global', 'ncpu', 0)
    parser.checkSpelling( step, ['outputColumn', 'predictType'])
    
    return run(obs, outputColumn, predictType, ncpu)


def run(obs, outputColumn='DATA', predictType='h5parmpredict', ncpu=0):
    """
    Runs DPPP to predict a sky model. Prediction type h5parmpredict will
    apply corruptions stored in a .h5parmdb (default).
    Prediction type predict will generate uncorrupted ground truth 
    visibilities.

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    outputColumn : str, optional
        Name of output column
    predictType : str, optional
        Type of DPPP predict command
    ncpu : int, optional
        Number of cpu to use, by default all available.
    """
    # Make sourcedb from sky model
    obs.make_sourcedb()

    # Set parset parameters and write parset to file
    obs.parset_parameters['steps'] = '[predict]'
    obs.parset_parameters['numthreads'] = ncpu    
    obs.parset_parameters['predict.type'] = predictType
    obs.parset_parameters['predict.sourcedb'] = obs.sourcedb_filename
    obs.parset_parameters['predict.operation'] = 'replace'
    obs.parset_parameters['msout.datacolumn'] = outputColumn
    obs.make_parset()

    # Run DPPP
    cmd = ['DPPP', obs.parset_filename]
    result = subprocess.call(cmd)

    # Return result
    return result
