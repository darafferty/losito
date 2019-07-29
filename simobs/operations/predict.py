#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Predict operation for simobs: runs DPPP to predict a sky model with corruptions


import logging
import subprocess
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
    # Write DPPP parset with current parameters
    obs.write_parset()

    # Run DPPP
    result = _predict(obs.parset_filename)

    # Return result
    return result
