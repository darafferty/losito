.. _tec:

TEC operation
-------------

The TEC operation produces TEC corruptions that emulate the first-order phase delays due to time- and direction-dependent ionospheric effects. A number of methods for generating the corruptions are available:


.. _tec_methods:

Available methods
=================

.. glossary::

    Turbulence
        This method generates TEC values using a model of a turbulent ionosphere. The model adopts a Von Karman -
        spectrum for the turbulence and is based on the implementation of Buscher (2016) [#f1]_. The ionosphere is
        modeled as a single thin layer at a height given by :term:`hIon` using the frozen turbulence approximation: the
        screen structure itself is constant in time, but moves with a velocity given by :term:`vIono`.
        The maximum differential TEC for a single timestep can be specified with :term:`maxdtec` and the exponent of the power spectrum  can
        be set using :term:`alphaIon`.
        The homogeneous part of the ionosphere can be controlled setting :term:`maxvtec`. This constant contribution
        will also cause some dTEC due to airmass effects, furthermore it is important for realistic Faraday rotation
        simulations. The homogeneuos TEC follows a daily modulation, peaking at 3 p.m. and attaining its minimum of 10% at 3 a.m..

    FITS
        **Currently not maintained!** This method reads the TEC values from the FITS cube specified by :term:`fitsFilename`. The FITS cube must conform to the format accepted by WSClean (see https://sourceforge.net/p/wsclean/wiki/ImageDomainGridder/#tec-correction). The LoSiTo :ref:`tecscreen_script` can be used to generate such a FITS cube for a simple TEC screen.

    TID
        **Currently not maintained!** This method generates TEC values from a traveling ionospheric disturbance (TID) wave. The wave has an altitude of 200 km, a peak-to-peak length of 200 km and travels at a speed of 500 km/hr. The amplitude of the wave can be specified with :term:`maxdtec`, the maximum differential TEC parameter.



.. _tec_pars:

Parameters
==========

The following parameters are available for this operation:

.. glossary::

    method
        This parameter is a string (no default) that sets the method to use to generate the TEC corruptions (see :ref:`tec_methods` for details):

        * ``'turbulence'`` - generate TEC values from a turbulent ionosphere.

        * ``'fits'`` - read TEC values from the FITS cube specified by :term:`fitsFilename` .

        * ``'tid'`` - generate TEC values from a traveling ionospheric disturbance (TID) wave.



    h5parmFilename
        This parameter is a string (default is ``corruptions.h5``) that sets the filename of the input/output h5parm file.

    maxdtec
        This parameter is a float (default is ``0.5``) that controls the maximum dTEC in one TEC-screen (in TECU). (:term:`method` = ``'turbulence'`` or ``'tid'`` only).

    maxvtec:
        This parameter is a float (default is ``10``) that sets the highest absolute TEC value in the daily modulation in TECU (:term:`absoluteTEC` = ``True`` only).

    alphaIon:
        This parameter is a float (default is ``11/3``) that sets the ionosphere power spectrum exponent. A slightly greater value of ~3.89 was found in LOFAR observations [#f2]_ [#f3]_(:term:`method` = ``'turbulence'`` only).

    angRes
        This parameter is a float (default is ``60``) that sets the angular resolution of the screen in arcsec. (:term:`method` = ``'turbulence'`` only).

    hIon
        This parameter is a float (default is ``250``) that sets the height of thin layer ionoshpere in km (:term:`method` = ``'turbulence'`` only).

    vIono
        This parameter is a float (default is ``20``) that sets the velocity of the TEC screen in m/s (:term:`method` = ``'turbulence'`` only), which controls the TEC variation frequency.

    seed
        This parameter is an integer (default is ``0``) that sets the random screen seed. Use for reproducibility (:term:`method` = ``'turbulence'`` only).

    fitsFilename
        This parameter is a string (default is ``None``) that sets the filename of input FITS cube with dTEC solutions (:term:`method` = ``'fits'`` only).


.. [#f1] Buscher D. 2016, Optics Express, Vol. 24, Issue 20, pp. 23566
.. [#f2] de Gasperin F. et al., 2018, Astronomy & Astrophysics, arxiv: 1804.07947
.. [#f3] Mevius M. et al, 2016, Radio Science, Vol. 51, pp. 927

