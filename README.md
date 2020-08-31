# LoSiTo
## The LOFAR simulation tool


**LoSiTo** is a Python package that can be used to produce simulated LOFAR visibilities with a variety of corruptions and effects.

It includes:
* Time- and direction-dependent ionospheric effects (TEC and rotation measure)
* Beam effects
* Station-based delay effects (clock and polarization misalignment)
* Realistic noise

Furthermore, LoSiTo features the simulation of LOFAR2.0 simultaneous LBA-HBA observations.

The full documentation can be found at the [LoSiTo webpage](https://www.astron.nl/citt/losito) (not up to date).

### Software requirements:
* [casacore and python-casacore](https://casacore.github.io)
* [DPPP](https://github.com/lofar-astron/DP3)
* [LoSoTo](https://github.com/revoltek/losoto)
* [RMextract](https://github.com/maaijke/RMextract)
* [LSMTool](https://github.com/darafferty/LSMTool)
* Python (including scipy, numpy, and astropy)

### Installation
The recommended way to install LoSiTo is to download it from github and install with:

```
git clone https://github.com/darafferty/losito.git
cd losito
python setup.py install --prefix=~/mydir/
```

### Directory Structure
LoSiTo contains the following sub-directories:
* **bin** the ```losito``` main program and a number of scripts for your convenience
* **data** data files for the bandpass
* **examples** example parsets
* **losito** the losito Python files

LoSiTo was developed by:
* David Rafferty
* Henrik Edler
* Francesco de Gasperin

with contributed code from:
* Maaijke Mevius
* Peter Dorman
