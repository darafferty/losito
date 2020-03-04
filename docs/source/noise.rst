.. _noise:

NOISE operation
---------------

The NOISE operation adds noise to the model visibilities. The noise values are drawn for each baseline from a Gaussian distribution, the width of which is given by the appropriate source equivalent flux density (SEFD) in each frequency channel. The values for the SEFD were derived from van Haarlem et al. (2013) [#f1]_ by fitting a 5th degree polynomial to the datapoints.

.. note::

    If this operation is used in conjunction with the :ref:`predict`, then it should always be done after PREDICT so that the data to which noise are added are not overwritten.

.. _noise_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    outputColumn
        This parameter is a string (default is ``'DATA'``) that sets the column name to which noise is added

.. [#f1] van Haarlem M. P., et al. 2013, A\&A, 556, 2
