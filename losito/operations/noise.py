#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Noise operation for losito: adds Gaussian noise to a data column
"""
import logging
from losito.lib_operations import *
import casacore.tables as pt
import numpy as np

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
    # TODO: test HBA
    # TODO: ensure eta = 1 is accurate enough
    tab = pt.table(obs.ms_filename, readonly=False)
    eta = 1. # system efficiency. Roughly 1.0
    def SEFD(station1, station2, freq):
        '''
        Return the source equivalent flux density (SEFD) per baseline and
        frequency. The values for the SEFD were derived from van Haarlem 
        et al. (2013) by fitting a 5th degree polynomial to the datapoints.
        
        Parameters
        ----------
        station1 : TYPE
            DESCRIPTION.
        station2 : TYPE
            DESCRIPTION.
        freq : TYPE
            DESCRIPTION.

        Returns
        -------
        SEFD : () array
            SEFD in Jansky.
        '''       
        if obs.antenna == 'LBA':
            lba_mode = tab.OBSERVATION.getcol('LOFAR_ANTENNA_SET')[0] 
            if lba_mode == 'LBA_OUTER':
                # coeffs for grade 5 polynomial of SEFD model
                coeffs = [4.46492043e+05, -4.04156579e-02,  1.58636639e-09,
                         -3.09364148e-17,  2.93955326e-25, -1.06998148e-33]
            elif lba_mode == 'LBA_INNER':
                coeffs = [8.32889327e+05, -8.93829326e-02,  3.90153820e-09,
                          -8.23245656e-17,  8.35181243e-25, -3.25202160e-33]
            else: 
                logging.error('LBA mode "{}" not supported'.format(lba_mode))
                return 1
            SEFD = np.polynomial.polynomial.polyval(freq, coeffs)
            return np.tile(SEFD, (len(station1), 1)) # SEFD same for all BL
                
        if obs.antenna == 'HBA':
            # For HBA, the SEFD differs between core and remote stations
            names = np.array([n[0:2] for n in tab.ANTENNA.getcol('NAME')])
            ids = tab.ANTENNA.getcol('LOFAR_STATION_ID')
            CS = ids[np.where(names == 'CS')]
            lim = np.max(CS) # this id seperates the core/remote stations                       
            # coeffs for grade 5 polynomial of SEFD model 
            coeffs_cs = [1.61262289e+06, -4.77373916e-02, 5.58287303e-10, 
                         -3.21467027e-18, 9.09997476e-27, -1.01106905e-35]
            coeffs_rs = [1.14718003e+06, -3.39191007e-02, 3.96252077e-10,
                         -2.27947113e-18, 6.44567520e-27, -7.14899170e-36]   
            # The SEFD for 1 BL is the sqrt of the products of the 
            # SEFD per station
            SEFD_cs = np.polynomial.polynomial.polyval(freq, coeffs_cs)
            SEFD_rs = np.polynomial.polynomial.polyval(freq, coeffs_rs)
            
            SEFD_s1 = np.where(station1[:,np.newaxis] <= lim, SEFD_cs, SEFD_rs)
            SEFD_s2 = np.where(station2[:,np.newaxis] <= lim, SEFD_cs, SEFD_rs)
            return np.sqrt(SEFD_s1*SEFD_s2)
        
    chan_width = tab.SPECTRAL_WINDOW.getcol('CHAN_WIDTH') 
    freq = tab.SPECTRAL_WINDOW.getcol('CHAN_FREQ')
    rows = pt.taql('SELECT EXPOSURE, ANTENNA1, ANTENNA2 FROM $tab')
    # Calculate correct standard deviation for each (row, SB) 
    std = (SEFD(rows.getcol('ANTENNA1'), rows.getcol('ANTENNA2'), freq)
           / np.sqrt(2*np.outer(rows.getcol('EXPOSURE'), chan_width)))/eta
    # draw complex valued samples of shape (row, SB, corr_pol)
    noise = np.random.normal(loc=0, scale=std, size=[4,*np.shape(std)])
    noise = np.moveaxis(noise, 0, 2)
    noise = noise + 1.j*np.moveaxis(np.random.normal(loc=0, scale=std, 
                                                     size=[4,*np.shape(std)]), 
                                    0, 2)
    prediction = tab.getcol(column) 

    tab.putcol(column, prediction + noise)
    tab.close()

    return 0
