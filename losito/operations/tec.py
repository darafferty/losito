#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TEC operation for losito: generates TEC corruptions
"""
import multiprocessing as mp
import warnings

import RMextract.PosTools as post
import astropy.coordinates as coord
import numpy as np
from astropy import units as u
from astropy import wcs
from astropy.coordinates import EarthLocation, AltAz
from astropy.io import fits as pyfits
from astropy.time import Time
from astropy.utils.exceptions import AstropyWarning

from losoto.h5parm import h5parm
from ..lib_io import logger
from ..lib_tecscreen import comoving_tecscreen, daytime_tec_modulation

logger.debug('Loading TEC module.')
# Mute AP warnings for now...
warnings.simplefilter('ignore', category=AstropyWarning)


def _run_parser(obs, parser, step):
    method = parser.getstr(step, 'method', default='turbulence')
    h5parmFilename = parser.getstr(step, 'h5parmFilename', 'corruptions.h5')
    r0 = parser.getfloat(step, 'r0', default=10)
    maxdtec = parser.getfloat(step, 'maxdtec', default=0.5)
    maxvtec = parser.getfloat(step, 'maxvtec', default=10.)
    alphaIon = parser.getfloat(step, 'alphaIon', default=11/3)
    hIon = parser.getfloat(step, 'hIon', default=250e3)
    vIon = parser.getfloat(step, 'vIon', default=20)
    seed = parser.getint(step, 'seed', default=0)
    fitsFilename = parser.getstr(step, 'fitsFilename', default='')
    angRes = parser.getfloat(step, 'angRes', default=60.)
    expfolder = parser.getstr(step, 'expfolder', default='')
    ncpu = parser.getint('_global', 'ncpu', 0)

    parser.checkSpelling(step, ['method', 'h5parmFilename', 'r0', 'maxdtec',
                                'maxvtec', 'alphaIon', 'hIon', 'vIon', 'seed',
                                'fitsFilename', 'angRes',
                                'expfolder', 'ncpu'])
    return run(obs, method, h5parmFilename, r0, maxdtec, maxvtec, alphaIon, hIon, vIon, seed,
               fitsFilename, step, angRes, expfolder, ncpu)


def _getaltaz(radec):
    ra = radec[0]
    dec = radec[1]
    aa = radec[2]
    mycoord = coord.SkyCoord(ra, dec, frame=coord.FK5, unit=(u.hourangle, u.deg))
    mycoord_aa = mycoord.transform_to(aa)
    return mycoord_aa


def _gettec(altaz_args):
    alltec = []
    altaz, stationpositions, A12, times, tidAmp, tidLen, tidVel = altaz_args
    direction = altaz.geocentrictrueecliptic.cartesian.xyz.value
    for ant in stationpositions:
        pp, am = post.getPPsimple([200.e3] * direction[0].shape[0], ant, direction)
        ppa = EarthLocation.from_geocentric(pp[:, 0], pp[:, 1], pp[:, 2], unit=u.m)
        ppaproj = EarthLocation.from_geodetic(-ppa.lon.deg + A12.lon.deg, -ppa.lat.deg + A12.lat.deg, ppa.height)
        x = ppaproj.z.value
        y = ppaproj.y.value
        tec = _tid(x, times, tidAmp, tidLen, tidVel)
        alltec.append([tec, x, y, altaz.secz])
    return alltec


def _tid(x, t, amp=0.2, wavelength=200e3, omega=500.e3 / 3600.):
    return amp * np.sin((x + omega * t) * 2 * np.pi / wavelength)


def run(obs, method, h5parmFilename, r0=10, maxdtec=0.5, maxvtec=50, alphaIon = 11/3, hIon=250e3,
        vIon=20, seed=0, fitsFilename=None, stepname='tec',
        angRes=60, expfolder='', ncpu=0):
    """
    Simulate TEC values and store them to a h5parm.

    Parameters
    ----------
    method : str
        Method to use:
        "turbulence": sample tec values from a turbulent TEC-screen.
        "fits": read TEC values from the FITS cube specified by fitsFilename
        "tid": generate a traveling ionospheric disturbance (TID) wave
    h5parmFilename : str
        Filename of output h5parm file.
    r0 : float, optional. Default = 10km, .
        Diffractive scale / Fried parameter ath 150MHz in km. This controls the amplitude of the dTEC.
        (only for method='turbulence')
    maxdtec: float, optional. Default = 50 .
        Maximum dTEC in TECU (only for method='tid').
    maxvtec: float, optional. Default = 50.
        Highest vTEC in daily modulation in TECU.
    alphaIon: float, optional. Default = 11/3.
        Ionosphere power spectrum exponent (only for method='turbulence'). Is 11/3 for Kolmogorov,
        F. de Gasperin and M. Mevius found ~3.89 for LOFAR.
    hIon : float, optional. Default = 250 km
        Height of thin layer ionoshpere.
    vIono : float, optional. Default = 20 m/s
        Velocity of tecscreen. This controls the tec variation frequency (only for method='turbulence').
    seed: int, optional.
        Random screen seed. Use for reproducibility.
    fitsFilename : str, optional
        Filename of input FITS cube with dTEC solutions (only method='fits').
    stepname _ str, optional
        Name of step to use in DP3 parset
    angRes : float, optional. Default = 60.
        Angular resolution of the screen [arcsec] (Only for turbulent model).
    expfolder : str, optional. Default = None
        Export the tecscreen data to this folder for plotting. Depending on
        system memory, this will not work for very large/highres screens.
        Only for 'turbulence' method.
    ncpu : int, optional
        Number of cores to use, by default all available.
    """
    # TODO : Test TID and polynomial method for multi-ms usage

    method = method.lower()
    if ncpu == 0:
        ncpu = mp.cpu_count()
    # Get sky model properties
    ras, decs = obs.get_patch_coords()
    source_names = obs.get_patch_names()
    ants = obs.stations
    sp = obs.stationpositions
    times = obs.get_times()

    tecvals = np.zeros((len(times), len(ants), len(ras)))
    weights = np.ones_like(tecvals)

    if method == 'turbulence':
        # Handle default arguments:
        directions = np.array([ras, decs]).T
        tecvals = comoving_tecscreen(sp, directions, times, alpha=alphaIon, angRes=angRes,
                                     hIon=hIon, vIon=vIon, maxvtec=maxvtec,
                                     r0=r0, ncpu=ncpu,
                                     expfolder=expfolder, seed=seed)
    elif method == 'fits':
    # Load solutions from FITS cube
        hdu = pyfits.open(fitsFilename, memmap=False)
        data = hdu[0].data
        header = hdu[0].header
        w = wcs.WCS(header)
        ntimes, _, nstations, ny, nx = data.shape

        # Check that number of stations in input FITS cube matches MS
        if nstations != len(ants):
            logger.error('Number of stations in input FITS cube does not '
                         'match that in the input MS')
            return 1

        # Get solutions at the source coords
        for d, (ra_deg, dec_deg) in enumerate(zip(ras, decs)):
            ra_dec = np.array([[ra_deg, dec_deg, 0, 0, 0]])
            x = int(w.wcs_world2pix(ra_dec, 0)[0][0])
            y = int(w.wcs_world2pix(ra_dec, 0)[0][1])
            if x < 0 or x > nx or y < 0 or y > ny:
                tecvals[:, :, d, :] = 0.0
                weights[:, :, d, :] = 0.0
                continue
            for t in range(ntimes):
                for s in range(nstations):
                    tecvals[t, s, d] = data[t, 0, s, y, x]
        tecvals = daytime_tec_modulation(times)[:, np.newaxis, np.newaxis] * (
                    tecvals + maxvtec)

    elif method == 'tid':
        # Properties of TID wave
        tidLen = 200e3
        tidVel = 500e3 / 3600,
        tid_prop = [maxdtec, tidLen, tidVel]
        # Generate solutions for TID wave
        A12 = EarthLocation(lat=52.91 * u.deg, lon=6.87 * u.deg, height=1 * u.m)
        mjd = Time(times / (3600.0 * 24.0), format="mjd")

        aa = AltAz(location=A12, obstime=mjd)
        altazcoord = []
        pool = mp.Pool(processes=ncpu)
        radec = [(r, d, aa) for r, d in zip(ras, decs)]
        altazcoord = pool.map(_getaltaz, radec)
        gettec_args = [(a, sp, A12, times, *tid_prop) for a in altazcoord]
        alltec = pool.map(_gettec, gettec_args)
        pool.close()
        pool.join()
        alltec = np.array(alltec)
        # Fill the axis arrays
        tecvals = alltec[:, :, 0, :].transpose([2, 1, 0])  # [:,:,:,0]
        # convert to vTEC
        tecvals = daytime_tec_modulation(times)[:, np.newaxis, np.newaxis] * (
                tecvals + maxvtec)

    else:
        logger.error('method "{}" not understood'.format(method))
        return 1

    # Write tec values to h5parm file as DP3 input
    ho = h5parm(h5parmFilename, readonly=False)

    if 'sol000' in ho.getSolsetNames():
        solset = ho.getSolset('sol000')
    else:
        solset = ho.makeSolset(solsetName='sol000')

    if 'tec000' in solset.getSoltabNames():
        logger.info('''Solution-table tec000 is already present in
                 {}. It will be overwritten.'''.format(h5parmFilename + '/sol000'))
        solset.getSoltab('tec000').delete()

    st = solset.makeSoltab('tec', 'tec000', axesNames=['time', 'ant', 'dir'],
                           axesVals=[times, ants, source_names], vals=tecvals,
                           weights=weights)
    antennaTable = solset.obj._f_get_child('antenna')
    antennaTable.append(list(zip(*(ants, sp))))
    sourceTable = solset.obj._f_get_child('source')
    vals = [[np.deg2rad(ra), np.deg2rad(dec)] for ra, dec in zip(ras, decs)]
    sourceTable.append(list(zip(*(source_names, vals))))

    # Add CREATE entry to history
    soltabs = solset.getSoltabs()
    for st in soltabs:
        st.addHistory('CREATE (by TEC operation of LoSiTo from obs {0} '
                      'and method="{1}")'.format(h5parmFilename, method))
    ho.close()

    # Update predict parset parameters for the obs
    is_dde = True if len(source_names) > 1 else False
    obs.add_to_parset(stepname, 'tec000', h5parmFilename, DDE=is_dde)

    return 0
