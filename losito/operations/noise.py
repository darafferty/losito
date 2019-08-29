#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Noise operation for losito: adds Gaussian noise to a data column

import logging
import subprocess
from losito.lib_operations import *
import casacore.tables as pt

logging.debug('Loading NOISE module.')


def _run_parser(obs, parser, step):
    return run(obs)


def run(obs):
    """
    Adds Gaussian noise to a data column.

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    """
    stddev=7500.

    myt=pt.table("/net/node100/data/users/lofareor/mevius/AARTFAAC/ACE_SB371_2min-3ch1s_LST23h30_08.MS",readonly=False)

    simul_data=myt.getcol("SIMULATED_DATA")
    myreal=np.random.normal(0,stddev,simul_data.shape)
    myimag=np.random.normal(0,stddev,simul_data.shape)
    noisedata=myreal+1.j*myimag
    desc=myt.getcoldesc("DATA")
    desc['name']="HALF_NOISE_DATA"
    myt.addcols(desc)
    desc['name']="SIMULATED_HALF_NOISE_DATA"
    myt.addcols(desc)

    myt.putcol("NOISE_DATA",noisedata)
    myt.putcol("SIMULATED_HALF_NOISE_DATA",simul_data+noisedata)
    myt.close()
