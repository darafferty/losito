#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bandpass-operation: Get bandpass amplitudes as solution-table
in h5parm file.
"""
import os
import numpy as np
import casacore.tables as pt
from losoto.h5parm import h5parm
from ..lib_io import logger

logger.debug('Loading Bandpass module.')


def _run_parser(obs, parser, step):
    h5parmFilename = parser.getstr(step, 'h5parmFilename', default = '')
    column = parser.getstr(step, 'outputColumn', default = '')
    method = parser.getstr(step, 'method', default = 'h5parm')

    parser.checkSpelling(step, ['h5parmFilename', 'outputColumn', 'method'])
    return run(obs, h5parmFilename, column, method, step)


def bandpass(f):
    """
    Return the bandpass amplitude for an array of frequencies.
    f : (n,) ndarray
    """
    # Only HBA-low bandpass is included
    is_lba = np.any((f > 10e6) & (f < 90e6))
    is_hba = np.any((f > 120e6) & (f < 170e6))
    assert np.any(is_lba) != np.any(is_hba), ('You have to use either LBA ' +
                                              'or HBA-low frequencies')
    mod_dir = os.path.dirname(os.path.abspath(__file__))

    if is_lba:
        bp = np.loadtxt(mod_dir + '/../../data/bandpass_lba.txt').T
    else:
        bp = np.loadtxt(mod_dir + '/../../data/bandpass_hba_low.txt').T
    amplitude = np.interp(f, *bp, left=0, right=0)
    return amplitude


def run(obs, h5parmFilename='', column='',method='h5parm', stepname='bandpass'):
    '''
    Add bandpass amplitudelitudes to h5parm.
    '''
    freq = obs.get_frequencies()
    ras, decs = obs.get_patch_coords()
    source_names = obs.get_patch_names()

    # Get the bandpass amplitude for each channel
    bp_amplitude = bandpass(freq)
    assert (len(h5parmFilename) > 0) != (len(column) > 0), """You have to 
                                                           specify either a 
                                                           h5parm or a MS 
                                                           column."""
    if method == 'h5parm':
        # Write bandpass amplitude to h5parm file as DPPP input
        ho = h5parm(h5parmFilename, readonly=False)
        if 'sol000' in ho.getSolsetNames():
            solset = ho.getSolset('sol000')
        else:
            solset = ho.makeSolset(solsetName='sol000')

        if 'amplitude000' in solset.getSoltabNames():
            logger.info('''Solution-table amplitude000 is already present in
                     {}. It will be overwritten.'''.format(h5parmFilename + '/sol000'))
            solset.getSoltab('amplitude000').delete()

        # h5parmpredict needs direction axis with directions from sky model.
        bp_amplitude = np.repeat(bp_amplitude[:, np.newaxis], len(source_names),
                                 -1)
        bp_amplitude = np.sqrt(bp_amplitude) # Jones-Matrix from Bandpass amp
        weights = np.ones_like(bp_amplitude)
        solset.makeSoltab('amplitude', 'amplitude000', axesNames=['freq', 'dir'],
                           axesVals=[freq, source_names], vals=bp_amplitude,
                           weights=weights)

        sourceTable = solset.obj._f_get_child('source')
        vals = [[ra, dec] for ra, dec in zip(ras, decs)]
        sourceTable.append(list(zip(*(source_names, vals))))

        soltabs = solset.getSoltabs()
        for st in soltabs:
            st.addHistory('CREATE (by bandpass operation of LoSiTo from obs {0})'.format(h5parmFilename))
        ho.close()

        # Update predict parset parameters for the obs
        obs.parset_parameters['predict.applycal.parmdb'] = h5parmFilename
        if 'predict.applycal.steps' in obs.parset_parameters:
            obs.parset_parameters['predict.applycal.steps'].append(stepname)
        else:
            obs.parset_parameters['predict.applycal.steps'] = [stepname]
        obs.parset_parameters['predict.applycal.correction'] = 'amplitude000'
        obs.parset_parameters['predict.applycal.{}.correction'.format(stepname)] = 'amplitude000'
        obs.parset_parameters['predict.applycal.{}.parmdb'.format(stepname)] = h5parmFilename

        return 0

    elif method == 'ms':
        logger.info('Applying bandpass to column ' + column+'.')
        tab = pt.table(obs.ms_filename, readonly=False)
        vis = tab.getcol(column)
        vis = vis * bp_amplitude[:, np.newaxis]
        tab.putcol(column, vis)
        tab.close()
        return 0

    else:
        logger.warning('You either have to specify h5parm or ms as method.')
        return 1
