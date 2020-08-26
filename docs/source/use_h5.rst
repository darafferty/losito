.. _use_h5:

USE_H5 operation
----------------

The USE_H5 operation allows the use of an h5parm from a previous LoSiTo run or an external source, for example the
calibration of a real measurement. When using an external source, the naming conventions in LoSiTo must be met. All
corruptions are store in a solution-set ``'sol000'``. The name of the solution-table depends on the type of corruption
that should be applied: ``'clock000'`` for clock delays, ``'clock001'`` for polarization misalignment, ``'tec000'``
for TEC and ``'rotationmeasure000'`` for ionospheric Faraday rotation. A direction axis containing all sources within
the input sky model must be present.


.. _use_h5_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    h5parmFilename
        This parameter is a string (no default) that sets the filename of input/output h5parm file.

    corruption
        This parameter is a string (no default) that sets the type of corruption to apply. Must be one of ``'clock'``, ``'tec'``, ``'polmisalign'``, ``bandpass` or ``'rm'``.

`