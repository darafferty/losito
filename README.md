# LoSiTo
## The LOFAR simulation tool


**LoSiTo** is a Python package that can be used to produce simulated LOFAR visibilities with a variety of corruptions and effects.

It includes:
* Time- and direction-dependent ionospheric effects (TEC and rotation measure)
* Beam effects
* Station-based delay effects (clock and polarization misalignment)
* Realistic noise

Furthermore, LoSiTo features the simulation of LOFAR2.0 simultaneous LBA-HBA observations.

The full documentation can be found at the [LoSiTo webpage](https://losito.readthedocs.io/en/latest/).

### Software requirements:
* [casacore and python-casacore](https://casacore.github.io)
* [DP3](https://github.com/lofar-astron/DP3)
* [LoSoTo](https://github.com/revoltek/losoto)
* [RMextract](https://github.com/maaijke/RMextract)
* [LSMTool](https://github.com/darafferty/LSMTool)
* Python 3.7+ (including scipy, numpy, and astropy)

### Installation
The recommended way to install LoSiTo is to download it from github and install with:

```
git clone https://github.com/darafferty/losito.git
cd losito
pip install .
```

### Directory Structure
LoSiTo contains the following sub-directories:
* **bin** the ```losito``` main program and a number of scripts for your convenience
* **examples** example parsets
* **losito** the losito Python files, operations and data.

LoSiTo was developed by:
* David Rafferty
* Henrik Edler
* Francesco de Gasperin

with contributed code from:
* Maaijke Mevius
* Peter Dorman
