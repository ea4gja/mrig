#!/usr/bin/env python
#
# File: dummy.py
# Version: 1.0
#
# mrigd: Dummy class definition
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


import sys,time
from backend import *

# This is a dummy backend that does not communicate with any real rig.

# These definitions are used to inform client (rig.info) about rig's
# structure AND are then used to recognize client's commands to us.
# Modes should be a subset of a standard list of possible modes
# maintained for all rigs - to make client's life easier.

DUMMY_MODE_LIST             = [ 'USB', 'LSB', 'CW',  
                                'AM', 'FM', 'RTTY' ]
#  Orion would prefer 'UCW', 'LCW', and 'FSK', but we use Hamlib convention.
DUMMY_VFO_LIST              = ['VFOA']
DUMMY_RX_LIST               = ['MAIN']
DUMMY_TX_LIST               = ['TX']
DUMMY_BACKEND_ID            = 'Dummy Backend v. 0.1'
DUMMY_VFO_STEP_LIST         = [1, 10, 100, 1000, 5000, 10000, 100000]
# Bandpass std. settings, (center, width) float Hz
DUMMY_BANDPASS_SETTINGS     = { 'NARROW':'0. 400.', 'MEDIUM':'0. 2400.',
                                'WIDE':'0. 3000.' }
# AGC std. settings
DUMMY_AGC_MODES             = [ 'FAST', 'MEDIUM', 'SLOW', 'OFF' ]

DUMMY_RIT_RANGE_LIST        = [-10000., +10000.]    # float Hz
DUMMY_XIT_RANGE_LIST        = DUMMY_RIT_RANGE_LIST

#Simplified standard mapping for the VFO - RX
DUMMY_VFO_TO_RX             = { 'VFOA':'MAIN' }
# Supported frequency bands - valid VFO settings, float Hz
DUMMY_BAND_MAIN             = [ (1.e6,30.e6)]
DUMMY_BANDS                 = { 'MAIN':DUMMY_BAND_MAIN }

