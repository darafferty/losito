#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TEC operation for losito: creates h5parm with TEC values from TEC FITS cube
import logging
from losito.lib_operations import *
from astropy.io import fits as pyfits
from astropy import wcs
from losoto.h5parm import h5parm

logging.debug('Loading TEC module.')


def _run_parser(obs, parser, step):
    fitsFilename = parser.getstr( step, 'fitsFilename')
    h5parmFilename = parser.getstr( step, 'h5parmFilename', fitsFilename+'.h5parm')

    parser.checkSpelling( step, ['fitsFilename', 'h5parmFilename'])
    return run(obs, fitsFilename, h5parmFilename)


def run(obs, fitsFilename, h5parmFilename):
    """
    Creates h5parm with TEC values from TEC FITS cube.

    Parameters
    ----------
    fitsFilename : str
        Filename of input FITS cube with dTEC solutions.
    h5parmFilename : str
        Filename of output h5parm file.
    """
    # Get sky model properites
    ras, decs = obs.get_patch_coords()
    source_names = obs.get_patch_names()
    ndirs = len(source_names)

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
    antennaTable.append(list(zip(*(obs.stations, obs.stationpos))))
    sourceTable = solset.obj._f_get_child('source')
    vals = [[ra, dec] for ra, dec in zip(ras, decs)]
    sourceTable.append(list(zip(*(source_names, vals))))

    # Add CREATE entry to history
    soltabs = solset.getSoltabs()
    for st in soltabs:
        st.addHistory('CREATE (by TEC operation of LoSiTo from '
                      'obs {0} and FITS cube {1})'.format(h5parmFilename, fitsFilename))
    ho.close()

    # Update predict parset parameters for the obs
    obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
    if 'predict.applycal.steps' in obs.parset_parameters:
        obs.parset_parameters['predict.applycal.steps'].append('tec')
    else:
        obs.parset_parameters['predict.applycal.steps'] = ['tec']
    obs.parset_parameters['predict.applycal.tec.correction'] = 'tec000'

    return 0
