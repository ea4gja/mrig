#!/usr/bin/env python
#
# File: tt_orion.py
# Version: 1.0
#
# mrigd: TT_orion class definition
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
from tentec import *

# To do:
#  Squelch settings
#  Antenna settings
#  Mic source
#  Manual notch (when TT supports it)
#  As always, more work is needed to overcome Orion timeout problems.

# These definitions are used to inform client (rig.info) about rig's
# structure AND are then used to recognize client's commands to us.
# Modes should be a subset of a standard list of possible modes
# maintained for all rigs - to make client's life easier.

FREQIO_BINARY = True    # Use faster(?) binary I/O, not alpha for VFO freq.

ORION_MODE_LIST             = [ 'USB', 'LSB', 'CW', 'CWR', 
                                'AM', 'FM', 'RTTY' ]
#  Orion would prefer 'UCW', 'LCW', and 'FSK', but we use Hamlib convention.
ORION_VFO_LIST              = ['VFOA', 'VFOB']
ORION_RX_LIST               = ['MAIN', 'SUB' ]
ORION_ATTEN_DICT            = { 'OFF':0, '6dB':1, '12dB':2, '18dB':3 }
ORION_TX_LIST               = ['TX']
ORION_BACKEND_ID            = 'Orion Backend v. 0.23'
ORION_VFO_STEP_LIST         = [1, 10, 100, 1000, 5000, 10000, 100000]
# Bandpass std. settings, (center, width) float Hz
ORION_BANDPASS_SETTINGS     = { 'NARROW':'0. 400.', 'MEDIUM':'0. 2400.',
                                'WIDE':'0. 3000.' }
# AGC std. settings
ORION_AGC_MODES             = [ 'FAST', 'MEDIUM', 'SLOW', 'OFF', 'PROG' ]
# Mic (tx audio) source
ORION_MIC_SOURCES           = [ 'NORMAL', 'ALTERNATE' ]
# Tx Antennas
ORION_TX_ANTENNAS           = [ 'ANT1', 'ANT2' ]
# Rx Antennas
ORION_RX_ANTENNAS           = [ 'ANT1', 'ANT2', 'ANT3' ]

ORION_MEMORY_CHANNELS       = [ 1, 200 ]
ORION_DSP_DELAY             = 0.2   # secs to wait after bandpass op.
ORION_RIT_RANGE_LIST        = [-10000., +10000.]    # float Hz
ORION_XIT_RANGE_LIST        = ORION_RIT_RANGE_LIST

# Mappings to Orion's ASCII command parameters
ORION_VFO_MAP               = { 'VFOA':'A', 'VFOB':'B' }
ORION_VFO_ASSIGN            = { 'VFOA':'M', 'VFOB':'S' }
ORION_RX_MAP                = { 'MAIN':'M', 'SUB':'S' }
ORION_TX_MAP                = { 'TX':'M' }    # TX is same as MAIN Rx
ORION_ANT_ASSIGN            = { 'M':'ANT1', 'S':'ANT1' } # or the other way round?
ORION_MODE_MAP              = { 'USB':'0', 'LSB':'1', 'CW':'2', 'CWR':'3',
                                'AM':'4', 'FM':'5', 'RTTY':'6' }
ORION_AGC_MODE_MAP          = { 'FAST':'F', 'MEDIUM':'M', 'SLOW':'S',
                                'OFF':'O', 'PROG':'P' }

#Simplified standard mapping for the VFO - RX
ORION_VFO_TO_RX             = { 'VFOA':'MAIN', 'VFOB':'SUB' }
# Supported frequency bands - valid VFO settings, float Hz
ORION_BAND_MAIN                   = [ (1.79e6,2.09e6), (3.49e6,4.075e6),
                                (6.89e6,7.43e6), (5.1e6,5.425e6),
                                (10.09e6,10.16e6), (13.99e6,15.01e6),
                                (18.058e6,18.178e6), (20.99e6,21.46e6),
                                (24.88e6,25.0e6), (27.99e6,29.71e6) ]
ORION_BAND_SUB                    = [ (0.101e6,29.999999e6) ]
ORION_BANDS                 = { 'MAIN':ORION_BAND_MAIN, 'SUB':ORION_BAND_SUB }

