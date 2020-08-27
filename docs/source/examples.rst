.. _examples:

Example parset
--------------

The :ref:`parset` is a simple text file that defines the steps in a run.
Below is an example parset that can be used with the 5 minute measurement set in the losito/examples folder.
This parset will apply the first and second order ionospheric effect, station delay effects, the bandpass and the noise step to the simulated visibilities.

You can execute the example simulation via command-line: ``losito example.parset``.

::

#LoSiTo parset
##### global #######
msin = example_t201806301100_SBL250.MS
skymodel = example.sky

######## IONOSPHERE #######
[tec]
operation=TEC
method = turbulence

[faraday]
operation=FARADAY

####### CLOCK #######
[clock]
operation=CLOCK

[polmisalign]
operation=POLMISALIGN

# Add beam effects (array_factor+element)
[beam]
operation = BEAM
mode = default

# Do the predict
[predict]
operation = PREDICT
outputColumn = DATA
resetWeights = True
predictType = h5parmpredict

# Add noise to the predicted visibilities
[noise]
operation = NOISE
outputColumn = DATA

# Apply the bandpass
[bandpass]
operation = BANDPASS
method = ms
