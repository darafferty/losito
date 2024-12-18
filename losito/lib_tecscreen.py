# -*- coding: utf-8 -*-
"""
Created on Fri Jan 31 10:14:35 2020

@author: Henrik Edler <henrik.edler@hs.uni-hamburg.de>
"""
import functools, os
import numpy as np
import multiprocessing as mp
from numpy import sqrt, fft, random, pi
from scipy.interpolate import RectBivariateSpline
from scipy.special import gamma
import astropy.units as u
import astropy.coordinates as coord
from astropy.time import Time
from astropy.coordinates import EarthLocation, SkyCoord, ITRS
from .lib_io import progress, logger

# Workaround for unavailable USNO server, both these mirrors work as May 2020
from astropy.utils import iers
iers.Conf.iers_auto_url.set('https://datacenter.iers.org/data/9/finals2000A.all')
#iers.Conf.iers_auto_url.set('ftp://cddis.gsfc.nasa.gov/pub/products/iers/finals2000A.all')
R_earth = 6364.62e3

def unit_vec(v):
    'Return unit vector of v w.r.t. last axis'
    return v/np.linalg.norm(v, axis = -1, keepdims = True)

def geocentric_to_geodetic(points):
    ''' Geocentric XYZ to longitude and latitude conversion.
    The input points can have arbitrary shape, the only restriction is that
    the last axis has length of 3 and corresponds to X/Y/Z.
    Parameters
    ----------
    points : (...,3) ndarray
        Input points
    Returns
    -------
    LonLatR: (...,3) ndarray           
            lon : (...,) ndarray
                Corresponding longitude in rad 
            lon : (...,) ndarray
                Corresponding latitude in rad
            R : (...,) ndarray
                Corresponding radius.
    '''
    R = np.linalg.norm(points, axis = -1)
    lon = np.arctan2(points[...,1], points[...,0])
    lat = np.arcsin(points[...,2]/R)
    return np.moveaxis(np.array([lon, lat, R]), 0, -1)


def daytime_from_mjds(t):
    ''' Turn an array of modified julian day seconds into an array
    containing the day hour, including decimal fraciton.
    Parameters
    ----------
    t : (n,) ndarray. MJDseconds timestamps.
    Returns
    -------
    hours : (n,) ndarray. Daytime hours.
    '''
    jd = Time(t/(3600.*24.), format = 'mjd')
    hours = np.array([step.hour for step in jd.to_datetime()])
    fracs = np.array([step.minute/60. for step in jd.to_datetime()])
    return hours + fracs

def daytime_tec_modulation(t):
    ''' Get the tec modulation values corresponding to the daytime derived
    from mjds timestamps. Peaking at 15h, with a tecmax/tecmin ration of 10.
    Parameters
    ----------
    t : (n,) ndarray. MJDseconds timestamps
    Returns
    -------
    modulation : (n,) ndarray. TEC modulation, between 0.05 and 1.
    '''
    # TODO: longitude dependency of modulation.
    hours = daytime_from_mjds(t)
    modulation = 0.45 * np.sin((hours - 9)*np.pi/12.) + 0.55
    return modulation

