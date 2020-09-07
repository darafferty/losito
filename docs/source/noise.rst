.. _noise:

NOISE operation
---------------

The NOISE operation adds noise to the model visibilities. The noise values are drawn for each baseline from a Gaussian distribution, the width of which is given by the appropriate system equivalent flux density (SEFD) in each frequency channel. The values for the SEFD were derived from van Haarlem et al. (2013) [#f1]_. For the LOFAR2.0 LBA stations, the SEFD is estimated using 0.71 times the mean of the SEFD of the modes ``LBA_INNER`` and ``LBA_OUTER``.

.. note::

    If this operation is used in conjunction with the :ref:`predict`, then it should always be done after PREDICT so that the data to which noise are added are not overwritten.

.. note::

    For a realistic simulation, you should apply the bandpass (using the ``mode='ms'``) AFTER applying the noise.

.. _noise_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    outputColumn
        This parameter is a string (default is ``'DATA'``) that sets the column name to which noise is added
    factor
        This parameter is a scalar that can be used to tweak the noise scale. The default is 1.0.

.. [#f1] van Haarlem M. P., et al. 2013, A\&A, 556, 2
