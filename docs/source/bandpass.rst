.. _bandpass:

BANDPASS operation
------------------

The BANDPASS operation adds a typical bandpass to the simulated visibilities. The bandpass tables used in this operation are located in the ``data/`` directory of the LoSiTo source tree.

.. _bandpass_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    method
        This parameter is a string (no default) that sets the method to use to apply the bandpass corruptions:

        * ``'h5parm'`` - store the corruptions in the h5parm given by :term:`h5parmFilename`.

        * ``'ms'`` - apply the corruptions directly to the MS file.

    h5parmFilename
        This parameter is a string (no default) that sets the filename of the input/output h5parm file.

    outputColumn
        This parameter is a string (default is ``'DATA'``) that sets the column name to which the bandpass is applied (:term:`method` = ``'ms'`` only).
