.. _examples:

Example parset
--------------

The :ref:`parset` is a simple text file that defines the steps in a run.
Below is an example parset that can be used with the 5 minute measurement set in the losito/examples folder.
This parset will apply the first and second order ionospheric effect, station delay effects, the bandpass and the noise step to the simulated visibilities.

You can execute the example simulation via command-line: ``losito example.parset``.

::

    # LoSiTo parset
    # Define global parameters
    msin = example_t201806301100_SBL250.MS
    skymodel = example.sky

    # Add ionospheric effects
    [tec]
    operation = TEC
    method = turbulence

    # Add Faraday rotation effects (using TEC values from the [tec] step)
    [faraday]
    operation = FARADAY

    # Add clock delays between stations
    [clock]
    operation = CLOCK

    # Add delays between polarizations
    [polmisalign]
    operation = POLMISALIGN

    # Add beam effects (array_factor+element)
    [beam]
    operation = BEAM
    mode = default

    # Do the prediction
    [predict]
    operation = PREDICT
    outputColumn = DATA
    resetWeights = True
    predictType = h5parmpredict

    # Add noise to the predicted visibilities
    [noise]
    operation = NOISE
    outputColumn = DATA

    # Add bandpass effects
    [bandpass]
    operation = BANDPASS
    method = ms
