#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is an example operation for losito


import logging
from losito.lib_operations import *

logging.debug('Loading EXAMPLE module.')


# this funct is called to set parameters and call the real run()
def _run_parser(obs, parser, step):
    opt1 = parser.getfloat( step, 'opt1')  # no default
    opt2 = parser.getarrayfloat( step, 'opt3', [1., 2., 3.])
    opt3 = parser.getint( step, 'opt2', 0 )

    parser.checkSpelling( step, ['op1', 'opt2', 'opt3'])
    return run(obs, opt1, opt2, opt3)


# this function can be called by python directly
# parameters that are non optional require the default value equal to the one defined for the parset above
def run(obs, opt1, opt2=[1., 2., 3.], opt3=0):
    """
    Generic unspecified step for easy expansion.

    Parameters
    ----------
    opt1 : float
        Is a mandatory parameter.

    opt2 : list of float, optional
        Is optional, by default [1.,2.,3.]

    opt2 : int, optional
        Is optional, by default 0.
    """

    return 0  # if everything went fine, otherwise 1
