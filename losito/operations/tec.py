#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TEC operation for losito: creates h5parm with TEC values from TEC FITS cube


import logging
from losito.lib_operations import *

logging.debug('Loading TEC module.')


def _run_parser(obs, parser, step):
    fitsFilename = parser.getstr( step, 'fitsFilename')
    h5parmFilename = parser.getstr( step, 'h5parmFilename', fitsFilename+'.h5parm')

    parser.checkSpelling( step, ['fitsFilename', 'h5parmFilename'])
    return run(obs, fitsFilename, h5parmFilename)


def run(obs, fitsFilename, h5parmFilename):
    """
    Creates h5parm with TEC values from TEC FITS cube.

    Parameters
    ----------
    fitsFilename : str
        Filename of input FITS cube with dTEC solutions.
    h5parmFilename : str
        Filename of output h5parm file.
    """
    # Get RA, Dec of sky model components
    ra, dec = obs.get_coords()

    # Get solutions at these coordinates from FITS cube

    # Make h5parm with solutions and write to disk

    # Update predict parset parameters for the obs
    # E.g.,
    # obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
    # obs.parset_parameters['predict.applycal.steps'].append('tec')
    # obs.parset_parameters['predict.applycal.tec.correction'] = 'tec000'

    return 0
