# -*- coding: utf-8 -*-
"""
FARADAY operation for LoSiTo
"""
import numpy as np
import multiprocessing as mp
import logging as log
from astropy.time import Time
# lofar specific imports
import EMM.EMM as EMM
from losoto.h5parm import h5parm
from ..lib_tecscreen import get_PP_PD, geocentric_to_geodetic
from ..progress import progress

log.debug('Loading FARADAY module.')

R_earth = 6364.62e3

def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename')
    hIono = parser.getfloat(step, 'hIono', 200.e3)
    ncpu = parser.getint('_global', 'ncpu', 0)
    parser.checkSpelling( step, ['h5parmFilename', 'hIono', 'ncpu'])
    return run(obs, h5parmFilename, hIono, ncpu)

def yearfrac_from_mjds(t):
    ''' Get year + decimal fraction from MJD seconds. 
    Parameters:
    ----------
    t : float, MJDseconds time.
    Returns
    -------
    year: flaot, year including decimal fraction.
    '''
    jd = Time(t/(3600.*24.), format = 'mjd')
    year =  jd.to_datetime().year
    month = jd.to_datetime().month
    day = jd.to_datetime().day
    return year + month/12 + day/30


def Bfield(gc_points, time = 5.0e9):
    '''
    Get Bfield value in nT.
    Parameters
    ----------
    gc_points : (3,) or (n,3) ndarray
        Point(s) at which to evaluate the B field. Must be given in
        geocentric ITRS. Unit: meter       
    time : float, optional. default = some time in 2017.
        MJD seconds single timestep for the simulation.
    Returns
    -------
    Bfield : (3,) or (n,3) ndarray
        B-field vectors (in nT?)
    '''
    llr = geocentric_to_geodetic(gc_points)
    lon = np.rad2deg(llr[...,0])
    lat = np.rad2deg(llr[...,1])
    height = (llr[...,2].mean() - R_earth) / 1000. # to km
    year = yearfrac_from_mjds(time)
    if hasattr(lon, "__len__"):
        B_xyz = np.zeros((len(lon), 3))
        emm = EMM.WMM(date = year, lon = lon[0], lat = lat[0], h = height)
        for i, (lo, la) in enumerate(zip(lon, lat)):
            emm.lon = lo
            emm.lat = la
            B_xyz[i] = emm.getXYZ()
        return B_xyz
    else:
        emm = EMM.WMM(date = year, lon = lon, lat = lat, h = height)
        return emm.getXYZ()
    

def run(obs, h5parmFilename, h_ion = 200.e3, stepname='rm', ncpu=0): 
    '''
    Add rotation measure Soltab to a TEC h5parm.
    '''
    if ncpu == 0:
        ncpu = mp.cpu_count()
    h5 = h5parm(h5parmFilename, readonly=False)
    solset = h5.getSolset('sol000')
    soltab = solset.getSoltab('tec000') 
    sp = np.array(list(solset.getAnt().values()))  
    directions = np.array(list(solset.getSou().values()))
    times = soltab.getAxisValues('time')
    
    sTEC = soltab.getValues()[0]
    if np.any(sTEC < 0): # Make sure absolute TEC is used
        log.warning('''Negative TEC values in {}. You are porbably using 
                    differential TEC. For an accurate estimate of the rotation
                    measure, absolute TEC is required.'''.format(h5parmFilename))    
    
    
    log.info('''Calculating ionosphere pierce points for {} directions, {} 
              stations and {} timestamps...'''.format(len(directions), len(sp), 
              len(times)))
    
    PP, PD = get_PP_PD(sp, directions, times, h_ion, ncpu)
    
    pool = mp.Pool(processes = ncpu)
    B_vec = np.zeros_like(PP)
    for i in range(len(B_vec[0])): # iterate stations
        prnt = 'Get B-field for {} pierce points'.format(
                                            len(directions)*len(sp)*len(times))
        progress(i, len(B_vec[0]), status = prnt)
        B_vec[:,i] =  pool.map(Bfield, PP[:,i])
    pool.close()
    pool.join()
    log.info('Calculate rotation measure...')   
    c = 29979245800 # cm/s
    m = 9.109 * 10**(-28) # g
    e = 4.803 * 10**(-10) # cm**(3/2)*g**(1/2)/s                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              
    constants = 10**(-5)*e**3/(2*np.pi*m**2*c**4) # 1/nT
    TECU = 10**16 # m**(-2)
    
    # Get B parallel to PD at PP
    # TODO: In which way is parallel defined? Going from source to receiver
    # or the other way around? Currently, PD is calculated such that it
    # is going from source to receiver. 
    B_parallel = (PD[:,np.newaxis,:,:]*B_vec).sum(-1)        
    RM = constants * TECU * B_parallel * sTEC # rad*m**-2
    
    # Delete rotationmeasureXYZ if it already exists
    stabnames = solset.getSoltabNames()
    rmtabs = [_tab for _tab in stabnames if 'rotationmeasure' in _tab]
    if 'rotationmeasure000' in solset.getSoltabNames():   
        log.info('''There are already rotation measure solutions present in
                 {}.'''.format(h5parmFilename+'/sol000'))    
        for rmt in rmtabs:
            solset.getSoltab(rmt).delete()
        
    st = solset.makeSoltab('rotationmeasure', 'rotationmeasure000', axesNames=
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
    obs.parset_parameters['predict.applycal.correction'] = 'rotationmeasure000'
    obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'rotationmeasure000'
    obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename

    return 0




