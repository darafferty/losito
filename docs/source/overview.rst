LoSiTo: the LOFAR Simulation Tool
=================================

LoSiTo is a Python package to produce simulated LOFAR visibilities with a variety
of corruptions, including:

- realistic time- and direction-dependent ionospheric effects (TEC, rotation measure)
- LOFAR beam effects
- station-based delay effects
- realistic noise


Installing LoSiTo
-----------------


Usage
-----

LoSiTo can be run as follows:

::

    Usage: losito <msfile> <skymodel> <parset>
    Options:
      --version   show program's version number and exit
      -h, --help  show this help message and exit
      -q          Quiet
      -v          Verbose

The parset specifies the operations to perform and their parameters.
These are described in detail below.


The parset
----------

The parset is a simple text file that defines the steps in a run.
Below is an example parset:

::

    [tec]
    operation = TEC
    method = tid
    h5parmFilename = tec_tid.h5

    [beam]
    operation = BEAM
    mode = array_factor

    [predict]
    operation = PREDICT
    outputColumn = DATA

    [noise]
    operation = NOISE
    outputColumn = DATA

The first line of each step defines the step name in brackets. The lines
following the step name define the operation performed by the step and its parameters. Steps are
applied sequentially, in the same order as written in the parset. A
list of step-specific parameters is given below.


Operations
----------

These are the operations that LoSiTo can perform:

TEC
    : Corrupt with time- and direction-dependent TEC values

BEAM
    : Corrupt with the LOFAR beam model

PREDICT
    : Predict model data with above corruptions

NOISE
    : Add realistic noise

Example parset
--------------

