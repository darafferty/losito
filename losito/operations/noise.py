#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Noise operation for losito: adds Gaussian noise to a data column

import logging
import subprocess
from losito.lib_operations import *
import casacore.tables as pt

logging.debug('Loading NOISE module.')


def _run_parser(obs, parser, step):
    stddev = parser.getfloat( step, 'stddev')
    outputColumn = parser.getstr( step, 'outputColumn')

    parser.checkSpelling( step, ['stddev', 'outputColumn'])
    return run(obs, stddev, outputColumn)


def run(obs, stddev=7500.0, outputColumn='DATA'):
    """
    Adds Gaussian noise to a data column.

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    stddev : float, optional
        Standard deviation of noise
    outputColumn : str, optional
        Name of output column to which noise is added
    """
    # TODO: calculate stddev from the LOFAR specifications (for given baseline, etc)
    # See https://old.astron.nl/radio-observatory/astronomers/lofar-imaging-capabilities-sensitivity/sensitivity-lofar-array/sensiti
    myt = pt.table(obs.ms_filename, readonly=False)
    simul_data = myt.getcol(outputColumn)
    myreal = np.random.normal(0, stddev, simul_data.shape)
    myimag = np.random.normal(0, stddev, simul_data.shape)
    noisedata = myreal + 1.j*myimag
    myt.putcol(outputColumn, simul_data+noisedata)
    myt.close()

    return 0
