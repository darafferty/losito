.. _running:

Starting a run
--------------

LoSiTo is run with the ``losito`` script as follows:

::

    usage: losito [-h] [--version] [--quiet] [--verbose] msfile skymodel [parset]

    losito - The LOFAR Simulation Tool

    positional arguments:
      msfile             Input MS filename.
      skymodel           Input sky model filename.
      parset             LoSiTo parset.

    optional arguments:
      -h, --help         show this help message and exit
      --version          show program's version number and exit
      --quiet, -q        Quiet
      --verbose, -V, -v  Verbose


The inputs are:

- ``msfile`` - the MS file into which the simulated data are written.
- ``skymodel`` - the sky model that defines the sources to be simulated
- ``parset`` - the :ref:`parset` file that specifies the operations to perform and their parameters. The default is ``'losito.parset'``.
