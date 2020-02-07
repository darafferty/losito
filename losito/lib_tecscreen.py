# -*- coding: utf-8 -*-
"""
Created on Fri Jan 31 10:14:35 2020

@author: Henrik Edler <henrik.edler@hs.uni-hamburg.de>
"""
import logging, functools, os
import numpy as np
import multiprocessing as mp
from numpy import sqrt, fft, random, pi
from scipy.interpolate import RectBivariateSpline
import astropy.units as u
import astropy.coordinates as coord
from astropy.time import Time
from astropy.coordinates import EarthLocation, SkyCoord, ITRS
from .progress import progress

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
    # pierce directions are defined as going from receiver to source
    PD = d
    return PP, PD 

def get_PP_PD(sp, directions, times, h_ion = 200.e3, ncpu = None):
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
        Pierce direction unit verctors in geocentric ITRS.
        The directions are oriented such that the point from the source
        towards earth.
        The (n,l,3) shape corresponds to (timestamp, direction, xyz).
        Since the coord sys is geocentric and not horizontal, the source 
        directions are the same for every station.
    '''
    if ncpu == 0:
        ncpu = mp.cpu_count()
    pool = mp.Pool(processes = ncpu)
    map_args = [(sp, d, times, h_ion) for d in directions]
    PP_PD = pool.map(get_PP_PD_per_source, map_args)
    pool.close() # w/o close+join: OSError: [Errno 12] Cannot allocate memory
    pool.join()
    # PP shaped as (timestamp, station, sources, xyz)
    PP = np.array([u for (u,v) in PP_PD]).swapaxes(0,1).swapaxes(1,2)
    # PD shaped as (timestamp, source, xyz)
    PD = np.array([v for (u,v) in PP_PD]).swapaxes(0,1)
    return PP, PD
    
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
    

def screen_grid(edges, gridsize, R_earth = 6364.62e3, h_ion = 200.0e3):
    '''
    
    Parameters
    ----------
    edges : (4,) ndarray
        Pierce point edges in minlon, maxlon, minlat, maxlat. (Radians)
    gridsize : int
        Resolution of the greater grid axis.
    R_earth : TYPE, optional
        DESCRIPTION. The default is 6364.62e3.
    h_ion : TYPE, optional
        DESCRIPTION. The default is 200.0e3.

    Returns
    -------
    None.

    '''
    min_lon, max_lon, min_lat, max_lat,  = edges
    lat_wdth, lat_center = max_lat - min_lat, np.mean([max_lat, min_lat])    
    # To get similar length scale res, cosine factor
    lon_wdth = (max_lon - min_lon) 
    res_rad = np.max([lat_wdth, lon_wdth * np.cos(lat_center)]) / gridsize
    res_lon = res_rad / np.cos(lat_center)
    
    pixel_lat = np.ceil(lat_wdth/res_rad)
    pixel_lon = np.ceil(lon_wdth/res_lon)  
    
    grid_lat = np.linspace(min_lat, max_lat, pixel_lat)
    grid_lon = np.linspace(min_lon, max_lon, pixel_lon)
    # update resolution to get rid of rounding error
    cellsz_lat = lat_wdth/pixel_lat
    cellsz_lon = lon_wdth/pixel_lon
    
    return grid_lon, grid_lat, cellsz_lon, cellsz_lat
    
    
def get_tecscreen(sp, directions, times, h_ion = 200.e3, maxvtec = 50., 
                  maxdtec = 1., screensize = 400., ncpu = None, 
                  expfolder = None, absoluteTEC = True):
    ''' Return a tecscreen-array. The TEC values represent a daily 
    sinusoidal modulation peaking at 15h, overlaid with von Karman 
    turbulences. 
    Parameters
    ----------
    PP : (l,m,n,3) ndarray
        Ionospheric pierce points in geocentric coordinates.
        Axes correspond to (time, station, direction, xyz)
    PD : (l,n,3) ndarray
        Pierce directions in geocentric coords. (time, direction, xyz)
    times : (n,) ndarray
        Timestamps in MJDseconds
    size : int
        Size of the greater screen axis.
    maxvtec : float, optinal. Default = 50.
        Daytime vTEC peak value for tec modulation in TECU.
    maxdtec : float, optional. Default = 1.
        Maximum allowed dTEC of the screen for a single timestep. 
    savefile: str, optional. Default = None.
        Filename of the output .npy tecscreen array. 
    absoluteTEC : bool, optional. Default = True
        Whether to use absolute (vTEC) or differential (dTEC) TEC        
    Returns
    -------
    tecscreen : (n, i, j) ndarray
        TECscreen time dependent grid, the axes are (time, lon, lat)
    '''    
    if ncpu == 0:
        ncpu = mp.cpu_count()
    # Get the ionospheric pierce points)
    PP, PD = get_PP_PD(sp, directions, times, h_ion, ncpu)   

    # Find the outermost piercepoints to define tecscreen size:
    PP_llr = geocentric_to_geodetic(PP)
    edges = [np.min(PP_llr[...,0]), np.max(PP_llr[...,0]), 
             np.min(PP_llr[...,1]), np.max(PP_llr[...,1])]
    grid_lon, grid_lat, cellsz_lon, cellsz_lat = screen_grid(edges, screensize)
    # Get turbulent screen generator object and convert to array
    # TODO: Make sure the r0 and L values for the screen are appropriate!
    it = MegaScreen(1, 1000, windowShape = [len(grid_lon), len(grid_lat)], 
               dx = 1, theta = 0, seed = 10, numIter = len(times))
    tecsc = np.zeros((len(times), len(grid_lon), len(grid_lat))) # this can't be parallelized :(
    for i, sc in enumerate(it):
        progress(i, len(tecsc), status='Generating tecscreen')
        tecsc[i] = sc
        
    # Rescale each timestep screen to have max dtec 
    tecsc *= maxdtec / (np.max(tecsc, axis=0) - np.min(tecsc, axis=0))
    if absoluteTEC:  
        tecsc = (daytime_tec_modulation(times)[:,np.newaxis,np.newaxis]
                 * (tecsc + maxvtec))
    else:
        tecsc = (daytime_tec_modulation(times)[:,np.newaxis,np.newaxis]*tecsc)
    cos_pierce = (unit_vec(PP)*unit_vec(PD)[:,np.newaxis,:,:]).sum(-1)
    
    # Interpolate screen for each time and get values at pierce points
    TEC = np.zeros((len(times), len(sp), len(directions)))
    for (i, sc) in enumerate(tecsc): # iterate times
        sc_interp = RectBivariateSpline(grid_lon, grid_lat, sc)
        TEC_ti = sc_interp.ev(PP_llr[i,:,:,0], PP_llr[i,:,:,1])
        TEC[i] = TEC_ti
    # slant TEC from pierce angle: (e_r*e_d)**-1 = cos(pierce_angle)**-1
    TEC /= cos_pierce  
    
    if expfolder:
        if not os.path.exists(expfolder):
            os.mkdir(expfolder) #exist_ok=True
        
        np.save(expfolder + '/tecscreen.npy', tecsc)
        np.save(expfolder + '/piercepoints.npy', PP_llr)
        np.save(expfolder + '/times.npy', times)
        np.save(expfolder + '/grid.npy', np.array([grid_lon, grid_lat]))
        np.save(expfolder + '/res.npy', np.array([cellsz_lon, cellsz_lat]))
        logging.info('Exporting tecscreen data to: ' + expfolder+'/')        
    return TEC




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


def FftScreen(spectrum, shape, pixelSize=1.0, seed = None):
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
    if not seed:
        seed = np.random.randint(0,10000)
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
    seed = None
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
    seed = None
):
    """
    Generate a sequence of phase screens with a Von Karman spectrum.
    Parameters
    ----------
    r0 : float
         Fried parameter :math:`r_0` in tweeter pixel units.
    L0 : float
         Outer scale of turbulence in tweeter pixel units.
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
    spectrum = functools.partial(VonKarmanSpectrum, r0=r0, L0=L0)
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