class Dummy(Backend):
    def __init__(self):
        Backend.__init__(self)

        # Override Backend settings (for info print)
        self.backend_id =   DUMMY_BACKEND_ID
        self.vfo_list=      DUMMY_VFO_LIST
        self.rx_list =      DUMMY_RX_LIST
        self.tx_list =      DUMMY_TX_LIST
        self.mode_list =    DUMMY_MODE_LIST
        self.bandpass_dict = DUMMY_BANDPASS_SETTINGS
        self.agc_mode_list = DUMMY_AGC_MODES
        self.bands =        DUMMY_BANDS

        # Variables to hold our copy of rig's state
        self.init_v     = ''            # string ("DUMMY START")
        self.rx_mode_v  = {'MAIN':'USB' }   # mode, string
        self.tx_mode_v  = {'TX':'USB' }     # mode, string
        self.freq_v     = {'VFOA':10. }     # Hz, float
        self.vfo_step_v = {'VFOA':'100.' }    # Hz, float
        self.bandpass_v = {'MAIN':[0.,3000.] } 	# entry is [ctr,width] (float)
        self.agc_mode_v = {'MAIN':'FAST' }  # mode, string
        self.rf_gain_v  = {'MAIN':1.0 }     # rf gain, float
        self.af_gain_v  = {'MAIN':0.3 }     # af gain, float
        self.rit_v      = {'MAIN':0.0 }           # rit offset, Hz, float
        self.xit_v      = {'MAIN':0.0 }           # xit offset, Hz, float
        self.mic_gain_v = {'TX':0.5   }           # mic gain, float
        self.transmit_v = { 'TX':0 }    # PTT setting, int/bool, needs init value
        self.power_v    = {'TX':100. }           # Power, Watts, Float
        self.strength_raw_v = {'MAIN':50 }       # raw strength, int.
        self.strength_v = {'MAIN':0. }           # calibrated strength, dB, float
        self.swr_raw_v  = {'TX':[80,5,200] }           # fwd,rev,ratio (raw), [int,int,int]
        self.swr_v      = {'TX':1.5 }           # swr, float
        return

    def info(self,tp,rx='',data=''):
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            return Backend.info(self,T_GET)
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return TP_INVALID        # no puts for this command

    def init(self,tp,rx='',data='/dev/ttyS0'):  # Firmware initalize
        # 'rx' is ignored!
        # 'Put' performs serial initialization
        if tp == T_PUT:
            self.init_v = 'Dummy initialized'     # remember me!
            return ACK
        elif tp == T_GET:
            return self.init_v
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return TP_INVALID

    def status(self,tp,rx=''): # Get rig status
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            return "Version 1.00"
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return TP_INVALID

    def rx_mode(self,tp,rx='',mode=''):
        if tp == T_PUT:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            if not mode in DUMMY_MODE_LIST:
                return NAK+'Unsupported mode %s' % mode
            self.rx_mode_v[rx] = mode
            return ACK
        elif tp == T_GET:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            return self.rx_mode_v[rx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def tx_mode(self,tp,tx='',mode=''):
    # Note: tx mode always = main rx mode (hardware)
    # side effect: rx='MAIN' mode changes
        if tp == T_PUT:
            if not tx in DUMMY_TX_LIST: return NAK+'invalid tx: %s' % tx
            self.tx_mode_v[tx] = mode
            return ACK
        elif tp == T_GET:
            if not tx in DUMMY_TX_LIST: return NAK+'invalid tx: %s' % tx
            return self.tx_mode_v[tx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def freq(self,tp,v='',data=''):
        if tp == T_PUT:
            f = float(data)
            # Check if f is in a valid range.
            if DUMMY_VFO_TO_RX[v] == 'MAIN':
                if not in_band(DUMMY_BAND_MAIN,f):
                    return NAK+'freq: bad freq. for main rx/tx: %f' % f
            self.freq_v[v] = f
            return ACK
        elif tp == T_GET:
            return '%.f' % self.freq_v[v]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def vfo_step(self,tp,v='',data=''):       # Set Tuning Step
        if tp == T_PUT:
            # validate fstep - has to be in the list
            if not int(fstep) in DUMMY_VFO_STEP_LIST:
                return NAK+'vfo_step: Invalid freq. step size %f' % fstep
            self.vfo_step_v[v] = data
            return ACK
        elif tp == T_GET:
            return '%.f' % self.vfo_step_v[v]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def bandpass_limits(self,tp,rx='',data=''):        # low_high: string
        if tp == T_PUT:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            l_h = data.split(None,2)                   # [low-Hz, high-Hz]
            offset = float( l_h[0] )
            width  = float( l_h[1] ) - float( l_h[0] )
            self.bandpass_v[rx] = [offset, width]   # remember as floats
            return ACK
        elif tp == T_GET:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            low = self.bandpass_v[rx][0]
            high = low + self.bandpass_v[rx][1]
            return '%.f %.f' % (low,high)           # return limits, char Hz
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def bandpass(self,tp,rx='',data=''):    # offset_width = string
        if tp == T_PUT:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            o_w = data.split(None,2)
            offset = float(o_w[0])
            width  = float(o_w[1])
            self.bandpass_v[rx] = [offset, width]   # remember as float Hz
            return ACK
        elif tp == T_GET:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            return '%.f %.f' % (self.bandpass_v[rx][0],self.bandpass_v[rx][1])
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def bandpass_standard(self,tp,rx='',data=''):
        # set according to standard bandpass table - NARROW/MEDIUM/WIDE etc.
        if tp == T_PUT:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            if not self.bandpass_dict.has_key(data):
                return NAK+'Invalid bandpass setting'
            ans = self.bandpass(T_PUT,rx,self.bandpass_dict[data])
            return ans                              # ACK/NAK etc
        elif tp == T_GET: return NO_READ
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def agc_mode(self,tp,rx='',data=''):
        # put or get current AGC mode (FAST/MEDIUM/SLOW/USER etc)
        if tp == T_PUT:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            self.agc_mode_v[rx] = data              # remember as string
            return ACK
        elif tp == T_GET:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            return self.agc_mode_v[rx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def rf_gain(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            self.rf_gain_v[rx] = float(data)
            return ACK
        elif tp == T_GET:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            return '%.3f' % self.rf_gain_v[rx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def af_gain(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            self.af_gain_v[rx] = float(data)
            return ACK
        elif tp == T_GET:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            return '%.3f' % self.af_gain_v[rx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def rit(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            self.rit_v[rx] = float(data)
            return ACK
        elif tp == T_GET:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            return '%.f' % self.rit_v[rx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def xit(self,tp,tx='',data=''):
        if tp == T_PUT:
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            self.xit_v[tx] = float(data)
            return ACK
        elif tp == T_GET:
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            return '%.f' % self.xit_v[tx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def mic_gain(self,tp,tx='',data=''):
        if tp == T_PUT:
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            self.mic_gain_v[tx] = float(data)
            return ACK
        elif tp == T_GET:
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            return '%.3f' % self.mic_gain_v[tx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID


    def transmit(self,tp,tx='',data=''):       # =="0" -> off, otherwise -> on
        if tp == T_PUT:
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            self.transmit_v[tx] = int(data)
            return ACK
        if tp == T_GET:                 # Orion has no query for ptt
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            return self.transmit_v[tx]  # Use self-stored value
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def power(self,tp,tx='',data=''):  # Power in watts, max 100.
        if tp == T_PUT:
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            self.power_v[tx] = float(data)
            return ACK
        elif tp == T_GET:
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            return '%.f' % self.power_v[tx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def strength_raw(self,tp,rx='',data=''):      # Get uncalibrated int value
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            return self.strength_raw_v[rx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def strength(self,tp,rx='',data=''):
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            if not rx in DUMMY_RX_LIST: return NAK+'rx invalid: %s' % rx
            return '%.1f' % self.strength_v[rx]     # return float dB in string
        elif tp == T_TEST: return ACK
        else: return TP_INVALID
        
    def swr_raw(self,tp,tx='',data=''):    # Get rig-dependent string,
                                        # e.g., 'fwd rev ratio'
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            return '%i %i %i' % (self.swr_raw_v[tx][0],
                                self.swr_raw_v[tx][1],
                                self.swr_raw_v[tx][2])
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def swr(self,tp,tx='',data=''):         # get the actual SWR ratio (float)
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            if not tx in DUMMY_TX_LIST: return NAK+'tx invalid: %s' % tx
            return '%.2f' % self.swr_v[tx]
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

if __name__ == '__main__':
# This is the place to test the subclass and ic module routines.
# THIS CODE IS NOT EXECUTED IF THIS FILE IS INVOKED FROM ANOTHER PYTHON ROUTINE.

    rig = Dummy()
    print rig.init(T_PUT,data='/dev/ham.orion')
    print rig.init(T_GET)
    print rig.status(T_GET)
    print rig.atten(T_PUT,'SUB','OFF')
    print rig.atten(T_GET,'SUB')
    print rig.agc_user(T_GET,'MAIN')
    print rig.bandpass(T_GET,'MAIN')
    print rig.bandpass_limits(T_GET,'MAIN')
    print rig.bandpass_standard(T_PUT,'MAIN','MEDIUM')
    print rig.bandpass(T_GET,'MAIN')
    print rig.info(T_GET)
    print rig.strength_raw(T_GET,'MAIN')
    print rig.strength(T_GET,'MAIN')
    print rig.freq(T_GET,'VFOA')
    print rig.freq(T_PUT,'VFOA', '7100001')
    print rig.freq(T_GET,'VFOA')
    print rig.preamp(T_GET,'MAIN')
    print rig.atten(T_GET,'MAIN')
