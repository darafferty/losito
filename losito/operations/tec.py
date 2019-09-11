#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TEC operation for losito: applies TEC values
import logging
from losito.lib_operations import *
from astropy.io import fits as pyfits
from astropy import wcs
from losoto.h5parm import h5parm
import numpy as np
from astropy import units as u
import astropy.coordinates as coord
from astropy.time import Time
from astropy.coordinates import EarthLocation
from astropy.coordinates import AltAz
from multiprocessing import Pool
import RMextract.PosTools as post
import os

logging.debug('Loading TEC module.')


def _run_parser(obs, parser, step):
    method = parser.getstr( step, 'method')
    h5parmFilename = parser.getstr( step, 'h5parmFilename')
    fitsFilename = parser.getstr( step, 'fitsFilename', '')

    parser.checkSpelling( step, ['method', 'fitsFilename', 'h5parmFilename'])
    return run(obs, method, h5parmFilename, fitsFilename, step)


def _getaltaz(radec):
    ra = radec[0]
    dec = radec[1]
    aa = radec[2]
    mycoord = coord.SkyCoord(ra, dec, frame=coord.FK5, unit=(u.hourangle, u.deg))
    mycoord_aa = mycoord.transform_to(aa)
    return mycoord_aa


def _gettec(altaz_args):
    alltec = []
    altaz, stationpositions, A12, times = altaz_args
    direction = altaz.geocentrictrueecliptic.cartesian.xyz.value
    for ant in stationpositions:
        pp, am = post.getPPsimple([200.e3]*direction[0].shape[0], ant, direction)
        ppa = EarthLocation.from_geocentric(pp[:, 0], pp[:, 1], pp[:, 2], unit=u.m)
        ppaproj = EarthLocation.from_geodetic(-ppa.lon.deg+A12.lon.deg, -ppa.lat.deg+A12.lat.deg, ppa.height)
        x = ppaproj.z.value
        y = ppaproj.y.value
        tec = tid(x, times*3600.*24)
        alltec.append([tec, x, y, altaz.secz])
    return alltec


def tid(x, t, omega=500.e3/3600., amp=1., wavelength=200e3):
    return amp*np.sin((x+omega*t)*2*np.pi/wavelength)


