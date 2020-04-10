#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Noise operation for losito: adds Gaussian noise to a data column
"""
import logging, os
import numpy as np
from scipy.interpolate import interp1d
import casacore.tables as pt
from ..progress import progress

logging.debug('Loading NOISE module.')


def _run_parser(obs, parser, step):
    column = parser.getstr(step, 'outputColumn', 'DATA')
    parser.checkSpelling( step, ['outputColumn'])
    return run(obs, column)


def run(obs, column='DATA'):
    """
    Adds Gaussian noise to a data column. Scale of the noise, frequency-
    and station-dependency are calculated according to 'Synthesis Imaging 
    in Radio Astronomy II' (1999) by Taylor et al., page 175.    

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    column : str, optional
        Name of column to which noise is added
    """
    # TODO: ensure eta = 1 is accurate enough
    tab = pt.table(obs.ms_filename, readonly=False)
    eta = 1. # system efficiency. Roughly 1.0
    
    def SEFD(station1, station2, freq):
        '''
        Return the source equivalent flux density (SEFD) for all rows and a
        single fequency channel.
        The values for the SEFD were derived from van Haarlem 
        et al. (2013).
        
        Parameters
        ----------
        station1 : (n,) ndarray, dtype = int
            ANTENNA1 indices.
        station2 : (n,) ndarray, dtpe = int
            ANTENNA2 indices.
        freq : float
            Channel frequency in Hz.
        Returns
        -------
        SEFD : (n,) ndarray
            SEFD in Jansky.
        '''
        mod_dir = os.path.dirname(os.path.abspath(__file__))

        if obs.antenna == 'LBA':
            lba_mode = tab.OBSERVATION.getcol('LOFAR_ANTENNA_SET')[0] 
            if lba_mode == 'LBA_OUTER':
                points = np.loadtxt(mod_dir+'/../../data/SEFD_LBA_OUTER.csv',
                                    dtype=float, delimiter=',')
            elif lba_mode == 'LBA_INNER':
                points = np.loadtxt(mod_dir+'/../../data/SEFD_LBA_OUTER.csv',
                                    dtype=float, delimiter=',')
            elif lba_mode == 'LBA_ALL':
                points = np.loadtxt(mod_dir+'/../../data/SEFD_LBA_FULL.csv',
                                    dtype=float, delimiter=',')
            else: 
                logging.error('LBA mode "{}" not supported'.format(lba_mode))
                return 1
            # Lin. extrapolation, so edge band noise is not very accurate.
            SEFD = interp1d(points[:, 0], points[:, 1], fill_value='extrapolate',
                            kind='linear')(freq)
            return np.repeat(SEFD, len(station1)) # SEFD same for all BL
                
        if obs.antenna == 'HBA':
            # For HBA, the SEFD differs between core and remote stations
            p_cs = np.loadtxt(mod_dir + '/../../data/SEFD_HBA_CS.csv',
                                dtype=float, delimiter=',')
            p_rs = np.loadtxt(mod_dir + '/../../data/SEFD_HBA_RS.csv',
                                dtype=float, delimiter=',')
            names = np.array([_n[0:2] for _n in tab.ANTENNA.getcol('NAME')])            
            CS = tab.ANTENNA.getcol('LOFAR_STATION_ID')[np.where(names =='CS')]
            lim = np.max(CS) # this id separates the core/remote stations

            # The SEFD for 1 BL is the sqrt of the products of the 
            # SEFD per station
            SEFD_cs = interp1d(p_cs[:, 0], p_cs[:, 1], fill_value='extrapolate',
                            kind='linear')(freq)
            SEFD_rs = interp1d(p_rs[:, 0], p_rs[:, 1], fill_value='extrapolate',
                            kind='linear')(freq)
            SEFD_s1 = np.where(station1 <= lim, SEFD_cs, SEFD_rs)
            SEFD_s2 = np.where(station2 <= lim, SEFD_cs, SEFD_rs)
            return np.sqrt(SEFD_s1*SEFD_s2)
        
    chan_width = tab.SPECTRAL_WINDOW.getcol('CHAN_WIDTH').flatten()
    freq = tab.SPECTRAL_WINDOW.getcol('CHAN_FREQ').flatten()
    ant1 = tab.getcol('ANTENNA1')
    ant2 = tab.getcol('ANTENNA2')
    exposure = tab.getcol('EXPOSURE')
    
    # Iterate over frequency channels to save memory.    
    for i, nu in enumerate(freq):
        progress(i, len(freq), status = 'estimating noise') # progress bar
        # find correct standard deviation from SEFD
        std = eta * SEFD(ant1, ant2, nu)
        std /= np.sqrt(2*exposure*chan_width[i])
        # draw complex valued samples of shape (row, corr_pol)
        noise = np.random.normal(loc=0, scale=std, size=[4,*np.shape(std)]).T
        noise = noise + 1.j*np.random.normal(loc=0, scale=std, size=[4,*np.shape(std)]).T
        noise = noise[:,np.newaxis,:]
        # TODO: is there a more efficient way to do this in taql?
        # Probably loading the predicted column is not necessary
        prediction = tab.getcolslice(column, blc = [i,-1], trc = [i,-1])     
        tab.putcolslice(column, prediction + noise,  blc = [i,-1], trc = [i,-1])
    tab.close()    
    return 0        
    