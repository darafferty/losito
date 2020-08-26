.. _running:

Starting a run
--------------

LoSiTo is run with the ``losito`` script as follows:

::

    usage: losito [-h] [--version] [--quiet] [--verbose]  parset

    losito - The LOFAR Simulation Tool

    positional arguments:
      parset             LoSiTo parset.

    optional arguments:
      -h, --help         show this help message and exit
      --version          show program's version number and exit
      --quiet, -q        Quiet
      --verbose, -V, -v  Verbose


The inputs are:

- ``parset`` - the :ref:`parset` file that specifies the skymodel and measurement set file to be use as well as the operations to perform and their parameters. The default is ``'losito.parset'``.
