.. _clock:

CLOCK operation
---------------

The CLOCK operation produces time-dependent clock delays for the remote stations only.
The delays arising from the clock drift are modeled as sinusoidal oscillations with random
distributed parameters.

.. _clock_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    h5parmFilename
        This parameter is a string (no default) that sets the filename of input/output h5parm file.

    seed
        This parameter is an integer (default is ``0``) that sets the random seed. Use for reproducibility.

    clockAmp
        This parameter is a float (default is ``7e-9``) that sets the standard deviation for the clock drift
        amplitude in s.

    clockOffset
        This parameter is a float (default is ``2e-8``) that sets the standard deviation for the clock offset in s.

    clockOmega
        This parameter is a float (default is 1.) that controls the frequency of the clock drift oscillations.