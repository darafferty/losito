.. _parset:

LoSiTo parset
-------------

The parset is a simple text file that defines the steps in a run. Below is an example parset:

::

    # LoSiTo parset
    # Define global parameters
    msin = example_t201806301100_SBL250.MS
    skymodel = example.sky

    # Add ionospheric dispersive delays
    [tec]
    operation = TEC
    method = turbulence

    # Add clock drifts
    [clock]
    operation = CLOCK

    # Do the prediction
    [predict]
    operation = PREDICT
    outputColumn = DATA
    resetWeights = True
    predictType = h5parmpredict

The parset file starts with a number of global parameters, most importantly the measurement set file name``msin``. All of the available global options are described below:


.. glossary::

    msin
        Input MS file name. Multiple MS files may be used if they have the same time-information. Glob-like expressions (``example_SB*.MS``) are supported.

    skymodel
        Filename of the sky model file. The sky model can be a text file in makesourcedb format or a FITS image. If it is a FITS image, a regions file must also be supplied.

    regions
        Filename of a ds9 region file that defines the directions (facets) used during prediction (optional). This file is used only when the input sky model is a FITS image and must follow the conventions described at https://wsclean.readthedocs.io/en/latest/ds9_facet_file.html.

    ncpu
        Integer, optional. How many cores to use. The default value of -1 will use all available cores.

    qsub
        Boolean, optional, default: False. If ``qsub=True``, LoSiTo will distribute jobs on multiple nodes when working on a SLURM-cluster.

    maxThreads
        Integer, optional. Maximum number of parallel jobs.

After the global parameters, a number of steps that define the simulation follow.
The first line of each step defines the step name in brackets. The lines following the step name define the operation performed by the step and its parameters. Steps are
applied sequentially, in the same order as written in the parset. See :ref:`examples` for an example parset.