class TT_orion(Tentec):
    def __init__(self):
        Tentec.__init__(self)

        # Override Backend settings (for info print)
        self.memory_range = ORION_MEMORY_CHANNELS
        self.backend_id =   ORION_BACKEND_ID
        self.vfo_list=      ORION_VFO_LIST
        self.rx_list =      ORION_RX_LIST
        self.atten_dict=    ORION_ATTEN_DICT
        self.tx_list =      ORION_TX_LIST
        self.mode_list =    ORION_MODE_LIST
        self.bandpass_dict = ORION_BANDPASS_SETTINGS
        self.agc_mode_list = ORION_AGC_MODES
        self.mic_source_list = ORION_MIC_SOURCES
        self.tx_ant_list =  ORION_TX_ANTENNAS
        self.rx_ant_list =  ORION_RX_ANTENNAS
        self.bands =        ORION_BANDS

        # Variables to hold our copy of rig's state
        self.init_v     = ''            # string ("ORION START")
        self.rx_mode_v  = { }           # mode, string
        self.tx_mode_v  = { }           # mode, string
        self.freq_v     = { }           # Hz, float
        self.vfo_step_v = { }           # Hz, float
        self.bandpass_v = { }           # entry is [ctr,width] (float)
        self.agc_mode_v = { }           # mode, string
        self.agc_user_v = { }           # user/prog agc settings, [x,y,z], float
        self.rf_gain_v  = { }           # rf gain, float
        self.af_gain_v  = { }           # af gain, float
        self.rit_v      = { }           # rit offset, Hz, float
        self.xit_v      = { }           # xit offset, Hz, float
        self.mic_gain_v = { }           # mic gain, float
        self.speech_proc_v = { }        # SP gain, float
        self.noise_blank_v = { }        # NB gain, float
        self.noise_reduce_v= { }        # NR gain, float
        self.notch_auto_v  = { }        # AN gain, float
        self.transmit_v = { 'TX':0 }    # PTT setting, int/bool, needs init value
        self.power_v    = { }           # Power, Watts, Float
        self.strength_raw_v = { }       # raw strength, int.
        self.strength_v = { }           # calibrated strength, dB, float
        self.swr_raw_v  = { }           # fwd,rev,ratio (raw), [int,int,int]
        self.swr_v      = { }           # swr, float
        self.atten_v    = { }           # attenuator setting, string
        self.preamp_v   = { }           # on/off, bool (int)
        self.memory_channel_v = 1       # current channel, int
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
            Tentec.serial_init(self,data)
            r = self.transact('init: error','XX')   # This is an Orion mystery
            if is_nak(r): return r                  # (does it do anything?)
            # Set up default VFO / Rx/Tx config (A<->MAIN, B<->SUB ?)
            self.transact('vfo init','*KVABA')  # main=vfoa, sub=vfob, tx=vfoa
            # Set up default Antennas (MAIN/SUB <-> ANT1 ?)
            self.transact('rx init','*KABNN')   # main=sub=ant1, ''=ant2, ''=rx_ant
            # Set up default spkr/phones configuration
            self.transact('spkr setup','*UCBBB') # spkr=right=left="both main & sub"
            self.init_v = r             # remember me!
            return ACK
        elif tp == T_GET:
            # 'Get' returns value obtained in init(T_PUT) e.g. "ORION START"
            return self.init_v
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return TP_INVALID

    def status(self,tp,rx=''): # Get rig status
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            if not self.ser: return NAK+'Serial port not open.'
            r = self.transact('?V: rig disconnected?', '?V')
            if is_nak(r): return r
            self.init_v += r        # add to stored init message
            return r.strip()        # "Version 1.372" or similar
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return TP_INVALID

    def rx_mode(self,tp,rx='',mode=''):
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            if not mode in ORION_MODE_LIST:
                return NAK+'Unsupported mode %s' % mode
            self.rx_mode_v[rx] = mode
            cmd = '*R%cM%c' % ( ORION_RX_MAP[rx], ORION_MODE_MAP[mode] )
            self.transact('put rx mode', cmd)
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            cmd = '?R%cM' % ORION_RX_MAP[rx]    # the query
            r = self.transact('get rx mode', cmd)
            if is_nak(r): return r
            if len(r) < 5: return NAK+'Bad response from Orion'
            mval = r[4]                 # return = '@RMM0' e.g.
            mymode = ''
            for x in ORION_MODE_MAP.iterkeys(): # reverse lookup
                if ORION_MODE_MAP[x] == mval:
                    mymode = x
                    break
            self.rx_mode_v[rx] = mymode
            return mymode
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def tx_mode(self,tp,tx='',mode=''):
    # Note: tx mode always = main rx mode (hardware)
    # side effect: rx='MAIN' mode changes
        if tp == T_PUT:
            if not tx in ORION_TX_LIST: return NAK+'invalid tx: %s' % tx
            self.tx_mode_v[tx] = mode
            self.rx_mode(T_PUT,'MAIN',mode)       # tx = main rx
            return ACK
        elif tp == T_GET:
            if not tx in ORION_TX_LIST: return NAK+'invalid tx: %s' % tx
            mymode = self.rx_mode(T_GET,'MAIN')
            self.tx_mode_v[tx] = mymode
            return mymode
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def freq(self,tp,v='',data=''):       # using Orion's binary mode freqs
        if tp == T_PUT:
            try:
                f = float(data)         # Validity check
            except ValueError:
                return NAK+'freq: invalid vfo setting request: %s' % data
            # Check if f is in a valid range.
            # Rules for MAIN <> rules for SUB.
            if not ORION_VFO_MAP.has_key(v): return NAK+'invalid vfo: %s' % v
            if ORION_VFO_TO_RX[v] == 'MAIN':
                if not in_band(ORION_BAND_MAIN,f):
                    return NAK+'freq: bad freq. for main rx/tx: %f' % f
            else:
                if not in_band(ORION_BAND_SUB,f):
                    return NAK+'freq: bad freq. for sub rx: %f' % f
            self.freq_v[v] = f
            fi = int(f)
            if FREQIO_BINARY:       # Construct binary command
                cmd = '*%c' % ORION_VFO_MAP[v] + \
                chr(fi>>24 & 0xff) + chr(fi>>16 & 0xff) + \
                chr(fi>> 8 & 0xff) + chr(fi     & 0xff)
            else:                   # Construct alphanumeric command
                cmd = '*%cF' % ORION_VFO_MAP[v] + str(fi)
            self.transact('put freq',cmd)
            return ACK
        elif tp == T_GET:
            # Orion's vfo is set modulo tuning step, so 7000010 -> 7000000,
            # if tuning step > 10 Hz.  Also, the actual value set may be
            # rounded to an even Hz above 10 MHz...
            if not ORION_VFO_MAP.has_key(v): return NAK+'invalid vfo: %s' % v
            if FREQIO_BINARY:  
                cmd = '?%c' % ORION_VFO_MAP[v]
            else:
                cmd = '?%cF' % ORION_VFO_MAP[v]
            r = self.transact('get_freq',cmd)
            if is_nak(r): return r
            if FREQIO_BINARY:           # Get freq in binary style
                tup4 = tuple(map(ord,r[2:]))
                freq = float(reduce(lambda x,y: 256*x + y,tup4))    # Go, Python!
            else:                       # Do it the alpha way
                try:
                    freq = float(r[3:])     # Being a little paranoid here
                    self.freq_v[v] = freq
                except ValueError:          # stop gap measure if invalid freq rcvd
                    return NAK+'freq: bad response: %s' % r
            return '%.f' % freq
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def vfo_step(self,tp,v='',data=''):       # Set Tuning Step
        if tp == T_PUT:
            try:
                fstep = float(data)
            except:
                return NAK+'vfo_step bad request %s' %data
            # validate fstep - has to be in the list
            if not int(fstep) in ORION_VFO_STEP_LIST:
                return NAK+'vfo_step: Invalid freq. step size %f' % fstep
            self.vfo_step_v[v] = data
            # Problem:  Orion provides a "receiver step", not a "vfo step"
            # So you need to decode the vfo assignments to do the "vfo step"
            # correctly.  WE ASSUME VFOA <-> MAIN and VFOB <-> SUB.
            rx = ORION_VFO_TO_RX[v]
            cmd = '*R%cI%s' % (ORION_RX_MAP[rx], int(fstep))
            self.transact('put vfo step',cmd)
            return ACK
        elif tp == T_GET:
            rx = ORION_VFO_TO_RX[v]
            cmd = '?R%cI' % ORION_RX_MAP[rx]
            r = self.transact('get_vfo_step',cmd)
            if is_nak(r): return r
            try:
                fstep = float(r[4:])
            except:
                return NAK+'vfo_step bad response %s' % r
            self.vfo_step_v[v] = r[4:]
            return '%.f' % fstep
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

