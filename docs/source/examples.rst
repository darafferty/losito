.. _examples:

Example parset
--------------

The :ref:`parset` is a simple text file that defines the steps in a run.
Below is an example parset that predicts data with TEC and beam corruptions and then adds noise:

::

    # Example parset
    ncpu = 0

    # Add beam effects (array_factor+element)
    [beam]
    operation = BEAM
    mode = default

    # Add TEC values from FITS images
    [tec1]
    operation = TEC
    method = fits
    fitsFilename = example.fits
    h5parmFilename = tec1.h5

    # Add TEC values from TID wave
    [tec2]
    operation = TEC
    method = tid
    tidAmp = 0.3
    h5parmFilename = tec2.h5

    # Do the predict
    [predict]
    operation = PREDICT
    outputColumn = CORRECTED_DATA

    # Add noise to the predicted visibilities
    [noise]
    operation = NOISE
    column = CORRECTED_DATA


