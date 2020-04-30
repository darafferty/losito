#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from ..lib_io import logger


def _run_parser(obs, parser, step):
    outputColumn = parser.getstr( step, 'outputColumn', 'DATA')
    parser.checkSpelling( step, ['outputColumn'])
    return run(obs, outputColumn)


def run(obs, outputColumn='DATA'):
    # Ensure that the LOFAR_APPLIED_BEAM_MODE keyword is unset (otherwise DPPP may
    # complain that the beam has already been applied)
    obs.reset_beam_keyword(outputColumn)
    s = obs.scheduler
    # Run DPPP
    for ms in obs:
        cmd = 'DPPP DPPP_elementbeam.parset msin={}'.format(ms.ms_filename)
        # TODO if ms filename contains dirname split
        pth_splt = os.path.split(ms.ms_filename)
        s.add(cmd, commandType='DPPP', log='element_'+pth_splt[1], processors='max')
    s.run(check=True)

    # Ensure again that the LOFAR_APPLIED_BEAM_MODE keyword is unset
    obs.reset_beam_keyword(outputColumn)

    # Return result
    return 0
