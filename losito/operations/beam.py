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
    parser.checkSpelling( step, ['h5parmFilename', 'mode', 'usechannelfreq', 'onebeamperpatch'])
    return run(obs, mode, usechannelfreq, onebeamperpatch)


def run(obs,   mode='default', usechannelfreq=True, onebeamperpatch=False):
    """
    Corrupts with the beam model.

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    mode : str, optional
        Beam mode to use: 'default' (= array factor + element), 'array_factor',
        or 'element'
    usechannelfreq : bool, optional
        If True, compute the beam for each channel of the measurement set separately
    onebeamperpatch : bool, optional
        If True, compute the beam only for the center of each patch.
    """
    if mode not in ['default', 'array_factor', 'element']:
        logger.error('mode "{}" not understood'.format(mode))
        return 1

    # Update predict parset parameters for the obs
    obs.parset_parameters['predict.usebeammodel'] = True
    obs.parset_parameters['predict.beammode'] = mode
    obs.parset_parameters['predict.usechannelfreq'] = usechannelfreq
    obs.parset_parameters['predict.onebeamperpatch'] = onebeamperpatch

    return 0
