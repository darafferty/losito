.. _bandpass:

BANDPASS operation
------------------

The BANDPASS operation adds a typical bandpass to the simulated visibilities. The bandpass tables used are taken from
*van Haarlem et al. (2013)* [#f1]_ and located in the ``data/`` directory of the LoSiTo source
tree. There are two methods to apply the bandpass: the bandpass amplitudes can either be stored to a *h5parm* - file
or be applied directly to a data column within a measurement set.

.. note::

    Depending on which method is used to add the bandpass to the simulation, the position of this step in the parset
    differs. For the ``'h5parm'`` - method, this step must be before the PREDICT step. For the ``'ms'`` - method, the
    bandpass operation must be placed after the PREDICT - step, otherwise it will be overwritten.


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


.. [#f1] van Haarlem M. P., et al. 2013, A\&A, 556, 2
