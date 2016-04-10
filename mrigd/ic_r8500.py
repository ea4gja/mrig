#!/usr/bin/env python
#
# File: ic_r8500.py
# Version: 1.0
#
# mrigd: IC_r8500 class definition
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

# This is the subclass of Backend to handle the IC_R8500 receiver
#
# Notes:
# Except for vfo frequency and mode, the R8500 does not provide
# read-back of parameters that we set. 
#
# To do:
#   memory operations, scanning?


import sys, serial, time
from icom import *

R8500_VFO_LIST          = ['VFOA']
R8500_RX_LIST           = ['MAIN','CONTROL']
R8500_ATTEN_DICT        = { 'OFF':0x00, '10dB':0x10, '20dB':0x20, '30dB':0x30 }
R8500_BACKEND_ID        = "Icom R8500 Backend v. 0.11 (USA)"
# Use integer STEPs, not floating
R8500_VFO_STEP_MAP      = {10:0x00, 50:0x01, 100:0x02, 1000:0x03, 2500:0x04, 
                            5000:0x05, 9000:0x06, 10000:0x07, 12500:0x08, 
                            20000:0x09, 25000:0x0A, 100000:0x0B, 1000000:0x0C }
R8500_MIC_SOURCES       = []  # Mic (tx audio) source
R8500_RX_ANTENNAS       = [ 'ANT1' ]  # Rx Antennas
#R8500_MEMORY_CHANNELS   = [ 1, 200 ]
R8500_ADDRESS           = 0x4A    # standard address for the R8500

# Supported frequency bands - valid VFO settings, Hz
#USA:
R8500_BANDS               = { 'VFOA':[ (0.1e6,823.999e6),
                                        (849.00001e6,868.99999e6),
                                        (894.00001e6,1999.99999e6) ] }
#EUROPE:
#R8500_BANDS              = { 'VFOA':[ (0.1e6,1999.99999e6) ] }
#FRANCE:
#R8500_BANDS              = { 'VFOA':[ (0.1e6,87.5e6), 
#                                       (108e6, 1999.99999e6) ] }

# Reverse mode map (note change to hex)
R8500_MODE_MAPr     = { 0x001:'LSB', 0x011:'USB', 0x022:'AM', 0x023:'AMN', 
                        0x021:'AMW', 0x031:'CW', 0x032:'CWN', 0x051:'FM',
                        0x052:'FMN', 0x061:'WFM' }
# Calculate the forward-going mode map from the reverse.
R8500_MODE_MAP      = {}
for x in R8500_MODE_MAPr:
    R8500_MODE_MAP[R8500_MODE_MAPr[x]] = x
    
R8500_AGC_MODE_LIST = [ 'FAST', 'SLOW' ]

R8500_CAPABILITIES = udict(IC_COMMON_CAPABILITIES,
    { 'status':'r', 'agc_mode':'rw', 'strength_raw':'r', 'atten':'rw',
      'af_gain':'w', 'operate':'w', 'squelch_level':'rw', 'squelch_open':'r',
      'bandpass':'rw', 'vfo_step':'rw'} )

GETPUT = ['GET', 'PUT']

class IC_r8500(Icom):
    def __init__(self):
        Icom.__init__(self)
        self.backend_id =   R8500_BACKEND_ID
        self.vfo_list=      R8500_VFO_LIST
        self.vfo_step_list= R8500_VFO_STEP_MAP.keys()
        self.vfo_step_map=  R8500_VFO_STEP_MAP
        self.bands =        R8500_BANDS
        self.rx_list =      R8500_RX_LIST
        self.atten_dict =   R8500_ATTEN_DICT
        self.mode_list =    R8500_MODE_MAP.keys()
#        self.bandpass_dict = R8500_BANDPASS_SETTINGS
        self.agc_mode_list = R8500_AGC_MODE_LIST
# We do not use agc_mode_map for the R8500
        self.mic_source_list = R8500_MIC_SOURCES
        self.rx_ant_list =  R8500_RX_ANTENNAS
        self.civ_address =  CIVAD['R8500']
        self.r8500_kluge =  True        # Tells Icom to do special R8500 level tricks
        self.mode_map =     R8500_MODE_MAP
        self.mode_map_r =   R8500_MODE_MAPr
        self.capabilities = R8500_CAPABILITIES
        return

    def agc_mode(self,tp,rx,mode=''):   # Override Icom method: R8500 is special
        if tp == T_PUT:
            m = mode.strip()
            if m not in R8500_AGC_MODE_LIST:
                return NAK+'Unrecognized AGC set for R8500, m= %s' % m
