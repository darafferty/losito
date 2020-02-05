#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FARADAY operation for LoSiTo
"""
import numpy as np
import multiprocessing as mp
import logging as log
from astropy.coordinates import EarthLocation
# lofar specific imports
import EMM.EMM as EMM
from losoto.h5parm import h5parm
from losito.lib_tecscreen import get_PP_PD, unit_vec

log.debug('Loading FARADAY module.')

R_earth = 6364.62e3

def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename')
    hIono = parser.getfloat(step, 'hIono', 200.e3)
    ncpu = parser.getint('_global', 'ncpu', 0)
    parser.checkSpelling( step, ['h5parmFilename', 'hIono', 'ncpu'])
    return run(obs, h5parmFilename, hIono, ncpu)

def geocentric_to_lonlat(stationpos, degrees = True):
    '''
    Convert a single or multiple geocentric values to geodetic.
    Parameters
    ----------
    gc_points : (3,) ndarray or (n,3) ndarray
        Points in ITRS geocentric x, y, z. Values in meters.

    Returns
    -------
    lon : (n,) ndarray
        Longitude in degree
    lat : (n,) ndarray
        Latitude in degrees
    height : (n,) ndarray
        Height in meter
    '''
    #TODO: tecscreen XYZ_to_lonlat + this comined
    stationpos = EarthLocation.from_geocentric(*stationpos.T, unit = 'meter')
    stationpos = stationpos.to_geodetic()
    lon, lat, height = stationpos.lon, stationpos.lat, stationpos.height
    if (not degrees):
        return np.deg2rad(lon.value), np.deg2rad(lat.value), height.value
    else:
        return lon.value, lat.value, height.value
    


def Bfield(gc_points):
    '''
    Get Bfield value in nT.
    Parameters
    ----------
    gc_points : (3,) or (n,3) ndarray
        Point(s) at which to evaluate the B field. Must be given in
        geocentric ITRS. Unit: meter       

    Returns
    -------
    Bfield : (3,) or (n,3) ndarray
        B-field vectors (in nT??)
    '''
    # TODO: Iterating over everything + I/O from EMM takes ages. 
    # There is probably room for speed gains
    # TODO: date year fraction could be more accurately determined from timestamps. 
    # lat and lon must be in degrees for EMM
    lon, lat, h = geocentric_to_lonlat(gc_points)
    h /= 1000. # Seems like EMM needs height in km
    if hasattr(lon, "__len__"):
        B_xyz = np.zeros((len(lon), 3))
        for i, (lo, la, he) in enumerate(zip(lon, lat, h)):
            emm = EMM.WMM(date = 2018., lon = lo, lat = la, h = he)
            B_xyz[i] = emm.getXYZ()
        return B_xyz
    else:
        emm = EMM.WMM(date = 2018., lon = lon, lat = lat, h = h)
        return emm.getXYZ()
    



def run(obs, h5parmFilename, h_ion = 200.e3, stepname='rm', ncpu=0): 
    '''
    Add rotation measure Soltab to a TEC h5parm.
    '''
    
    h5 = h5parm(h5parmFilename, readonly=False)
    solset = h5.getSolset('sol000')
    soltab = solset.getSoltab('tec000') 
    sp = np.array(list(solset.getAnt().values()))  
    directions = np.array(list(solset.getSou().values()))
    times = soltab.getAxisValues('time')
    vTEC = soltab.getValues()[0] # TODO: is this actually vTEC?
    if ncpu == 0:
        ncpu = mp.cpu_count()
    log.info('''Calculating ionosphere pierce points for {} directions, {} 
              stations and {} timestamps...'''.format(len(directions), len(sp), 
              len(times)))
    
    PP, PD = get_PP_PD(sp, directions, times, h_ion, ncpu)
    
    log.info('Calculating B-field vectors for {} points...'.format(
              len(directions)*len(sp)*len(times)))
    pool = mp.Pool(processes = ncpu)
    B_vec = np.zeros_like(PP)
    for i in range(len(B_vec[0])): # iterate stations
        # TODO progressbar
        log.info('starting {}/{}'.format(i+1,len(B_vec[0])))
        B_vec[:,i] =  pool.map(Bfield, PP[:,i])
    
    log.info('Calculate rotation measure...')   
    c = 29979245800 # cm/s
    m = 9.109 * 10**(-28) # g
    e = 4.803 * 10**(-10) # cm**(3/2)*g**(1/2)/s                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              
    constants = 10**(-5)*e**3/(2*np.pi*m**2*c**4) # 1/nT
    TECU = 10**16 # m**(-2)
    
    # Get B parallel to PD at PP
    B_parallel = (PD[:,np.newaxis,:,:]*B_vec).sum(-1)     
    
    RM = constants * TECU * B_parallel * sTEC # rad*m**-2
    st = solset.makeSoltab('rotationmeasure', 'rotatim000', axesNames=
                           ['time', 'ant', 'dir'],
                           axesVals=[times, soltab.getAxisValues('ant'), 
                                             soltab.getAxisValues('dir')], 
                           vals=RM, weights = np.ones_like(RM))
    # Add CREATE entry to history
    st.addHistory('CREATE (by FARADAY operation of LoSiTo from '
                  + 'obs {0})'.format(h5parmFilename))
    h5.close()    
    # Update predict parset parameters for the obs
    obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
    if 'predict.applycal.steps' in obs.parset_parameters:
        obs.parset_parameters['predict.applycal.steps'].append(stepname)
    else:
        obs.parset_parameters['predict.applycal.steps'] = [stepname]
    obs.parset_parameters['predict.applycal.correction'] = 'rm000'
    obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'rm000'
    obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename

    return 0




