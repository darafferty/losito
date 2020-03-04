.. _polmisalign:

POLMISALIGN operation
---------------------

The POLMISALIGN operation produces constant, direction-independent delay offsets between the XX and YY polarizations. The delay offsets are drawn randomly for each station from a Gaussian distribution with a standard deviation of 1 ns.

.. note::

    If this operation is used in conjunction with other operations that produce corruptions, care should be taken to apply the corruptions in the correct order. Polarization misalignment corruptions should be applied after all other corruptions. The order in which the corruptions are applied is set by the order of the steps in the parset.


.. _polmisalign_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    h5parmFilename
        This parameter is a string (no default) that sets the filename of input/output h5parm file.

    seed
        This parameter is an integer (default is ``0``) that sets the random seed. Use for reproducibility.
