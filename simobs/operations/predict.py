#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Predict operation for simobs: runs DPPP to predict a sky model with corruptions


import logging
from simobs.lib_operations import *

logging.debug('Loading PREDICT module.')


def _run_parser(obs, parser, step):
    return run(obs)


def _predict(parset):
    """
    Runs DPPP to preform predict.

    Parameters
    ----------
    parset : str
        Filename of DPPP parset.
    """
    cmd = ['DPPP', parset]
    result = subprocess.call(cmd)
    return result


def run( obs ):
    """
    Runs DPPP to predict a sky model with corruptions.

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    """
    # Run DPPP
    mpm = multiprocManager(ncpu, _predict)
    mpm.put([obs.parset_filename])
    mpm.wait()

    # Return result
    for result in mpm.get():
        return result
