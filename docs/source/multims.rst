.. _multims:

Multi-MS simulations
--------------------
Simulations that include many frequency sub-bands can become very memory heavy when a single concatenated measurement
set is used as input. This makes it appealing to run the simulation on multiple smaller measurement sets, containing
only a single (or a few) sub-bands.

Of course, it has to be taken care that the appropriate systematics are applied for each frequency channel. This can be
achieved by using the fact that most of the corrupting effects in LoSiTo are are stored in a *h5parm* - file
without a frequency axis. So it is possible to create one *h5parm* - file that includes all these effects (currently
all steps but the :ref:`BEAM`, :ref:`BANDPASS` and :ref:`NOISE`) for one of the measurement sets. Then, for each of the
input measurement sets, the corruptions in this *h5parm* - file are added to the simulation with the :ref:`USE_H5`
step, and subsequently, a :ref:`PREDICT` step is carried out. In this LoSiTo - run, also the :ref:`BEAM`,
:ref:`BANDPASS` and :ref:`NOISE` may be included.


For example, suppose that you want to simulate a LOFAR observation consisting of 244 sub-bands, each stored in a
single measurement set. The input measurement sets may be called *sim_SB150.MS* up to *sim_SB393.MS*.
The following :ref:`parset` generates the one *h5parm* - file containing the corruptions which can be stored in a
frequency - independent way. It is sufficient to run LoSiTo on only one of the input measurement sets, e.g.:
``losito  multims_run1.parset``


::

    #LoSiTo parset multims_run1.parset
    msin = sim_SB150.MS
    skymodel = example.sky
    ############## CREATE H5PARM FILE ####################
    # Add TEC values from von Karman tecscreen
    [tec]
    operation = TEC
    method = turbulence
    h5parmFilename = corruptions.h5

    # Compute faraday rotation
    [rm]
    operation = FARADAY
    h5parmFilename = corruptions.h5

    # Clock delay
    [clock]
    operation = CLOCK
    h5parmFilename = corruptions.h5

    # Polarization misalignment
    [polmisalign]
    operation = POLMISALIGN
    h5parmFilename = corruptions.h5



Subsequently, LoSiTo can be run on every single input measurement set, including the effects stored in
``corruptions.h5`` to the simulation using the :ref:`parset` below. Glob-style expressions are supported for the input ms
name.


::

    #LoSiTo parset multims_run2.parset
    msin = sim_SB*.MS
    skymodel = example.sky
    ############ APPLY CORRUPTIONS ########################
    # Add the corruptions stored in the h5parm file:
    [tec]
    operation = USE_H5
    corruption = tec
    h5parmFilename = corruptions.h5

    [rotationmeasure]
    operation = USE_H5
    corruption = rm
    h5parmFilename = corruptions.h5

    [polmisalign]
    operation = USE_H5
    corruption = polmisalign
    h5parmFilename = corruptions.h5

    [clock]
    operation = USE_H5
    corruption = clock
    h5parmFilename = corruptions.h5

    # Add the Beam
    [beam]
    operation = beam
    mode = default

    # Do the predict
    [predict]
    operation = PREDICT
    outputColumn = DATA
    predictType = h5parmpredict

    # Add bandpass to predicted visibilities
    [bandpass]
    operation = BANDPASS
    outputColumn = DATA
    method = ms

    # Add noise to the predicted visibilities
    [noise]
    operation = NOISE
    outputColumn = DATA