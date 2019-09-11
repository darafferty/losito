#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Noise operation for losito: adds Gaussian noise to a data column

import logging
from losito.lib_operations import *
import casacore.tables as pt
import numpy as np

logging.debug('Loading NOISE module.')


def _run_parser(obs, parser, step):
    stddev = parser.getfloat( step, 'stddev', 1e-4)
    column = parser.getstr( step, 'outputColumn', 'DATA')

    parser.checkSpelling( step, ['stddev', 'column'])
    return run(obs, stddev, column)


def run(obs, stddev=1e-4, column='DATA'):
    """
    Adds Gaussian noise to a data column.

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    stddev : float, optional
        Standard deviation of noise
    column : str, optional
        Name of column to which noise is added
    """
    # TODO: calculate stddev from the LOFAR specifications (for given baseline, etc)
    # See https://old.astron.nl/radio-observatory/astronomers/lofar-imaging-capabilities-sensitivity/sensitivity-lofar-array/sensiti
    myt = pt.table(obs.ms_filename, readonly=False)
    simul_data = myt.getcol(column)
    myreal = np.random.normal(0, stddev, simul_data.shape)
    myimag = np.random.normal(0, stddev, simul_data.shape)
    noisedata = myreal + 1.j*myimag
    myt.putcol(column, simul_data+noisedata)
    myt.close()

    return 0
