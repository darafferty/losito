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
        This parameter is an integer (default is ``0``) that sets the seed for random number generation. Use for
        reproducibility. The default value of ``seed = 0`` means that a random seed is used.

    mode
        Should the clock error be simulated for LOFAR1 or LOFAR2.0? for ``mode='lofar1'``, the CS will have a shared clock.
        For ``mode='lofar2'``, each station will have an independent but much smaller clock offset. This selection also changes the default values.
        The default is ``mode='lofar1'``.

    clockAmp
        This parameter is a float (default is ``7e-10`` (lofar1) respectively ``8.25e-11`` (lofar2)) that sets the standard deviation for the clock drift
        amplitude in s.

    clockOffset
        This parameter is a float (default is ``2e-8`` respectively ``1.17e-10``) that sets the standard deviation for the clock offset in s.

    clockOmega
        This parameter is a float (default is 1.) that controls the frequency of the clock drift oscillations.
