.. _parset:

LoSiTo parset
-------------

The parset is a simple text file that defines the steps in a run. Below is an example parset:

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
applied sequentially, in the same order as written in the parset. See :ref:`examples` for an example parset.