# def screen_grid(edges, angRes, hIon):
#     '''Get the screen grid from the screen edges and the angular resolution.
#     Parameters.
#     ----------
#     edges : (4,) ndarray
#         Pierce point edges in minlon, maxlon, minlat, maxlat. (Radians)
#     angRes : float. Angular resoluation of grid in arcsec
#
#     Returns
#     -------
#     grid_lon : (n,) ndarray
#         Longitude values of the grid in rad.
#     grid_lat : (m,) ndarray
#         Latitude values of the grid in rad.
#     cellsz_lon : float. Longitudinal size of grid cell.
#     cellsz_lat : flaot. Latidude size of grid cell.
#     '''
#     min_lon, max_lon, min_lat, max_lat,  = edges
#     lat_wdth, lat_center = max_lat - min_lat, np.mean([max_lat, min_lat])
#     # To get similar length scale res, cosine factor
#     lon_wdth = (max_lon - min_lon)
#     res_rad = np.arctan(np.tan(np.deg2rad(angRes / 3600) * hIon
#                                 / (R_earth + hIon)))
#     res_lon = res_rad / np.cos(lat_center)
#     npixel_lat = np.ceil(lat_wdth/res_rad)
#     npixel_lon = np.ceil(lon_wdth/res_lon)
#     grid_lat = np.linspace(min_lat, max_lat, npixel_lat)
#     grid_lon = np.linspace(min_lon, max_lon, npixel_lon)
#     # update resolution to get rid of rounding error
#     cellsz_lat = lat_wdth/npixel_lat
#     cellsz_lon = lon_wdth/npixel_lon
#     return grid_lon, grid_lat, cellsz_lon, cellsz_lat


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
        -itrs : (n,) ITRS frame object
              ITRS object, corresponding to timestamps in mjd seconds.
            
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
    sp, radec, itrs, hIon = args
    direction = SkyCoord(radec[0], radec[1], frame=coord.FK5, unit=(u.deg, u.deg))
    direction = direction.transform_to(itrs) # this is bottleneck here
    # TODO: The ITRS values seem to vary randomly each calculation?
    PD = np.array([direction.x, direction.y, direction.z]).T # source direction unit vector in itrs
    S = np.array([sp.x.value, sp.y.value, sp.z.value]) # station position in itrs, [m]
    alpha = -(PD @ S) + np.sqrt((PD @ S)**2 + (R_earth + hIon)**2 - (S**2).sum(0))
    PP = S.T[np.newaxis,:,:] + alpha[:,:,np.newaxis] * PD[:,np.newaxis,:]
    # pierce directions are defined as going from receiver to source
    return PP, PD

