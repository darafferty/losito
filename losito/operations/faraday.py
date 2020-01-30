#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FARADAY operation for LoSiTo
"""
import numpy as np
import multiprocessing
from multiprocessing import Pool
import logging as log
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, SkyCoord, ITRS
import astropy.coordinates as coord
# lofar specific imports
import EMM.EMM as EMM
from losoto.h5parm import h5parm

logging.debug('Loading FARADAY module.')


R_earth = 6364.62e3
h_ion = 200.e3


def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename')
    hIono = parser.getfloat(step, 'hIono', 200.e3)
    ncpu = parser.getint('_global', 'ncpu', 0)
    parser.checkSpelling( step, ['h5parmFilename', 'hIono', 'ncpu'])
    return run(obs, h5parmFilename, hIono, ncpu)

def geocentric_to_lonlat(stationpos):
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
    stationpos = EarthLocation.from_geocentric(*stationpos.T, unit = 'meter')
    stationpos = stationpos.to_geodetic()
    lon, lat, height = stationpos.lon, stationpos.lat, stationpos.height
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
    

def get_PP_PD_per_source(args):
    ''' 
    Get the Pierce Points and the Pierce Directions for a single direction,
    <m> stations as well as <n> timestamps. The idea is that this function
    is used within a pool.map parallelization taking the individual directions
    as arguments.
    
    Parameters
    ----------
    args: list,
        containing (sp, radec, time) obeying these definitions:
        -sp : (m, 3) ndarray
              Station positions in meters ITRS XYZ
        -radec : (2,) ndarray
              Source direction RA and DEC in degree
        -time : (n,) ndarray
              Array containing timestamps in mjd seconds.
            
    Returns
    -------
    PP : (n, m, 3) ndarray
        Pierce points in geocentric ITRS. Unit: meter
        The (n, m, 3) shape corresponds to (timestamp, station, xyz).
    PD : (n, 3) ndarray
        Pierce direction unit verctors in geocenric ITRS.
        The directions are oriented such that the point from the source
        towards earth.
        The (n, 3) shape corresponds to (timestamp, xyz). Since the coord sys
        is geocentric and not horizontal, the source directions are the same
        for every station.
    '''
    sp, radec, times, h_ion = args 
    sp = EarthLocation.from_geocentric(x = sp[:,0], y= sp[:,1], z = sp[:,2], unit = 'meter')
    times = Time(times/(3600*24), format = 'mjd') # convert to mjd object
    itrs = ITRS(obstime=times)
    direction = SkyCoord(radec[0], radec[1], frame=coord.FK5, unit=(u.deg, u.deg))
    direction = direction.transform_to(itrs)
    # TODO: The ITRS values seem to vary randomly each calculation?
    d = np.array([direction.x, direction.y, direction.z]).T # source direction unit vector in itrs
    S = np.array([sp.x.value, sp.y.value, sp.z.value]) # station position in itrs, [m]

    alpha = -(d @ S) + np.sqrt((d @ S)**2 + (R_earth + h_ion)**2 - (S**2).sum(0))
    PP = S.T[np.newaxis,:,:] + alpha[:,:,np.newaxis] * d[:,np.newaxis,:]
    #PD: -d Minus: ray/ pierce direction going towards earth.
    PD = -d
    return PP, PD 

def get_PP_PD(sp, directions, times, h_ion = 200.e3, ncpu = 0):
    ''' 
    This is a wrapper function to parallelize get_PP_PD_per_source()
    and unpack the return.
    Get the Pierce Points and the Pierce Directions for <l> directions,
    <m> stations and <n> timestamps. 
    
    Parameters
    ----------
    sp : (m, 3) ndarray
        Station positions in meters ITRS XYZ
    directions : (l,2) ndarray
        Source directions RA and DEC in degree
    times : (n,) ndarray
        Array containing timestamps in mjd seconds.
    h_ion : float, optional. Ionosphere height in m, default: 200km
    ncpu : int, optional. 
            
    Returns
    -------
    PP : (n,m,l,3) ndarray
        Pierce points in geocentric ITRS. Unit: meter
        The (n,m,l3) shape corresponds to (timestamp, station, direction, xyz).
    PD : (n,l,3) ndarray
        Pierce direction unit verctors in geocenric ITRS.
        The directions are oriented such that the point from the source
        towards earth.
        The (n,l,3) shape corresponds to (timestamp, direction, xyz).
        Since the coord sys is geocentric and not horizontal, the source 
        directions are the same for every station.
    '''
    if ncpu == 0:
        ncpu = multiprocessing.cpu_count()
    pool = Pool(processes = ncpu)
    map_args = [(sp, d, times, h_ion) for d in directions]
    PP_PD_per_source = pool.map(get_PP_PD, map_args)
    # PP shaped as (timestamp, station, sources xyz)
    PP = np.array([u for (u,v) in PP_PD_per_source]).swapaxes(0,1).swapaxes(1,2)
    # PD shaped as (timestamp, source, xyz)
    PD = np.array([v for (u,v) in PP_PD_per_source]).swapaxes(0,1)
    return PP, PD

def unit_vec(v):
    'Return unit vector of v w.r.t. last axis'
    return v/np.linalg.norm(v, axis = -1, keepdims = True)

def run(obs, h5parmFilename, h_ion = 200.e3, stepname='rm', ncpu=0):    
    h5 = h5parm(h5parmFilename, readonly=False)
    solset = h5.getSolset('sol000')
    soltab = solset.getSoltab('tec000') 
    sp = np.array(list(solset.getAnt().values()))  
    directions = np.array(list(solset.getSou().values()))
    times = soltab.getAxisValues('time')
    vTEC = soltab.getValues()[0] # TODO: is this actually vTEC?

    log.info('''Calculating ionosphere pierce points for {} directions, {} 
             stations and {} timestamps...'''.format(len(directions), len(sp), 
             len(times)))
    PP, PD = get_PP_PD(sp, directions, times, h_ion, ncpu)
    
    log.info('Calculating B-field vectors for {} points...'.format(
              len(directions)*len(sp)*len(times)))
    pool = Pool(processes = ncpu)
    B_vec = np.zeros_like(PP)
    for i in range(len(B_vec[0])): # iterate stations
        # TODO progressbar
        print('starting {}/{}'.format(i+1,len(B_vec[0])))
        B_vec[:,i] =  pool.map(Bfield, PP[:,i])
    
    log.info('Calculate rotation measure...')   
    c = 29979245800 #cm/s
    m = 9.109 * 10**(-28) #g
    e = 4.803 * 10**(-10) #cm**(3/2)*g**(1/2)/s                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              
    constants = 10**(-5)*e**3/(2*np.pi*m**2*c**4) # 1/nT
    TECU = 10**16 # m**(-2)
    
    # Get B parallel to PD at PP
    B_parallel = (PD[:,np.newaxis,:,:]*B_vec).sum(-1)     
    # slant TEC from pierce angle: (e_r*e_d)**-1 = cos(pierce_angle)**-1
    cos_pierce = (unit_vec(PP)*unit_vec(PD)[:,np.newaxis,:,:]).sum(-1)
    # TODO: Is sTEC required here if we have sTEC in .h5? Probably not.
    sTEC = vTEC/cos_pierce
    
    RM = constants * TECU * B_parallel * sTEC # rad*m**-2
    st = solset.makeSoltab('rm', 'rm000', axesNames=['time', 'ant', 'dir'],
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