def run(obs, method, h5parmFilename, fitsFilename=None, stepname=None):
    """
    Creates h5parm with TEC values from TEC FITS cube.

    Parameters
    ----------
    method : str
        Method to use:
        "fits": read TEC values from the FITS cube specified by fitsFilename
        "tid": generate a traveling ionospheric disturbance (TID) wave
    h5parmFilename : str
        Filename of output h5parm file.
    fitsFilename : str, optional
        Filename of input FITS cube with dTEC solutions.
    """
    # Get sky model properties
    ras, decs = obs.get_patch_coords()
    source_names = obs.get_patch_names()
    ndirs = len(source_names)

    if method == 'fits':
        # Load solutions from FITS cube
        hdu = pyfits.open(fitsFilename, memmap=False)
        data = hdu[0].data
        header = hdu[0].header
        w = wcs.WCS(header)
        ntimes, nfreqs, nstations, ny, nx = data.shape

        # Check that number of stations in input FITS cube matches MS
        if nstations != len(obs.stations):
            logging.error('Number of stations in input FITS cube does not match that in the input MS')
            return 1

        # Get solutions at the source coords
        vals = np.zeros((ntimes, nstations, ndirs, nfreqs))
        weights = np.ones(vals.shape)
        for d, (ra_deg, dec_deg) in enumerate(zip(ras, decs)):
            ra_dec = np.array([[ra_deg, dec_deg, 0, 0, 0]])
            x = int(w.wcs_world2pix(ra_dec, 0)[0][0])
            y = int(w.wcs_world2pix(ra_dec, 0)[0][1])
            if x < 0 or x > nx or y < 0 or y > ny:
                vals[:, :, d, :] = 1.0
                weights[:, :, d, :] = 0.0
                continue
            for t in range(ntimes):
                for f in range(nfreqs):
                    for s in range(nstations):
                        vals[t, s, d, f] = data[t, f, s, y, x]

        # Fill the axis arrays
        t_ref = header['CRVAL4']
        t_del = header['CDELT4']
        times = [t_ref+(t_del*i) for i in range(ntimes)]
        f_ref = header['CRVAL3']
        f_del = header['CDELT3']
        freqs = [f_ref+(f_del*i) for i in range(nfreqs)]
        ants = obs.stations

        # Make h5parm with solutions and write to disk
        if os.path.exists(h5parmFilename):
            os.remove(h5parmFilename)
        ho = h5parm(h5parmFilename, readonly=False)
        solset = ho.makeSolset(solsetName='sol000')
        st = solset.makeSoltab('tec', 'tec000', axesNames=['time', 'ant', 'dir', 'freq'],
                               axesVals=[times, ants, source_names, freqs], vals=vals,
                               weights=weights)
        antennaTable = solset.obj._f_get_child('antenna')
        antennaTable.append(list(zip(*(obs.stations, obs.stationpositions))))
        sourceTable = solset.obj._f_get_child('source')
        vals = [[ra, dec] for ra, dec in zip(ras, decs)]
        sourceTable.append(list(zip(*(source_names, vals))))

        # Add CREATE entry to history
        soltabs = solset.getSoltabs()
        for st in soltabs:
            st.addHistory('CREATE (by TEC operation of LoSiTo from '
                          'obs {0} and FITS cube {1})'.format(h5parmFilename, fitsFilename))
        ho.close()

    elif method == 'tid':
        # Generate solutions for TID wave
        times = np.array([obs.starttime+i*obs.timepersample for i in range(obs.numsamples)])
        times /= 3600.0 * 24.0

        A12 = EarthLocation(lat=52.91*u.deg, lon=6.87*u.deg, height=1*u.m)
        time = Time(times, format="mjd")

        aa = AltAz(location=A12, obstime=time)
        altazcoord = []
        p = Pool(processes=16)
        radec = [(r, d, aa) for r, d in zip(ras, decs)]
        altazcoord = p.map(_getaltaz, radec)

        p = Pool(processes=16)
        gettec_args = [(a, obs.stationpositions, A12, times) for a in altazcoord]
        alltec = p.map(_gettec, gettec_args)
        alltec = np.array(alltec)

        # Fill the axis arrays
        times *= 3600.0 * 24.0
        freqs = [obs.referencefreq]
        ants = obs.stations
        vals = np.zeros((len(times), len(ants), len(source_names), 1))
        weights = np.ones(vals.shape)
        vals[:, :, :, 0] = alltec[:, :, 0, :].transpose([2, 1, 0])

        # Make h5parm with solutions and write to disk
        if os.path.exists(h5parmFilename):
            os.remove(h5parmFilename)
        ho = h5parm(h5parmFilename, readonly=False)
        solset = ho.makeSolset(solsetName='sol000')
        st = solset.makeSoltab('tec', 'tec000', axesNames=['time', 'ant', 'dir', 'freq'],
                               axesVals=[times, ants, source_names, freqs], vals=vals,
                               weights=weights)
        antennaTable = solset.obj._f_get_child('antenna')
        antennaTable.append(list(zip(*(obs.stations, obs.stationpositions))))
        sourceTable = solset.obj._f_get_child('source')
        vals = [[ra, dec] for ra, dec in zip(ras, decs)]
        sourceTable.append(list(zip(*(source_names, vals))))

        # Add CREATE entry to history
        soltabs = solset.getSoltabs()
        for st in soltabs:
            st.addHistory('CREATE (by TEC operation of LoSiTo from '
                          'obs {0} and method="wave")'.format(h5parmFilename))
        ho.close()
    else:
        logging.error('method "{}" not understood'.format(method))
        return 1

    # Update predict parset parameters for the obs
    obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
    if 'predict.applycal.steps' in obs.parset_parameters:
        obs.parset_parameters['predict.applycal.steps'].append('tec')
    else:
        obs.parset_parameters['predict.applycal.steps'] = [stepname]
    obs.parset_parameters['predict.applycal.correction'] = 'tec000'
    obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'tec000'
    obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename

    return 0