def get_PP_PD(sp, directions, times, hIon, ncpu):
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
    hIon : float, Ionosphere height in m
    ncpu : int,

    Returns
    -------
    PP : (n,m,l,3) ndarray
        Pierce points in geocentric ITRS. Unit: meter
        The (n,m,l3) shape corresponds to (timestamp, station, direction, xyz).
    PD : (n,l,3) ndarray
        Pierce direction unit verctors in geocentric ITRS.
        The directions are oriented such that the point from the source
        towards earth.
        The (n,l,3) shape corresponds to (timestamp, direction, xyz).
        Since the coord sys is geocentric and not horizontal, the source 
        directions are the same for every station.
    '''
    sp = EarthLocation.from_geocentric(x = sp[:,0], y= sp[:,1], z = sp[:,2], unit = 'meter')
    itrs = ITRS(obstime=Time(times/(3600*24), format = 'mjd'))
    map_args = [(sp, d, itrs, hIon) for d in directions]
    pool = mp.Pool(processes = ncpu)
    PP_PD = pool.map(get_PP_PD_per_source, map_args)
    pool.close() # w/o close+join: OSError: [Errno 12] Cannot allocate memory
    pool.join()
    # PP shaped as (timestamp, station, sources, xyz)
    PP = np.array([u for (u,v) in PP_PD]).swapaxes(0,1).swapaxes(1,2)
    # PD shaped as (timestamp, source, xyz)
    PD = np.array([v for (u,v) in PP_PD]).swapaxes(0,1)
    return PP, PD


def screen_grid_comoving(edges, angRes, hIon):
    '''Get the screen grid from the comoving screen edges and the angular 
    resolution.    
    Parameters. 
    ----------
    edges : (4,n) ndarray
        Pierce point edges in minlon, maxlon, minlat, maxlat per timestep [rad]
    angRes : float. Angular resolution of grid in arcsec
    Returns
    -------
    grid_lon : (n,m) ndarray
        Longitude values of the grid in rad. Shape : (time, grid)
    grid_lat : (n,l) ndarray
        Latitude values of the grid in rad. Shape : (time, grid)
    cellsz_lon : (n,) ndarray.
        Longitudinal size of grid cell per timestep.
    cellsz_lat : (n,) ndarray.
        Latidude size of grid cell per timestep.
    '''    
    min_lon, max_lon, min_lat, max_lat,  = edges
    lat_center = np.mean([max_lat, min_lat], axis = 0)  
    # To get similar length scale res, cosine factor
    res_rad = np.arctan(np.tan(np.deg2rad(angRes / 3600) * hIon 
                                / (R_earth + hIon))) 
    res_lon = res_rad / np.cos(lat_center)
    # Since sources move on sky grid size changes.
    # But MegaScreen needs constant screen size. So the smaller screens have
    # to be extended. They are extended in pos. lon / lat direction.
    npixel_lat = np.ceil((max_lat - min_lat)/res_rad).astype(int)
    npixel_lon = np.ceil((max_lon - min_lon)/res_lon).astype(int)
    mssng_px_lt = np.max(npixel_lat) - npixel_lat
    mssng_px_ln = np.max(npixel_lon) - npixel_lon
    max_lat += mssng_px_lt * res_rad # Fill for timesteps where screen smaller
    max_lon += mssng_px_ln * res_lon # Fill for timesteps where screen smaller
    grid_lat = np.linspace(min_lat, max_lat, np.max(npixel_lat)).T
    grid_lon = np.linspace(min_lon, max_lon, np.max(npixel_lon)).T
    # update resolution to get rid of rounding error
    cellsz_lat = (max_lat - min_lat) / np.max(npixel_lat)
    cellsz_lon = (max_lon - min_lon) / np.max(npixel_lon)
    logger.info('Tecscreen resolution {} x {} pixel'.format(len(grid_lat[0]), len(grid_lon[0])))
    return grid_lon, grid_lat, cellsz_lon, cellsz_lat


def comoving_tecscreen(sp, directions, times, hIon = 250.e3, vIon = 10,
                       alpha = 11/3, r0=10, maxvtec = 10,
                       angRes = 60, ncpu = None, seed = 0, expfolder = None):
    ''' Return TEC values for [times, station, source]. 
    The differential TEC is modeled using a tecscreen with von-Karman
    turbulence. Absolute TEC (optional) is modeled sinusoidal and peakes at 
    15h. Airmass-effect caused by elevation of source is considered.
    To save computation time, the longitude-latitude grid of the screen is
    comoving, and the screen is just big enough to cover all piercepoints.

    Parameters
    ----------
    sp : (n,3) ndarray
        Station positions in geocentric coordinates (meters).
    direction : (m,3) ndarray
          Source directions RA and DEC in degree.
    times : (n,) ndarray
        Timestamps in MJDseconds
    hIon : float, optional. Default = 250e3 meter.
        Height of ionospheric layer in meter.
    vIon : float, optional. Default = 10 m/s
        Velocity of tecscreen in frozen turbulence model.
    alpha : float, optional. Default = 11/3
        Ionosphere power spectrum exponent. Is 11/3 for Kolmogorov, de Gasperin and Mevius found ~ 3.89 with LOFAR.
    r0 : float, optional. Default = 10km
        Diffractive scale / Fried parameter at 150MHz in kilometer
    maxvtec : float, optinal. Default = 50
        Daytime vTEC peak value for tec modulation in TECU.
    angRes : float, optional. Default = 60 arcseconds
        Angular resolution of the tecscreen grid as seen from a station.
    seed : int, optional. 
        Random seed to reproduce turbulence.
    expfolder: str, optional. Default = None.
        If filename is set, tecscreen array and other data for a plot
        are exported to the specified directory. Beware: For a high resolution
        tecscreen, the tecscreen array can easily overflow the system memory.
    Returns
    -------
    TEC : (n, i, j) ndarray
        TECscreen time dependent grid, the axes are (time, lon, lat)
    '''    
    if ncpu == 0:
        ncpu = mp.cpu_count()
    # Find pierce points
    PP, PD = get_PP_PD(sp, directions, times, hIon, ncpu)   
    PP_llr = geocentric_to_geodetic(PP)
    cos_pierce = (unit_vec(PP)*unit_vec(PD)[:,np.newaxis]).sum(-1)
    # Find the outermost piercepoints to define tecscreen size:
    edges = np.array([np.min(PP_llr[..., 0], axis=(1,2)),
                      np.max(PP_llr[..., 0], axis=(1,2)),
                      np.min(PP_llr[..., 1], axis=(1,2)),
                      np.max(PP_llr[..., 1], axis=(1,2))])
    # Find the grid for each timestep. The sources move on the sky, so the
    # minimal fixed resolution grid in lon, lat that covers all PP changes    
    grid_lon, grid_lat, cs_lon, cs_lat = screen_grid_comoving(edges, angRes, 
                                                              hIon)
    if expfolder: # Export for plotting etc.
        if not os.path.exists(expfolder):
            os.mkdir(expfolder) #exist_ok=True
        export = np.zeros((len(times), len(grid_lon[0]), len(grid_lat[0])))
        
    # Find scales for von-Karman turbulence
    r0 = np.arctan(r0*1e3/hIon)/np.deg2rad(angRes/3600)
    L0 = np.arctan(1000e3/hIon)/np.deg2rad(angRes/3600) # Assuming L0 = 1000km
    dx = vIon /(hIon*np.tan(np.deg2rad(angRes/3600))) # pixel per second
    dx *= (times[-1] - times[0])/len(times) # pixel per step
    squareFFTsize = (np.ceil(np.max([len(grid_lon[0]), len(grid_lat[0])])/2)*2).astype(int) # round to next even number

    # get the screen generator
    sc_gen = MegaScreen(r0, L0, alpha, nfftTweeter=squareFFTsize, windowShape =
           [len(grid_lon[0]), len(grid_lat[0])], dx = dx, theta = 0, seed = seed, numIter = len(times))
    TEC = np.zeros((len(times), len(sp), len(directions)))

    # differential TEC from screen
    for i, tecsc in enumerate(sc_gen):
        progress(i, len(times), status='Generating tecscreen')        
        # Interpolate screen for each time and get values at pierce points
        tecsc /= 56.32 # transformation from PHASE at 150MHz to dTEC (to make difdractive scale r0 physical)
        sc_interp = RectBivariateSpline(grid_lon[i], grid_lat[i], tecsc)
        TEC_ti = sc_interp.ev(PP_llr[i,:,:,0], PP_llr[i,:,:,1])
        # slant TEC from pierce angle: (e_r*e_d)^-1 = cos(pierce_angle)^-1
        TEC[i] = TEC_ti/cos_pierce[i]       
        if expfolder: # export screen data for plotting
            export[i] = tecsc

    # add constant vertical TEC (taking into account projection and daily variation)
    daytime_variation_factor = daytime_tec_modulation(times)
    if maxvtec > 0.:
        logger.info('Adding constant TEC..')
        for i, t in enumerate(times):
            TEC[i] += daytime_variation_factor[i]*maxvtec/cos_pierce[i]
            if expfolder:
                export[i] += daytime_variation_factor[i]*maxvtec

    if expfolder: # TODO check plotting maxsize
        np.save(expfolder + '/tecscreen.npy', export)
        np.save(expfolder + '/piercepoints.npy', PP_llr)
        np.save(expfolder + '/times.npy', times)
        np.save(expfolder + '/grid_lon.npy', grid_lon )
        np.save(expfolder + '/grid_lat.npy', grid_lat)
        np.save(expfolder + '/res.npy', np.array([cs_lon, cs_lat]))
        logger.info('Exporting tecscreen data to: ' + expfolder+'/')
    return TEC
           
def delta_z(nu, z, h_iono=250e3, nu_plasma=10e6, delta_h=50e3):
    """
    Helper function, currently not used. Calculate the ionospheric refraction angle.
    Parameters
    ----------
    nu
    z
    h_iono
    nu_plasma
    delta_h: thickness of ionospheric layer

    Returns
    -------
    """
    return (2*delta_h*np.sin(np.deg2rad(z))/(3*6370e3)) * (nu_plasma/nu)**2 * (1 + h_iono/6370e3) * (np.cos(np.deg2rad(z))**3 + 2*h_iono/6370e3)

# The following code is taken from "Simulating large atmospheric phase 
# screens using a woofer-tweeter algorithm " (2016) by D. Buscher.
# Optics Express Vol. 24, Issue 20, pp. 23566-23571 (2016).

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
def FrequencyGrid(shape, pixelSize=1.0):
    """Return a 2-d grid with absolute frequency relevant to an FFT of a
    grid of pixels of size pixelSize."""
    return sqrt(
        np.add.outer(
            np.fft.fftfreq(shape[0], pixelSize) ** 2,
            np.fft.fftfreq(shape[1], pixelSize) ** 2,
        )
    )


def VonKarmanSpectrum(f, r0, L0=1e6, alpha=11.0 / 3.0):
    """Phase spectrum of atmospheric seeing with Von Karman turbulence"""
    return 0.0229 * r0 ** (2.0 - alpha) * (f ** 2 + 1 / L0 ** 2) ** (-alpha / 2)

def GeneralizedVonKarmanSpectrum(f, r0, L0=1e6, alpha=11.0/3.0):
    """
    Taken from >>Zernike expansions for non-Kolmogorov turbulence<<,
    correctly normalize such that r0 follows the 1rad/aperture definition.
    """
    def A_beta(beta):
        return ((2**(beta-2)*(gamma(beta/2+1)**2)*gamma(beta/2+2)*gamma(beta/2)*np.sin(np.pi*(beta/2-1)))
                / ((np.pi**beta)*gamma(beta+1)))

    return A_beta(alpha) * r0 ** (2.0 - alpha) * (f ** 2 + 1 / L0 ** 2) ** (-alpha / 2)


def FftScreen(spectrum, shape, pixelSize=1.0, seed = 0):
    """Generate infinite sequence of screens based on filtered 2D white noise
    Parameters
    ----------
    spectrum : Callable[[numpy.ndarray[float]],numpy.ndarray[float]]
       spectrum of fluctuations, assumed radially symmetric
    shape: Tuple[int,int]
        Size of output grid
    pixelSize: float
        Pixel size of output grid
    Yields
    ------
    out : ndarray
        2D array of phase disturbances
    """
    f = FrequencyGrid(shape, pixelSize)
    filter = sqrt(spectrum(f) * f[0, 1] * f[1, 0])
    if seed == 0:
        seed = np.random.randint(0, 10000)
    random.seed(int(seed))
    while 1:
        sample = random.normal(size=(2,) + filter.shape)
        result = fft.fft2(filter * (sample[0] + 1j * sample[1]))
        yield result.real
        yield result.imag


def SplineTiles(tileGenerator):
    """Generate a sequence of splined tiles with shape (n0/2,n1) from a
    sequence of tiles with shape (n0,n1)
    """
    previous = next(tileGenerator)
    n0 = previous.shape[0] // 2
    assert n0 * 2 == previous.shape[0]
    cspline = np.cos(np.linspace(0, pi / 2, n0, endpoint=False))
    sspline = np.sin(np.linspace(0, pi / 2, n0, endpoint=False))
    for current in tileGenerator:
        yield previous[n0:] * cspline[:, np.newaxis] + current[:n0] * sspline[
            :, np.newaxis
        ]
        previous = current


def GridInterpolator(grid):
    xgrid = np.arange(grid.shape[0])
    ygrid = np.arange(grid.shape[1])
    def interpolator(x, y, grid = False):
        pass 
    return RectBivariateSpline(xgrid, ygrid, grid)


def SlidingPixels(tileGenerator, x, y, dx):
    """Return phase values from a set of pixel coordinates sliding along an infinite ribbon.
    Parameters
    ----------
    tileGenerator: iterator
        A sequence of 2D phase screens which are stiched together to form a ribbon
    x,y: 1D arrays
        starting pixel coordinates in units of the tile grid size
    dx: float
        increment of pixel "x" coordinate on each iteration
    Yields
    -------
    1D array
        phase values at each pixel
    """
    tiles = [next(tileGenerator)]
    xtile = tiles[0].shape[0]
    assert xtile >= dx
    xmin = np.amin(x)
    xmax = np.amax(x)
    numTile = int(np.ceil((xmax - xmin + dx) / xtile))
    for i in range(numTile):
        tiles.append(next(tileGenerator))
    interpolator = GridInterpolator(np.concatenate(tiles))
    xoffset = -xmin
    ynew = y - np.amin(y)
    while True:
        yield interpolator(x + xoffset, ynew, grid=False)
        xoffset += dx
        if xoffset + xmin > xtile:
            tiles.pop(0)
            tiles.append(next(tileGenerator))
            interpolator = GridInterpolator(np.concatenate(tiles))
            xoffset -= xtile


def PixelCoords(origin, shape, pixelSize=1, theta=0):
    """Return x and y coodinates of a grid of pixels in rectangular region
    given by *origin* and *shape*, in a frame scaled to *pixelSize* and
    rotated by angle *theta*
    """
    c = np.cos(theta)
    s = np.sin(theta)
    x = (origin[0] + np.arange(shape[0])) * pixelSize
    y = (origin[1] + np.arange(shape[1])) * pixelSize
    return np.add.outer(c * x, s * y).flatten(), np.add.outer(-s * x, c * y).flatten()


def SlidingWindows(
    tileGenerator, shape, dx, origins=((0.0, 0.0),), pixelSize=1, theta=0.0
):
    """Return phase values from a set of rectangular windows sliding along an infinite ribbon.
    Parameters
    ----------
    tileGenerator: iterator
        A sequence of 2D phase screens which are stiched together to form a ribbon
    origins: sequence of pairs of floats
        The origins of each of the rectangular windows
    shape: tuple
        Shape of rectangular window (same for all windows)
    dx: float
        Increment of pixel `x` coordinate on each iteration
     Yields
     -------
     2D array
         phase values at each pixel
     """
    coords = [
        PixelCoords(origin=origin, shape=shape, pixelSize=pixelSize, theta=theta)
        for origin in origins
    ]
    coords = np.array(coords)
    x = coords[:, 0, :].flat
    y = coords[:, 1, :].flat
    numWindow = len(origins)
    if numWindow == 1:
        newshape = shape
    else:
        newshape = [numWindow] + list(shape)
    for screen in SlidingPixels(tileGenerator, x, y, dx):
        yield np.reshape(screen, newshape)


def NestedSpectra(spectrum, f0, eps=1e-6):
    grad = (spectrum(f0 * (1 + eps)) - spectrum(f0 * (1 - eps))) / (2 * f0 * eps)
    c1 = spectrum(f0)

    def OuterSpectrum(f):
        s = spectrum(f)
        s1 = np.where(
            f < f0, c1 - 2 * grad * f0 / np.pi * np.cos(np.pi * f / (2 * f0)), s
        )
        return np.where(s1 < s, s1, s)

    def InnerSpectrum(f):
        return spectrum(f) - OuterSpectrum(f)

    return InnerSpectrum, OuterSpectrum


def NestedScreen(
    spectrum,
    windowShape,
    dx,
    windowOrigins=((0.0, 0.0),),
    pixelSize=1.0,
    theta=0.0,
    nfftWoofer=256,
    nfftTweeter=256,
    frequencyOverlap=4.0,
    fractionalSupport=0.5,
    debug=False,
    numIter=None,
    seed = 0
):
    """Generate a sequence of phase screens for an arbitrary spectrum
    Parameters
    ----------
    spectrum: Callable[[numpy.ndarray[float]],numpy.ndarray[float]]
       Returns the spectral power density of the phase perturbations at a given frequency
    Notes
    -----
    See MegaScreen() for the other parameters
    """
    if seed == 0:
        seed = np.random.randint(0,10000)
    wooferPixelSize = nfftTweeter / (2 * frequencyOverlap)
    f0 = 1 / (2 * wooferPixelSize) * fractionalSupport
    wooferSpectrum, tweeterSpectrum = NestedSpectra(spectrum, f0)
    innerWindows = SlidingWindows(
        SplineTiles(
            FftScreen(wooferSpectrum, (nfftWoofer, nfftWoofer), wooferPixelSize,
                      seed = seed)
        ),
        dx=dx / wooferPixelSize,
        shape=windowShape,
        origins=windowOrigins,
        pixelSize=pixelSize / wooferPixelSize,
        theta=theta,
    )
    outerWindows = [
        SlidingWindows(
            SplineTiles(
                FftScreen(tweeterSpectrum, (nfftTweeter, nfftTweeter), pixelSize,
                          seed = seed + 1)
            ),
            dx=dx,
            shape=windowShape,
            origins=[origin],
            pixelSize=pixelSize,
            theta=theta,
        )
        for origin in windowOrigins
    ]
    iter = 0
    while numIter is None or iter < numIter:
        iter += 1
        inner = next(innerWindows)
        outer = np.squeeze(np.array([next(o) for o in outerWindows]))
        if debug:
            yield inner, outer, inner + outer
        else:
            yield inner + outer
def MegaScreen(
    r0=7.0,
    L0=7000.0,
    alpha=11/3,
    windowShape=(100, 100),
    dx=3.5,
    windowOrigins=((0.0, 0.0),),
    pixelSize=1.0,
    theta=0.0,
    nfftWoofer=256,
    nfftTweeter=256,
    frequencyOverlap=4.0,
    fractionalSupport=1.0,
    debug=False,
    numIter=None,
    seed = 0
):
    """
    Generate a sequence of phase screens with a Von Karman spectrum.
    Parameters
    ----------
    r0 : float
         Fried parameter :math:`r_0` in tweeter pixel units.
    L0 : float
         Outer scale of turbulence in tweeter pixel units.
    alpha : float
         Power spectrum exponent, alpha = 11/3 for Kolmogorov-like.
    windowShape : Tuple[int,int]
                  Shape of rectangular output window grid (same for all windows).
    dx : float
         Increment in the "x" coordinate of the tweeter phase screen between 
         subsequent calls. Represents the "frozen turbulence" windspeed in 
         tweeter pixels/iteration. Should be > 0. See note below about coordinate 
         directions.
    windowOrigins : Sequence[Tuple[float,float]]
                    Relative coordinates of the rectangular windows in the window 
                    coordinate system - note that this coordinate system is scaled
                    and rotated with respect to the to the coordinate system of 
                    the "woofer" and "tweeter" screens, and hence to the "wind" direction.
    pixelSize : float
                Size of the window pixels in tweeter pixel units 
                (typically <= 1.0).
    theta: float
           Angle in radians between the output window "x" axis and the 
           tweeter screen "x" axis. Used to simulate the wind travelling in a given 
           direction with respect to the window coordinate axes. See note below about
           the coordinate convention used.
    nfftWoofer : int
                 Size of the square FFT used to produce the woofer screen.
    nfftTweeter : int
                 Size of the square FFT used to produce the tweeter screen.
    frequencyOverlap : float
                       The Nyquist frequency of the woofer spectrum in units of the 
                       fundamental frequency of the tweeter spectrum.
    fractionalSupport : float
                        Frequency above which woofer spectrum is zero (the "crossover
                        frequency"), expressed as a fraction of the woofer Nyquist 
                        frequency.
    debug : boolean
            If true, yield additional debugging information along with phase screens.
    numIter : Optional[int]
            Number of iterations to stop after, or None to return an infinite,
            non-repeating sequence of phase screens.
    Yields
    ------
    screen  : numpy.ndarray[float]
              Wavefront perturbation at each pixel in each of the output windows, in
              radians. If there is only one window this is a 2-D array, otherwise 
              an array of 2-D arrays (i.e. a 3-D array) is returned.
    Notes
    -----
    The convention used in the above descriptions has the "x" coordinate corresponding 
    to the leftmost index of the 2-D phase screen arrays. This is a FORTRAN-like 
    convention, and when the phase screen is plotted in `matplotlib.imshow()` and similar
    image plotting functions, this coordinate appears as the "y" coordinate in the 
    image (albeit by default the "y" coordinate is plotted increasing downwards).
    """
    spectrum = functools.partial(VonKarmanSpectrum, r0=r0, L0=L0, alpha=alpha)
    return NestedScreen(
        spectrum,
        windowShape,
        dx,
        windowOrigins=windowOrigins,
        pixelSize=pixelSize,
        theta=theta,
        nfftWoofer=nfftWoofer,
        nfftTweeter=nfftTweeter,
        frequencyOverlap=frequencyOverlap,
        fractionalSupport=fractionalSupport,
        debug=debug,
        numIter=numIter,
        seed = seed
    )
