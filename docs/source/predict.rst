.. _predict:

PREDICT operation
-----------------

The PREDICT operation runs DPPP to preform the prediction of the visibility data.

.. note::

    The PREDICT step should be done after all corruption operations but before a :ref:`noise`. PREDICT will overwrite any existing data in the output column.


.. _predict_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    outputColumn
        This parameter is a string (default is ``'DATA'``) that sets the column name to which the predicted visibilities are written.

    predictType
        This parameter is a string (default is ``'h5parmpredict'``) that sets the type of prediction done. Use ``'h5parmpredict'`` for normal prediction and ``'predict'`` to predict without direction-dependent corruptions.

    resetWeights
        This parameter is a boolean (default is ``True``) that sets whether to reset the entries in the WEIGHT_SPECTRUM column.