#            if m == 'SLOW':
#                thiscmd = ICOM_CMD['SET_AGC_SLOW']
#                icmd = 'SET_AGC_SLOW'
#            elif m == 'FAST':
#                thiscmd = ICOM_CMD['SET_AGC_FAST']
#                icmd = 'SET_AGC_FAST'
#            else:
#            
            self.agc_mode_v = m
#            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            err = self.ic_put('agc_mode', 'SET_AGC_'+m, NULL_TUP)
            if is_nak(err): return err
            return ACK
        elif tp == T_GET:
            return self.agc_mode_v
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

# IF shift level is unique to the R8500
    def bandpass(self,tp,rx,c_w=''): # Adjust bp center via IF shift
        if tp == T_GET:
            return '%.f %.f' % self.center_width, ACK
        elif tp == T_PUT:
            self.center_width = map(float,c_w.split(None,2))
            shift = self.center_width[0]             # ignore "width"
            shift = min(1200.,max(-1200.,shift))    # +/- 1.2 kHz max.
            self.center_width[0] = shift
            shift0 = (shift+1200.)/2400.    # transform to 0.0 - 1.0, zero 0.5
#            thiscmd = ICOM_CMD['SET_IF_SHIFT']
#            err=thiscmd[FN](self.ser,self.civ_address, thiscmd[BN], shift0)
            err = self.ic_put('bandpass', 'SET_IF_SHIFT', shift0)
            if is_nak(err): return err
            return ACK
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

    def strength(self,tp,rx,data=''):   # return dB relative to S9 (very rough!)
        if tp == T_GET:
#            thiscmd = ICOM_CMD['RD_STRENGTH']
#            f,err = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            resp = self.ic_get('strength_raw','RD_STRENGTH') # resp=(f,err)
            if is_nak(resp): return resp
            m = int(resp*255.)                 # NB, measured 50 uV -> "S8"
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
            on_off = min(1,max(0,int(data)))
            icmd = {0:'PWR_OFF', 1:'PWR_ON'}[on_off]
#            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            err = self.ic_put('operate', icmd, NULL_TUP)
            if is_nak(err): return err
            return ACK
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

if __name__ == "__main__":

# This is the place to test the subclass and ic module routines.
# Not executed if this file is invoked by another Python routine.

    rig = IC_r8500()
    print                   rig.init(T_PUT, data='/dev/ham.8500')
    print                   rig.status(T_GET)
    print                   rig.info(T_GET)
    print                   rig.freq(T_GET,'VFOA')
    print                   rig.bandpass(T_PUT,'MAIN','0 2000')
    print                   rig.rx_mode(T_PUT,'MAIN','WFM')
    print                   rig.freq(T_PUT,'VFOA','91.5e6')
    print "vfo_step set",   rig.vfo_step(T_PUT,'VFOA','100')
    print "vfo_step=",      rig.vfo_step(T_GET,'VFOA')
    print                   rig.agc_mode(T_PUT,'MAIN','SLOW')
    print                   rig.agc_mode(T_GET,'MAIN')
    print                   rig.af_gain(T_PUT,'MAIN', 0.3)
    print                   rig.strength_raw(T_GET,'MAIN')
    print                   rig.strength(T_GET,'MAIN')
#    sys.exit()
#    time.sleep(1)
#    print                   rig.operate(T_PUT,'MAIN','0')
#    time.sleep(2)
#    print                   rig.operate(T_PUT,'MAIN','1')
    print                   rig.atten(T_PUT, data='OFF')
    print "atten=",         rig.atten(T_GET)
    time.sleep(1)
    print                   rig.atten(T_PUT,'MAIN','10dB')
    time.sleep(1)
    print                   rig.atten(T_PUT,'MAIN','20dB')
    time.sleep(1)
    print                   rig.atten(T_PUT,'MAIN','OFF')
    print "sq level set",   rig.squelch_level(T_PUT,'MAIN','0.00')
    print "squelch=",       rig.squelch_open(T_GET,'MAIN')
    print "ifshift set",        rig.bandpass(T_PUT,'MAIN','500. 1000.')

