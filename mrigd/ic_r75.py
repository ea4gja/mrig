#!/usr/bin/env python
#
# File: IC_r75.py
# Version: 1.0
#
# mrigd: IC_r75 class definition
# Copyright (c) 2006-2008 Martin Ewing
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  
# 02110-1301, USA.
#
# Contact ewing @@ alum.mit.edu or c/o San Pasqual Consulting, 28
# Wood Road, Branford CT 06405, USA.

# This is the subclass of Backend to handle the IC_R75 receiver
#
# NOTES:

# TO DO:
# - Verify operations against hardware
# - Check "strength" calibration against R75 S meter


import sys, serial, time
from icom import *

R75_VFO_LIST          = ['VFOA']
R75_RX_LIST           = ['MAIN','CONTROL']
R75_ATTEN_DICT        = { 'OFF':0x00, '20dB':0x20 }
R75_TX_LIST           = []    # We are not a Tx, but keep placeholders.
R75_BACKEND_ID        = "Icom R75 Backend v. 0.01"
# Use integer STEPs, not floating
R75_VFO_STEP_MAP      = {10:0x00, 50:0x01, 100:0x02, 1000:0x03, 2500:0x04, 
                            5000:0x05, 9000:0x06, 10000:0x07, 12500:0x08, 
                            20000:0x09, 25000:0x0A, 100000:0x0B}
R75_MIC_SOURCES       = []  # Mic (tx audio) source
R75_TX_ANTENNAS       = []  # Tx Antennas
R75_RX_ANTENNAS_DICT  = { 'ANT1':(0,), 'ANT2':(1,) }    # Note tuple here, because some
#                                                       rigs will need 2 byte commands
#R75_MEMORY_CHANNELS   = [ 1, 200 ]
R75_ADDRESS           = 0x5A    # standard address for the R75

# Supported frequency bands - valid VFO settings, Hz
#USA:
R75_BANDS               = { 'VFOA':[ (0.03e6,60.000e6) ] }
#EUROPE:
#R75_BANDS              = { 'VFOA':[ (0.1e6,1999.99999e6) ] }
#FRANCE:
#R75_BANDS              = { 'VFOA':[ (0.1e6,87.5e6), 
#                                       (108e6, 1999.99999e6) ] }

# Reverse mode map (note change to hex)
R75_MODE_MAPr       = { 0x001:'LSB', 0x002:'LSBW', 0x011:'USB', 0x012:'USBW', 
                        0x022:'AM', 0x023:'AMN', 0x021:'AMW', 
                        0x030: 'CWW', 0x031:'CW', 0x032:'CWN', 
                        0x040:'RTTYW', 0x041:'RTTY', 
                        0x051:'FM', 0x052:'FMN', 0x061:'WFM',
                        0x070:'CW-RW', 0x071:'CW-R', 
                        0x080:'RTTY-RW', 0x081:'RTTY-R',
                        0x110:'S-AMW', 0x111:'S-AM', 0x112:'S-AMN' }
# Calculate the forward-going mode map from the reverse.
R75_MODE_MAP      = {}
for x in R75_MODE_MAPr:
    R75_MODE_MAP[R75_MODE_MAPr[x]] = x

R75_AGC_MODE_LIST = [ 'FAST', 'SLOW' ]

R75_CAPABILITIES = udict(IC_COMMON_CAPABILITIES,
    { 'status':'r', 'agc_mode':'rw', 'strength_raw':'r', 'atten':'rw',
      'af_gain':'rw', 'operate':'w', 'squelch_level':'rw', 'squelch_open':'r',
      'bandpass':'rw', 'vfo_step':'rw'} )
# Capabilities copied from R8500; should be checked.

GETPUT = ['GET', 'PUT']

class IC_r75(Icom):
    def __init__(self):
        Icom.__init__(self)
        self.vfo_step = 0
        self.agc_mode_v = ''
        self.af_gain_v = 0
        self.atten_v = ''
        self.squelch_level_v = 0
        self.center_width = [ 0., 0.]
        self.backend_id =   R75_BACKEND_ID
        self.vfo_list=      R75_VFO_LIST
        self.bands =        R75_BANDS
        self.rx_list =      R75_RX_LIST
        self.atten_dict =   R75_ATTEN_DICT
        self.tx_list =      R75_TX_LIST
        self.mode_list =    R75_MODE_MAP.keys()
#        self.bandpass_dict = R75_BANDPASS_SETTINGS
        self.agc_mode_list = R75_AGC_MODE_LIST
        self.mic_source_list = R75_MIC_SOURCES
        self.tx_ant_list =  R75_TX_ANTENNAS
        self.rx_ant_list =  R75_RX_ANTENNAS_DICT.keys()
        self.rx_ant_dict =  R75_RX_ANTENNAS_DICT
        self.capabilities = R75_CAPABILITIES
        return

    def info(self,tp,rx='',data=''): 
        if tp == T_GET:
            return Backend.info(self,T_GET,'','')
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

# This is the strength function for the R8500.  It needs to be checked for
# the R75.
    def strength(self,tp,rx,data=''):   # return dB relative to S9
        if tp == T_GET:
            thiscmd = ICOM_CMD['RD_STRENGTH']
            f,err = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            if err[0] == NAK1: return err
            m = int(255.*f)
            if m < 17:                      # rough calibration @ 14 MHz
                db = -51. + 4.*float(m)/17.0
            elif m < 177:                   # (piecewise linear)
                db = -47. + 67.*float(m-17)/160.
            else:
                db = 20. + 40.*float(m-177)/64.
            return '%.1f' % db
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF                      # no put

    def operate(self,tp,s,data=''):     # on/off only for R75 R8500
        if tp == T_PUT:
            onoff = int(data)
            if onoff: thiscmd = ICOM_CMD['PWR_ON']
            else: thiscmd = ICOM_CMD['PWR_OFF']
            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            if err[0] == NAK1: return err
            return ACK
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

if __name__ == "__main__":
# This is the place to test the subclass and ic module routines.
# Not executed if this file is invoked by another Python routine.

    rig = IC_r75()
    print                   rig.init(T_PUT, data='/dev/ham.75')
    print                   rig.status(T_GET)
    print                   rig.info(T_GET)
    print                   rig.freq(T_GET,'VFOA')

