.. _scripts:

LoSiTo scripts
--------------

LoSiTo includes a number of convenience scripts to help with constructing simple sky models and FITS TEC screens. They are located in the ``bin/`` directory of the LoSiTo source tree.


.. _skymodel_script:

Sky model script
================

The sky model script, called ``skymodel``, can be used to generate a variety of simple sky models for use with LoSiTo.

::

    usage: skymodel [-h] [--output OUTPUT] [--kind KIND] [--radius RADIUS]
                    [--nptsrc NPTSRC] [--ngauss NGAUSS] [--minflux MINFLUX]
                    [--maxflux MAXFLUX] [--minmaj MINMAJ] [--maxmaj MAXMAJ]
                    [--maxell MAXELL] [--minspidx MINSPIDX] [--maxspidx MAXSPIDX]
                    [--logsi LOGSI]
                    msfile

    skymodel - generate simple sky models

    positional arguments:
      msfile               Input MS filename.

    optional arguments:
      -h, --help           show this help message and exit
      --output OUTPUT      Ouput sky model filename.
      --kind KIND          Kind of sky model: cross, spiral, tree, or random.
      --radius RADIUS      Radius in degrees within which sources are added.
      --nptsrc NPTSRC      Number of point sources to generate.
      --ngauss NGAUSS      Number of Gaussians to generate (kind=random only).
      --minflux MINFLUX    Minimum peak flux density in Jy (kind=random only).
      --maxflux MAXFLUX    Maximum peak flux density in Jy (kind=random only).
      --minmaj MINMAJ      Minimum major axis in arcsec of Gaussian sources.
      --maxmaj MAXMAJ      Maximum major axis in arcsec of Gaussian sources.
      --maxell MAXELL      Maximum ellipticity (1 - maj/min) of Gaussian sources.
      --minspidx MINSPIDX  Minimum spectral index of sources (kind=random only).
      --maxspidx MAXSPIDX  Maximum spectral index of sources (kind=random only).
      --logsi LOGSI        Value for LogarithmicSI: true or false (kind=random
                           only).



.. _synthms_script:

Synthms script
================

The ``synthms`` script can be used to create artificial LOFAR measurement sets from scratch.
Choose if you want to simulate an LBA or HBA observation.


::

    usage: synthms [-h] [--name NAME] [--start START] [--tobs TOBS]
                    [--ra RA] [--dec DEC] [--station STATION]
                    [--lofarversion LOFARVERSION] [--minsb MINSB] [--maxsb MAXSB]

    synthms - synthesize input ms files


    optional arguments:
      -h, --help           show this help message and exit
      --name NAME          MS file prefix
      --start START        Start of the obervation in MJD seconds.
      --tobs TOBS          Observation time in hours.
      --ra RA              Target right ascension in rad
      --dec DEC            Target declination in rad
      --station            >LBA<, >HBA< or >both<
      --lofarversion LOFARVERSION   >1< for the current instrument, >2< for LOFAR2.0
      --minsb MINSB        Specify the lowest sub band of the observation. The lowest possible subband is defined as SB150
      --maxsb MAXSB        Highest sub band




.. _tecscreen_script:

TEC screen script
=================

The TEC screen script, called ``tecscreen``, can be used to generate a TEC screen FITS cube for use with LoSiTo (and WSClean). The output FITS cube conforms to format accepted by WSClean (see https://sourceforge.net/p/wsclean/wiki/ImageDomainGridder/#tec-correction).

.. note::

   Other TEC screens can be generated directly (as h5parm tables instead of FITS cubes) in the :ref:`tec`.

::

    usage: tecscreen [-h] [--polygrade POLYGRADE] [--npixels NPIXELS]
                     [--size SIZE] [--seed SEED] [--maxdtec MAXDTEC] [--freq FREQ]
                     msfile fitsfile

    tecscreen - generate simple TEC screen FITS files

    positional arguments:
      msfile                Input MS filename
      fitsfile              Output FITS filename

    optional arguments:
      -h, --help            show this help message and exit
      --polygrade POLYGRADE
                            define grade of polynomial
      --npixels NPIXELS     number of screen pixels
      --size SIZE           width of screen in degrees
      --seed SEED           define random seed
      --maxdtec MAXDTEC     maximum dTEC value in screen
      --freq FREQ           factor controlling frequency