#
# Orion's passband is determined by the receiver "filter" (100 - 6000 Hz, "F")
# and its "passband" (-2500 -> 0 -> +2500 Hz, "P").  These control operation of
# the DSP.
# Rigserve allows setting the passband either as "offset" and
# "width" or as "low" and "high" - the lower and upper edges of the 
# passband (Hz).  
# Note that Orion works with "offset" (PBT) and "width" OR with High / Low
# Cut (on front panel), but the ASCII commands are for PBT and Filter = BW.

    def bandpass_limits(self,tp,rx='',data=''):        # low_high: string
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            try:
                l_h = data.split(None,2)                   # [low-Hz, high-Hz]
                offset = float( l_h[0] )
                width  = float( l_h[1] ) - float( l_h[0] ) # hi - low
            except:
                return NAK+'bandpass_limits bad request %s' % data
            cmd = '*R%cF%d' % (ORION_RX_MAP[rx], int(width) )
            self.transact('put filter bw',cmd)              # Send filter BW
            time.sleep(ORION_DSP_DELAY)
            cmd = '*R%cP%d' % (ORION_RX_MAP[rx], int(offset) )
            self.transact('put pbt',cmd)                    # Send PBT offset
            self.bandpass_v[rx] = [offset, width]   # remember as floats
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            cmd = '?R%cF' % ORION_RX_MAP[rx]
            r = self.transact('get_bandpass_limits 1',cmd)    # Get filter BW
            if is_nak(r): return r
            try:
                width = float(r[4:])
            except:
                return NAK+'bandpass_limits bad response 1 %s' % r
            cmd = '?R%cP' % ORION_RX_MAP[rx]
            r = self.transact('get_bandpass_limits 2',cmd)    # Get PBT offset
            if is_nak(r): return r
            try:
                offset = float(r[4:])
            except:
                return NAK+'bandpass_limits band response 2 %s' % r
            o_w = '%.f %.f' % (offset, width)
            self.bandpass_v[rx] = [offset,width]    # remember as floats
            low = offset
            high = offset + width
            return '%.f %.f' % (low,high)           # return limits, char Hz
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def bandpass(self,tp,rx='',data=''):    # offset_width = string
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            try:
                o_w = data.split(None,2)
                offset = float(o_w[0])
                width  = float(o_w[1])
            except:
                return NAK+'bandpass: invalid request %s' % data
            print "DEBUG **** bandpass offs, wid = ",offset,width
            cmd = '*R%cP%d' % ( ORION_RX_MAP[rx], int(offset) )
            self.transact('bandpass put pbt',cmd)   # Send PBT offset
            time.sleep(ORION_DSP_DELAY)
            cmd = '*R%cF%d' % ( ORION_RX_MAP[rx], int(width) )
            self.transact('bandpass put bw',cmd)    # send filter BW
            self.bandpass_v[rx] = [offset, width]   # remember as float Hz
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            cmd = '?R%cF' % ORION_RX_MAP[rx]
            r = self.transact('bandpass get bw',cmd)
            if is_nak(r): return r
            try:
                width = float (r[4:])
            except:
                return NAK+'bandpass: response error 1: %s' % r
            cmd = '?R%cP' % ORION_RX_MAP[rx]
            r = self.transact('bandpass get pbt',cmd)
            if is_nak(r): return r
            try:
                offset = float(r[4:])
            except:
                return NAK+'bandpass: response error 2: %s' % r
            self.bandpass_v[rx] = [offset,width]    # remember as floats
            return '%.f %.f' % (offset,width)
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def bandpass_standard(self,tp,rx='',data=''):
        # set according to standard bandpass table - NARROW/MEDIUM/WIDE etc.
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
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
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            cmd = '*R%cA%c' % ( ORION_RX_MAP[rx], ORION_AGC_MODE_MAP[data] )
            self.transact('put agc_mode',cmd)       # Send AGC mode
            self.agc_mode_v[rx] = data              # remember as string
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            cmd = '?R%cA' % ORION_RX_MAP[rx]
            r = self.transact('get agc_mode',cmd)
            if is_nak(r): return r
            modec = r[4]
            for mm in ORION_AGC_MODE_MAP.iterkeys():
                if ORION_AGC_MODE_MAP[mm] == modec:
                    self.agc_mode_v[rx] = mm        # remember as string
                    return mm
            return NAK
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

