.. _use_h5:

USE_H5 operation
----------------

The USE_H5 operation allows the use of an externally derived h5parm.


.. _use_h5_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    h5parmFilename
        This parameter is a string (no default) that sets the filename of input/output h5parm file.

    corruption
        This parameter is a string (no default) that sets the type of corruption to apply. Must be one of ``'clock'``, ``'tec'``, ``'polmisalign'``, or ``'rm'``.

