#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Beam operation for losito: corrupts with the beam
"""
from losito.lib_operations import logger

logger.debug('Loading BEAM module.')


def _run_parser(obs, parser, step):
    mode = parser.getstr( step, 'mode', 'default')
    usechannelfreq = parser.getbool( step, 'usechannelfreq', True)
    onebeamperpatch = parser.getbool( step, 'onebeamperpatch', False)
    onebeamperpatch = parser.getbool( step, 'onebeamperpatch', False)
    predictType = parser.getstr( step, 'predictType', 'h5parmpredict')
    parser.checkSpelling( step, ['mode', 'usechannelfreq', 'onebeamperpatch', 'predictType'])
    return run(obs, mode, usechannelfreq, onebeamperpatch, predictType)


def run(obs, mode='default', usechannelfreq=True, onebeamperpatch=False,
        predictType='h5parmpredict'):
    """
    Corrupts with the beam model.

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    mode : str, optional
        Beam mode to use: 'default' (= array factor + element), 'array_factor',
        or 'element'. If predictType = 'idgpredict', only the full beam
        (array factor + element) is used
    usechannelfreq : bool, optional
        If True, compute the beam for each channel of the measurement set separately
    onebeamperpatch : bool, optional
        If True, compute the beam only for the center of each patch. If predictType =
        'idgpredict', this option is not used
    predictType : str, optional
        Type of DP3 predict command: one of "h5parmpredict", "predict",
        "idgpredict", or "wgridderpredict" (not yet supported)
    """
    if mode not in ['default', 'array_factor', 'element']:
        logger.error('mode "{}" not understood'.format(mode))
        return 1
    if predictType == "wgridderpredict":
        logger.error('Beam corruptions are not supported when using predict '
                     'type "wgridderpredict"')
        return 1

    # Update predict parset parameters for the obs
    if predictType == "idgpredict":
        obs.parset_parameters['predict.aterms'] = '[beam_aterm]'
        obs.parset_parameters['predict.beam_aterm.type'] = 'beam'
        obs.parset_parameters['predict.beam_aterm.usechannelfreq'] = usechannelfreq
    else:
        obs.parset_parameters['predict.usebeammodel'] = True
        obs.parset_parameters['predict.beammode'] = mode
        obs.parset_parameters['predict.usechannelfreq'] = usechannelfreq
        obs.parset_parameters['predict.onebeamperpatch'] = onebeamperpatch

    return 0
