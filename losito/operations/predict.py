#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Predict operation for losito: runs DPPP to predict a sky model with corruptions
"""
import logging
import subprocess
import casacore.tables as pt


logging.debug('Loading PREDICT module.')

def _run_parser(obs, parser, step):
    outputColumn = parser.getstr( step, 'outputColumn', 'DATA')
    predictType = parser.getstr( step, 'predictType', 'h5parmpredict')
    resetWeights = parser.getbool( step, 'resetWeights', True)
    ncpu = parser.getint( '_global', 'ncpu', 0)
    parser.checkSpelling( step, ['outputColumn', 'resetWeights',
                                 'predictType'])

    return run(obs, outputColumn, predictType, resetWeights, ncpu)


def run(obs, outputColumn='DATA', predictType='h5parmpredict',
        resetWeights=True, ncpu=0):
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
    resetWeights : bool, optional
        Whether to reset the entries in WEIGHT_SPECTRUM column
    ncpu : int, optional
        Number of cpu to use, by default all available.
    """
    # reset weights if specified (default).
    if resetWeights:
        logging.info('Reset entries in WEIGHT_SPECTRUM...')
        for ms in obs:
            pt.taql("UPDATE {0} SET WEIGHT_SPECTRUM=1.0".format(ms.ms_filename))

    # Make sourcedb from sky model
    obs.make_sourcedb()

    # Set parset parameters and write parset to file
    for ms in obs:
        ms.parset_parameters['steps'] = '[predict]'
        ms.parset_parameters['numthreads'] = ncpu
        ms.parset_parameters['predict.type'] = predictType
        ms.parset_parameters['predict.sourcedb'] = obs.sourcedb_filename
        ms.parset_parameters['predict.operation'] = 'replace'
        ms.parset_parameters['msout.datacolumn'] = outputColumn
        ms.make_parset()
        # Ensure that the LOFAR_APPLIED_BEAM_MODE keyword is unset (otherwise DPPP may
        # complain that the beam has already been applied)
        ms.reset_beam_keyword(outputColumn)

    # Run DPPP
    # TODO run this on multiple cluster nodes!
    results = []
    for ms in obs:
        cmd = ['DPPP', ms.parset_filename]
        results.append(subprocess.call(cmd))

    # Ensure again that the LOFAR_APPLIED_BEAM_MODE keyword is unset
    for ms in obs:
        ms.reset_beam_keyword(outputColumn)

    # Return result
    return sum(results)
