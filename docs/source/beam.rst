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

        * ``'array_factor'`` - use only the array factor beam model.

        * ``'element'`` - use only the element beam model.

    usechannelfreq
        This parameter is a boolean (default is ``True``) that sets the way in which the beam is computed as a function of frequency. If ``True``, the beam is computed for each channel of the measurement set separately.

    onebeamperpatch
        This parameter is a boolean (default is ``False``) that determines whether the beam is computed just once per patch. If True, the beam is computed only for the center of each patch.


.. [#f1] https://github.com/lofar-astron/LOFARBeam
