.. _parset:

LoSiTo parset
-------------

The parset is a simple text file that defines the steps in a run. Below is an example parset:

::

#LoSiTo parset
##### global #######
msin = example_t201806301100_SBL250.MS
skymodel = example.sky

[tec] # add ionospheric dispersive delay
operation=TEC
method = turbulence

[clock] # clock drift
operation=CLOCK

# Do the predict
[predict]
operation = PREDICT
outputColumn = DATA
resetWeights = True
predictType = h5parmpredict

The parset file starts with a number of global parameters, most importantly the measurement set file name``msin``

.. glossary::

    msin
        Input MS file name. Multiple MS files may be used if they have the same time-information. Glob-like expressions (``example_SB*.MS``) are supported.

    skymodel
        Name of the sky model file.

    ncpu
        Integer, optional. How many cores to use. The default value of -1 will use all available cores.

    qsub
        Boolean, optional, default: False. If ``qsub=True``, LoSiTo will distribute jobs on multiple nodes when working on a SLURM-cluster.

    maxThreads
        Integer, optional. Maximum number of parallel jobs.

After the global parameters, a number of steps that define the simulation follow.
The first line of each step defines the step name in brackets. The lines following the step name define the operation performed by the step and its parameters. Steps are
applied sequentially, in the same order as written in the parset. See :ref:`examples` for an example parset.