# put/get prog mode agc parameters: tc, hold, threshold (sec, sec, uV)
# Note that Orion also lets us set FAST/MEDIUM/SLOW AGC parameters, but we
# do not implement this capability.
    def agc_user(self,tp,rx='',data=''):
        if tp == T_PUT:
            # input: time-constant (sec), hold time (sec), threshold (uV)
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            try:
                list3 = data.split(None,3)
                list3f = map(float,list3)
            except:
                return NAK+'agc_user bad request %s' % data
            # (Should we save & restore current mode, which might not be 'prog'?)
            self.agc_mode(T_PUT,rx, 'PROG')   # ensure 'prog' mode
            db_per_sec = 3.0 / list3f[0]    # Orion's choice of unit
            cmd = '*R%cAD%.4f' % ( ORION_RX_MAP[rx], db_per_sec)
            self.transact('put db/sec',cmd)
            cmd = '*R%cAH%.4f' % ( ORION_RX_MAP[rx], list3f[1] )
            self.transact('put hold time',cmd)
            cmd = '*R%cAT%.4f' % ( ORION_RX_MAP[rx], list3f[2] )
            self.transact('put threshold',cmd)
            self.agc_user_v[rx] = list3f    # remember as floats
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            GAU_WT = 0.10                   # seems to prevent timeouts
            self.agc_mode(T_PUT,rx, 'PROG')
            cmd = '?R%cAD' % ORION_RX_MAP[rx]
            time.sleep(GAU_WT)
            r = self.transact('get db/sec',cmd)
            if is_nak(r): return r
            try:
                db_per_sec = float(r[5:])
            except:
                return NAK+'agc_user bad response 1 %s' % r
            tc = 3.0 / db_per_sec
            cmd = '?R%cAH' % ORION_RX_MAP[rx]
            time.sleep(GAU_WT)
            r = self.transact('get hold time',cmd)
            if is_nak(r): return r
            try:
                hold = float(r[5:])
            except:
                return NAK+'agc_user bad response 2 %s' % r
            cmd = '?R%cAT' % ORION_RX_MAP[rx]
            time.sleep(GAU_WT)
            r = self.transact('get threshold',cmd)
            if is_nak(r): return r
            try:
                thr = float(r[5:])
            except:
                return NAK+'agc_user bad response 3 %s' % r
            self.agc_user_v[rx] = [tc, hold, thr]
            return '%f %f %f' % (tc, hold, thr)
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def rf_gain(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            try:
                gain = float(data)
            except:
                return NAK+'rf_gain bad request %s' % data
            self.transact('put rf_gain',
                '*R%cG%03d' % ( ORION_RX_MAP[rx], int(gain * 100.0) )) 
            self.rf_gain_v[rx] = gain
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            r = self.transact('get_rf_gain',
                '?R%cG' % ORION_RX_MAP[rx])
            if is_nak(r): return r
            try:
                gain = float(r[4:])/100.
            except:
                return NAK+'rf_gain bad response %s' % r
            self.rf_gain_v[rx] = gain
            return '%.3f' % gain
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def af_gain(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            try:
                gain = float(data)
            except:
                return NAK+'af_gain bad request %s' % data
            # Note: We should have set up the spkr/phone selections in init.
            self.transact('put af_gain',
                '*U%c%03d' % ( ORION_RX_MAP[rx], int(gain * 256.0) ))
            self.af_gain_v[rx] = gain
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            r = self.transact('get_af_gain',
                '?U%c' % ORION_RX_MAP[rx])
            if is_nak(r): return r
            try:
                gain = float( r[3:] ) / 256.0
            except:
                return NAK+'af_gain bad response %s' % r
            self.af_gain_v[rx] = gain
            return '%.3f' % gain
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def rit(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            try:
                offset = float(data)
            except:
                return NAK+'rit bad request %s' % data
            if not in_range(ORION_RIT_RANGE_LIST,offset):
                return NAK+'rit: value out of range: %s' % data
            self.transact('put rit',
                '*R%cR%d' % ( ORION_RX_MAP[rx], int(offset)))
            self.rit_v[rx] = offset
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            r = self.transact('get rit',
                '?R%cR' % ORION_RX_MAP[rx])
            if is_nak(r): return r
            try:
                offset = float( r[4:] )
            except:
                return NAK+'rit bad response %s' % r
            self.rit_v[rx] = offset
            return '%.f' % offset
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def xit(self,tp,tx='',data=''):
        if tp == T_PUT:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            try:
                offset = float(data)
            except:
                return NAK+'xit bad request %s' % data
            if not in_range(ORION_XIT_RANGE_LIST,offset):
                return NAK+'xit: value out of range: %s' % data
            self.transact('put xit', '*RMX%d' % int(offset))
            self.xit_v[tx] = offset
            return ACK
        elif tp == T_GET:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            r = self.transact('get xit', '?RMX')
            if is_nak(r): return r
            try:
                offset = float( r[4:] )
            except:
                return NAK+'xit bad response %s' % r
            self.xit_v[tx] = offset
            return '%.f' % offset
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def mic_gain(self,tp,tx='',data=''):
        if tp == T_PUT:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            try:
                gain = float(data)
            except:
                return NAK+'mic_gain bad request %s' % data
            self.transact('put mic_gain', '*TM%03d' % int(gain * 100.0) )
            self.mic_gain_v[tx] = gain
            return ACK
        elif tp == T_GET:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            r = self.transact('get mic_gain', '?TM')
            if is_nak(r): return r
            try:
                gain = float( r[3:] ) / 100.0
            except:
                return NAK+'mic_gain bad response %s' % r
            self.mic_gain_v[tx] = gain
            return '%.3f' % gain
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

#    def mic_source(self,tp,tx,source):    not supported

    def speech_proc(self,tp,tx='',data=''):
        if tp == T_PUT:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            try:
                sp_gain = float(data)
            except:
                return NAK+'sp bad request %s' % data
            self.transact('put speech_proc', '*TS%2d' % int( 10.0 * sp_gain ) )
            self.speech_proc_v[tx] = sp_gain
            return ACK
        elif tp == T_GET:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            r = self.transact('get_speech_proc', '?TS')
            if is_nak(r): return r
            try:
                sp_gain = float( r[3:] ) / 10.0
            except:
                return NAK+'sp bad response %s' % r
            self.speech_proc_v[tx] = sp_gain
            return '%.3f' % sp_gain
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def noise_blank(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            try:
                nb_gain = float(data)
            except:
                return NAK+'nb bad request %s' % data
            self.transact('put noise_blank',
                '*R%cNB%d' % ( ORION_RX_MAP[rx], int(10.0 * nb_gain) ))
            self.noise_blank_v[rx] = nb_gain
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            r = self.transact('get_noise_blank',
                '?R%cNB' % ORION_RX_MAP[rx])
            if is_nak(r): return r
            try:
                nb_gain = float( r[5:] ) / 10.0
            except:
                return NAK+'nb bad response %s' % r
            self.noise_blank_v[rx] = nb_gain
            return '%.3f' % nb_gain
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def noise_reduce(self,tp,rx='',data=''):    # Broken in 1.372 & 1.373b5
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            try:
                nr_gain = float(data)
            except:
                return NAK+'nr bad request %s' % data
            self.transact('put noise_reduce',
                '*R%cNN%d' % ( ORION_RX_MAP[rx], int(10.0 * nr_gain) ))
            self.noise_reduce_v[rx] = nr_gain
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            r = self.transact('get noise_reduce',
                '?R%cNN' % ORION_RX_MAP[rx])
            if is_nak(r): return r
            try:
                nr_gain = float( r[5:] ) / 10.0
            except:
                return NAK+'nr bad response %s' % r
            self.noise_reduce_v[rx] = nr_gain
            return '%.3f' % nr_gain
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def notch_auto(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            try:
                gain = float(data)
            except:
                return NAK+'notch_auto bad request %s' % data
            self.transact('put notch_auto',
                '*R%cNA%d' % ( ORION_RX_MAP[rx], int(10.0 * gain) ))
            self.notch_auto_v[rx] = gain
            return ACK
        elif tp == T_GET:                   # read auto_notch broken 1.372
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            r = self.transact('get_notch_auto', 
                '?R%cNA' % ORION_RX_MAP[rx])
            if is_nak(r): return r
            try:
                gain = float( r[5:] ) / 10.0
            except:
                return NAK+'notch_auto bad response %s' % r
            self.notch_auto_v[rx] = gain
            return '%.3f' % gain
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

# manual (non-auto) notch control not available in 1.372

    def transmit(self,tp,tx='',data=''):       # =="0" -> off, otherwise -> on
        if tp == T_PUT:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            ptt = int(data)
            pttcmd = '*TU'
            if ptt==1: pttcmd = '*TK'
            self.transact('put transmit', pttcmd )
            self.transmit_v[tx] = ptt
            return ACK
        if tp == T_GET:                 # Orion has no query for ptt
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            return self.transmit_v[tx]  # Use self-stored value
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def power(self,tp,tx='',data=''):  # Power in watts, max 100.
        if tp == T_PUT:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            try:
                pwr = float(data)               # =0 -> disable tx
            except:
                return NAK+'power bad request %s' % data
            pwr2 = min(pwr,100.0)
            self.transact('put power', '*TP%d' % int( pwr2 ) )
            self.power_v[tx] = pwr2
            return ACK
        elif tp == T_GET:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            r = self.transact('get power', '?TP')
            if is_nak(r): return r
            try:
                pwr = float( r[3:] )
            except:
                return NAK+'power bad response %s' % r
            self.power_v[tx] = pwr
            return '%.f' % pwr
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

# to do:
# tx_ant()
# rx_ant()

    def memory_channel(self,tp,vfo='',data='1'):
        if tp == T_PUT:
            ch = int(data)
            if not in_range(ORION_MEMORY_CHANNELS,ch):
                return NAK+'Invalid memory channel'
            self.memory_channel_v = ch
        elif tp == T_GET:
            if not in_range(ORION_MEMORY_CHANNELS,ch):
                return NAK+'Invalid memory channel'
            return '%d' % self.memory_channel_v
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

# The Orion store memory operation stores a vfo frequency from VFO A or B,
# but also captures MODE, BW, and PBT settings.  Note that this breaks
# the "independent vfo" theory, since MODE, etc, refer to _receiver_
# settings.  Beware of the side effects!

    def vfo_memory(self,tp,vfo='',data=''):
        if tp == T_PUT:
            if not ORION_VFO_MAP.has_key(vfo): return NAK+'invalid vfo %s' % vfo
            self.freq(T_PUT,vfo,data)
            ch = int(self.memory_channel_v)
            self.transact('put vfo_memory',
                '*KW%c%d' % (ORION_VFO_MAP[vfo],ch))
            return ACK
        elif tp == T_GET:
            if not ORION_VFO_MAP.has_key(vfo): return NAK+'invalid vfo %s' % vfo
            ch = int(self.memory_channel_v)
            self.transact('get vfo_memory',
                '*KR%c%d' % (ORION_VFO_MAP[vfo],ch))  # Send mem to vfo.
            time.sleep(ORION_DSP_DELAY)     # (change to bandpass)
            # possibly should use Backend methods to store new Mode, BW,
            # and PBT, as well as VFO freq.  However, this requires an
            # analysis of which rx is currently attached to this vfo!
            time.sleep(0.2)                 # Avoid read timeout
            ans = self.freq(T_GET,vfo)      # NB the vfo is not restored
            return ans                      # returns only the freq.
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def strength_raw(self,tp,rx='',data=''):      # Get uncalibrated int value
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            r = self.transact('get strength_raw', '?S' )
            if is_nak(r): return r
            # Can be @SRMmainSsub in Rx mode or @STFfffRrrrSsss in Tx
            if not r[2] == 'R':
                return NAK+'get_strength_raw: must be in rcv mode'
            x1, x2 = r.split('M')
            xmain, xsub = x2.split('S')     # Well, that's one way to parse!
            if rx == 'MAIN':
                value = xmain.lstrip('0')       # trim leading zeroes
            else:
                value = xsub.lstrip('0')
            self.strength_raw_v[rx] = int (value)
            return value
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def strength(self,tp,rx='',data=''):
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            if self.strength_table == []: return NAK+'No S-meter cal.'
            raws= self.strength_raw(T_GET,rx)
            try:
                raw = float(raws)    # uncalibrated float, paranoid!
            except:
                return NAK+'strength: invalid raw response %s' % raws
            p = (0.,-45.)             # "previous" pair
            for t in self.strength_table:
                if t[0] > raw:      # piecewise linear interpolation
                    cal = p[1] + (raw-p[0]) * ( (t[1]-p[1])/(t[0]-p[0]) )
                    break
                else:
                    p = t           # remember "previous"
            else:           # if raw is higher than the highest cal point
                cal = t[1]          # Use highest dB value
            self.strength_v[rx] = cal
            return '%.1f' % cal     # return float dB in string
        elif tp == T_TEST: return ACK
        else: return TP_INVALID
        
    def swr_raw(self,tp,tx='',data=''):    # Get rig-dependent string,
                                        # e.g., 'fwd rev ratio'
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            r = self.transact('get swr_raw', '?S')
            if is_nak(r): return r
            # hopefully @STFfffRrrrSsss (fwd, rev, ratio)
            if not r[2] == 'T':
                return NAK+'swr_raw: must be in xmit mode'
            x1,x2 = r.split('F')
            xfwd,x3 = x2.split('R')
            xrev,xratio = x3.split('S')
            self.swr_raw_v[tx] = [ int(xfwd), int(xrev), int(xratio) ]
            return '%s %s %s' % (xfwd, xrev, xratio)    # string of 3 vals
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def swr(self,tp,tx='',data=''):         # get the actual SWR ratio (float)
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            if not tx in ORION_TX_LIST: return NAK+'tx invalid: %s' % tx
            raw = self.swr_raw(T_GET,tx)    # Get raw values
            if raw.startswith(NAK): return raw
            f,r,s = raw.split(None,3)
            if int(s) >= 800:
                ratio = 999.                # off-scale
            else:
                ratio = float(s) / 256.     # Orion's idea of swr?
            self.swr_v[tx] = ratio
            return '%.2f' % ratio
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def atten(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            if not self.atten_dict.has_key(data):
                return NAK+'Invalid attenuator request: %s' % data
            try:
                o_att = self.atten_dict[data]
            except:
                return NAK+'atten bad request %s' % data
            self.transact('put atten',
                '*R%cT%d' % ( ORION_RX_MAP[rx], o_att) )
            self.atten_v[rx] = data         # Save actual setting (string)
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            r = self.transact('get_atten',
                '?R%cT' % ORION_RX_MAP[rx])
            if is_nak(r): return r
            try:
                o_att = int( r[4:] )            # Orion's attenuator code
            except:
                return NAK+'atten bad response %s' % r
            for att_s in self.atten_dict:       # reverse dictionary lookup
                if self.atten_dict[att_s] == o_att: break
            else:
                return NAK+'Invalid attenuator setting read: %d' % o_att
            self.atten_v[rx] = att_s            # save the string value
            return att_s                        # and return it
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

    def preamp(self,tp,rx='',data=''):
        if tp == T_PUT:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            onoff = bool(data)
            if rx == 'MAIN':                        # SUB has no preamp
                self.transact('put preamp', '*RME%d' % onoff )
            self.preamp_v[rx] = onoff
            return ACK
        elif tp == T_GET:
            if not rx in ORION_RX_LIST: return NAK+'rx invalid: %s' % rx
            if rx == 'MAIN':
                r = self.transact('get_preamp', '?RME') 
                if is_nak(r): return r
                onoff = ( r[4:5] == '1' )
                self.preamp_v[rx] = onoff
                return '%d' % onoff
            else:
                self.preamp_v[rx] = False       # No preamp on sub rx
                return False
        elif tp == T_TEST: return ACK
        else: return TP_INVALID

# Firmware version-specific subclasses.
# We are asking the client to declare which version he is using.
# Alternatively, we could have used the get_status info for this purpose and
# relied on the single TT_orion class, but that would have been messier.

class TT_orion_v1(TT_orion):
# Important note: The original Orion (model 565) when running version 1.xxx
# firmware has problems with serial command timing.  The command/response sequence
# can be corrupted if commands come too fast.  Rigserve users are strongly 
# recommended to upgrade to version 2.xxx firmware for this reason.

# Orion with "v1" S-meter cal. (v1.372) and any other "v1" behavior
# Updated to correspond to Hamlib driver, 11/2007
    def __init__(self):
        # Calibration (hardware_value, dB value)
        # NB - these values were measured, but should not be relied upon
        # too much!  Also, this calibration is only measured on the main rx.
        SMETER_CAL_v1372  = [ 
                (  10., -47. ), # S 1.5 min meter indication
                (  13., -42. ),
                (  18., -37. ),
                (  22., -32. ),
                (  27., -27. ),
                (  32., -18. ),
                (  37., -11. ),
                (  42.,  -4. ), # S9
                (  47.,  -1. ),
                (  52.,  10. ),
                (  57.,  20. ),
                (  65.,  30. ),
                (  74.,  40. ) #severe dsp quantization error 
                             ] # at high end of scale
        TT_orion.__init__(self)
        self.strength_table = SMETER_CAL_v1372
        return None

class TT_orion_v2(TT_orion):
# Orion with "v2" S-meter cal. and "v2" behavior
# Will it stay the same for all v2.x?
    def __init__(self):
        SMETER_CAL_v2059d   = [
                (10., -48.),    # S1 = min. indication
                (24., -42.),
                (38., -36.),
                (47., -30.),
                (61., -24.),
                (70., -18.),
                (79., -12.),
                (84.,  -6.),
                (94.,   0.),    # S9
                (103., 10.),
                (118., 20.),
                (134., 30.),
                (147., 40.),
                (161., 50.) ]
        TT_orion.__init__(self)
        self.strength_table = SMETER_CAL_v2059d
        return None

# operate   (not available)

if __name__ == '__main__':
# This is the place to test the subclass and ic module routines.
# THIS CODE IS NOT EXECUTED IF THIS MODULE IS INVOKED FROM ANOTHER PYTHON ROUTINE.
    rig = TT_orion_v2()
    print rig.init(T_PUT,data='/dev/ham.orion')
    print rig.init(T_GET)
    print rig.status(T_GET)
    print rig.rx_mode(T_GET,'MAIN')
    print rig.rx_mode(T_PUT,'MAIN','LSB')
    print rig.rx_mode(T_GET,'MAIN')
    print rig.rx_mode(T_PUT,'MAIN','USB')
    print rig.freq(T_GET,'VFOA')
    print rig.freq(T_PUT,'VFOA', '7100120')
    print rig.freq(T_GET,'VFOA')
    print rig.freq(T_GET,'VFOA')
    print rig.vfo_step(T_GET,'VFOA')
    print rig.vfo_step(T_PUT,'VFOA','100')
    print rig.vfo_step(T_GET,'VFOA')
    print rig.vfo_step(T_PUT,'VFOA','1')
    print rig.bandpass(T_GET,'MAIN')
    print rig.bandpass_limits(T_PUT,'MAIN','222 555')
    print rig.bandpass_limits(T_GET,'MAIN')
    print rig.bandpass_standard(T_PUT,'MAIN','MEDIUM')
    print rig.bandpass(T_GET,'MAIN')
    print rig.atten(T_PUT,'SUB','OFF')
    print rig.atten(T_GET,'SUB')
    print rig.agc_user(T_GET,'MAIN')
    print rig.agc_user(T_GET,'MAIN')
    print rig.info(T_GET)
    print rig.strength_raw(T_GET,'MAIN')
    print rig.strength(T_GET,'MAIN')
    print rig.freq(T_GET,'VFOA')
    print rig.freq(T_PUT,'VFOA', '7100120')
    print rig.freq(T_GET,'VFOA')
    print rig.freq(T_GET,'VFOA')
    print rig.preamp(T_GET,'MAIN')
    print rig.atten(T_GET,'MAIN')
    print rig.mic_gain(T_PUT,'TX','0.51')
    print rig.mic_gain(T_GET,'TX')
    print rig.af_gain(T_PUT,'MAIN','0.12')
    print rig.af_gain(T_GET,'MAIN')
    print rig.rf_gain(T_PUT,'MAIN','0.79')
    print rig.rf_gain(T_GET,'MAIN')
    
