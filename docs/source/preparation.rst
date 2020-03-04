.. _data_preparation:

Preparing the input files
-------------------------

LoSiTo requires the following input files:

- A LOFAR measurement set. The simulated visibilities will be written to a new or existing column in this measurement set. Currently, LoSiTo does not have the ability to create measurement sets from scratch.

- A sky model in the makesourcedb format. This file can be obtained in a number of ways: e.g., from an image using PyBDSF, generated directly by WSClean during imaging, from a survey catalog (e.g., the TGSS), or with the LoSiTo :ref:`skymodel_script`.

- A parset that defines the steps to be done. See :ref:`parset` for details.
