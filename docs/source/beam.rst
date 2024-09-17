.. _beam:

BEAM operation
--------------

The BEAM operation uses the LOFAR beam model [#f1]_ to produce beam corruptions.


.. _beam_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    mode
        This parameter is a string (default is ``'default'``) that sets the beam mode to use:

        * ``'default'`` - use the full beam model (array factor + element).

        * ``'array_factor'`` - use only the array factor beam model (not supported when predictType = ``'idgpredict``').

        * ``'element'`` - use only the element beam model (not supported when predictType = ``'idgpredict``').

    usechannelfreq
        This parameter is a boolean (default is ``True``) that sets the way in which the beam is computed as a function of frequency. If ``True``, the beam is computed for each channel of the measurement set separately.

    onebeamperpatch
        This parameter is a boolean (default is ``False``) that determines whether the beam is computed just once per patch. If True, the beam is computed only for the center of each patch (not supported when predictType = ``'idgpredict``').

    predictType
        This parameter is a string (default is ``'h5parmpredict'``) that sets the type of DP3 predict to use. It must be one of ``'h5parmpredict``', ``'predict``', ``'idgpredict``', or ``'wgridderpredict``' (not yet supported). It should match the value given for the same parameter in the parset for the PREDICT operation.


.. [#f1] https://github.com/lofar-astron/LOFARBeam
