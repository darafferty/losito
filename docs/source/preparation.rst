.. _data_preparation:

Preparing the input files
-------------------------

LoSiTo requires the following input files:

- One (or multiple) LOFAR **measurement sets**. This measurement set will be used as template for the simulation. The visibility data in this MS file will be overwritten, but the metadata (such as frequency-, station- and time-information) will be kept. The simulated visibilities will be written to a new or existing column in this measurement set. You may use any existing LOFAR MS. Alternatively, LoSiTo can be used to create measurement sets from scratch with the :ref:`synthms_script` script.

- A **sky model** in the makesourcedb format or as a FITS image. A makesourcedb file can be obtained in a number of ways: e.g., from an image using PyBDSF, generated directly by WSClean during imaging, from a survey catalog (e.g., the TGSS), or with the LoSiTo :ref:`skymodel_script`.

- A **parset** that defines the steps to be done. See :ref:`parset` for details.
