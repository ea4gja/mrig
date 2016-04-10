#!/usr/bin/env python
#
# File: icom.py
# Version: 1.0 
#
# mrigd: Icom and Icom_trx class definition
# Copyright (c) 2006-2007 Martin Ewing
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

# This is the subclass of Backend to handle Icom equipment
#
# NOTES:
# We have relied heavily on Icom CI-V reference information from
# Ekkehard Plicht, http://df4or.de/civ/ . Thanks!
#
# The Icom class has the methods that are common to all (or most) Icom rigs,
# both receivers and transceivers.  It also supports the Ten-Tec Omni VI
# and Omni VI Plus.

# An Icom_trx subclass has those methods that are used in all (or most)
# Icom transceivers.  There is (probably) no need for an equivalent
# receiver subclass.

# Most Icom models will have their own subclass to manage the
# information that is unique to a given model.  However, the methods
# defined in Icom and Icom_trx should cover the commonly used functions
# of most rigs.

# TO DO:
# - How to check self.bands_tx for Tx freqs?
# - Test IC_r75 functions (see ic_r75.py)
# - Implement Bandpass method using Twin PBT as available in most rigs.
# - Implement common trx methods in Icom_trx.
# - Check ICOM_CMD and other tables for accuracy.
# - Add scanning / memory functions?

import sys, serial, time

from backend import *
from ic_codes import *

# Capabilities:  This is a Python dictionary that expresses all the methods that
# are being supported for a particular Icom model.  "All" CI-V rigs are supposed
# to have IC_COMMON_CAPABILITIES.  See DF4OR's Section 5.2 "Older Rigs", e.g.
# These capabilities may not all have implented Rigserve methods.

#IC_COMMON_CAPABILITIES = set(['TR_FREQ','TR_MODE', 'RD_FRQ_EDGES', 'RD_OP_FRQ',
#    'RD_OP_MODE','SET_FREQ', 'SET_MODE', 'VFO_MODE', 'MEM_WRITE', 'MEM2VFO'])
IC_COMMON_CAPABILITIES = { 'freq':'rw', 'rx_mode':'rw', 'tx_mode':'rw'}

#save for later use
# {'vfo_select':'w', 'vfo_step':'rw', 'rit':'rw', 'agc_mode':'rw',
#    'af_gain':'rw', 'rf_gain':'rw', 'squelch_level':'rw', 'strength_raw':'r',
#    'atten':'rw', 'squelch_open':'r', 'rx_mode':'rw', 'rx_ant':'rw'}

# Receiver-related methods, used by all Icom gear -- at least the HF
# models.
class Icom(Backend):
    def __init__(self):
        Backend.__init__(self)
        self.ser = None             # Serial port object
        self.port = ''              # device name
        self.port_rate = 0          # params as required by Orion
        self.port_size = 8
        self.port_parity = 'N'
        self.port_stopbits = 1
        self.port_predelay = 0.0
        self.port_postdelay = 0.02
        self.ser = False
#
        self.capabilities = IC_COMMON_CAPABILITIES  # default for Icom
        self.vfo_step_v = 0
        self.vfo_step_list = []     # int Hz, to be filled by subclass
        self.vfo_step_map = {}
        self.vfo_list = []
        self.agc_mode_v = ''
        self.af_gain_v = 0
        self.rf_gain_v = 0
        self.atten_v = ''
        self.squelch_level_v = 0
        self.center_width = [ 0., 0.]
# Local to icom & subclasses
        self.civ_address = 0x00    # to be set by specific rig subclass
        self.agc_mode_map = {}
        self.r8500_kluge = False    # Will be set if running R8500
        self.mode_map = {}
        self.mode_map_r = {}
        self.rx_ant_v = ''
        self.rx_ant_list = []
        self.rx_ant_dict = {}
        return

    def serial_setup(self,s):       # set up serial port and open
    # s = "dev [speed [char_size [parity 
    #           [stopbits [predelay [postdelay]]]]]]"
        lst = s.split()     # parse the input
        nlst = len(lst)     # no. of args
        if nlst < 1: 
            print "port_control: No arguments"
            return XNAK
        self.port = lst[0]          # device name
        self.port_rate = 19200
        if nlst >=2: self.port_rate = int(lst[1])
        self.port_size = 8
        if nlst >=3: self.port_size = int(lst[2])
        self.port_parity = 'N'
        if nlst >=4: self.port_parity = lst[3]
        self.port_stopbits = 1
        if nlst >= 5: self.port_stopbits = int(lst[4])
        if nlst >= 6: self.port_predelay = float(lst[5])
        if nlst >= 7: self.port_predelay = float(lst[6])
        # open the port
        # Note: rtscts=0 -> no flow control (required for Omni w/o rtscts jumpers in cable)
        #   It would be better to use rtscts=1 when rig supports it.
        try:
            self.ser = serial.Serial(
                self.port, 
                baudrate=self.port_rate,
                bytesize=self.port_size,
                parity=self.port_parity,
                stopbits=self.port_stopbits,
                xonxoff=0,rtscts=0,timeout=0.2)
        except serial.SerialException:
            return NAK+'Cannot open serial port.'
        self.ser.flushInput()
        self.ser.flushOutput()
        return ACK

    def ic_put(self, meth, s, cmd): # cmd is sometimes a level, byte, or freq ##
        """
        ic_put sends the Icom's command from the command table, after
        checking whether this rig has the capability for the command.
        """
        if 'w' in self.capabilities.get(meth,''):
            thiscmd = ICOM_CMD[s]
            code = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN], cmd)
            return code         # ACK or NAK
        else:
            return NOT_DEF         # no capability!

    def ic_get(self, meth, s, cmd=()): # cmd is always a tuple
        """
        ic_get gets info from rig after capability check
        may return either data(some type) or a NAK message.
        """
        if 'r' in self.capabilities.get(meth,''):
            thiscmd = ICOM_CMD[s]
            data = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN] + cmd)
#            if is_nak(data): return data
            return data
        else:
            return NOT_DEF         # no capability!

    def init(self,tp,rx='',data='/dev/ttyS0'):
#           Firmware initalize
        if tp == T_PUT:
            return self.serial_setup(data)
        elif tp == T_GET:
            return None, NOT_DEF
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

# Get rig "status"
# Note that we return the *default* CIV address for this rig, which may not
# be the same as the current address. The user might have modified it.
# Won't work for Omni6, 735, ... (?)
    def status(self,tp,rx=''): 
        if not self.ser: return NAK+'Serial port not open.'
        if tp == T_GET:
#            thiscmd = ICOM_CMD['GET_ID']
#            s3,err = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            resp = self.ic_get('status', 'GET_ID')
            if is_nak(resp): 
                return resp
            else:
                return 'CIV Addr: 0x%X' % ord(resp[2])
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF      # no put

    def info(self,tp,rx='',data=''): 
        if tp == T_GET:
            return Backend.info(self,T_GET,'','')
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF


# Note: Presently checking only self.bands.  Need to check self.bands_tx
# if non-null ** for transmitting **

    def freq(self,tp,v,s=''):
        if tp == T_PUT:
            f = float(s)
            if not in_band(self.bands[v],f):    # what about TX != RX bands??
                return NAK+'Out of band frequency request: %f' % f
            err = self.ic_put('freq', 'SET_FREQ', f )
#            thiscmd = ICOM_CMD['SET_FREQ']
#            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN], f)
            if is_nak(err): return err
            return ACK
        elif tp == T_GET:
#            thiscmd = ICOM_CMD['RD_OP_FRQ']
#            freq,err = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            resp = self.ic_get('freq', 'RD_OP_FRQ') # resp=(freq,err)
            if is_nak(resp): return resp
            return '%.f' % resp
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

# Set Tuning Step
# Note that the steps are model-dependent, so we need to use a 'vfo_step_map'
# passed up from the model's subclass.
    def vfo_step(self,tp,v,s=''):
        if tp == T_PUT:
            si = int(float(s))
#            thiscmd = ICOM_CMD['TSTEP']
            try:
#                err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN], 
#                                            self.vfo_step_map[si])
#                if err[0] == NAK1: return err
                vsm = self.vfo_step_map[si]
            except KeyError:
                return NAK+'Invalid freq. step size requested. %d' % si
            err = self.ic_put('vfo_step', 'TSTEP', vsm)
            if is_nak(err): return err
            self.vfo_step_v = si
            return ACK
        elif tp == T_GET:
            return '%.f' % self.vfo_step_v
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

    def vfo_select(self,tp,v,s=''):
        if tp == T_PUT:
            if v not in self.vfo_list:
                return NAK+'Invalid vfo in select_vfo = %s' % v
            if v == self.vfo_list[0]:       # Normally, 'VFOA'
#                thiscmd = ICOM_CMD['VFO_A']
                err = self.ic_put('vfo_select', 'VFO_A', NULL_TUP)
            else:                           # Normally, 'VFOB'
#                thiscmd = ICOM_CMD['VFO_B']
                err = self.ic_put('vfo_select', 'VFO_B', NULL_TUP)
#            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            if is_nak(err): return err
            return ACK
        elif tp == T_GET: return NOT_DEF
        elif tp == T_TEST: return ACK   # Yes, the method is defined
        else: return NOT_DEF

    def rit(self,tp,rx,s=''):
        if tp == T_PUT:
            f = float(s)
            if abs(f) > 9.99e3:
                return NAK+'Invalid rit request = %f' % f
#            thiscmd = ICOM_CMD['SET_OFF_FREQ']
#            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN], f)
            err = self.ic_put('rit', 'SET_OFF_FREQ', f)
            if is_nak(err): return err
            return ACK
        elif tp == T_GET:
#            thiscmd = ICOM_CMD['RD_OFF_FREQ']
#            freq,err = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            resp = self.ic_get('rit', 'RD_OFF_FREQ') # resp=(freq,err)
            if is_nak(resp): return resp
            return '%.f' % freq
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

    def agc_mode(self,tp,rx,mode=''):           # Not for R8500 -- not tested
        if tp == T_PUT:
            m = mode.strip()
#            thiscmd = ICOM_CMD['SET_AGC']
#            try:
#                err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN], self.agc_mode_map[m])
#                if err[0] == NAK1: return err
#            except KeyError:
#                return NAK+'Invalid AGC mode requested: %s' % m
            try:
                mm = self.agc_mode_map[m]
            except KeyError:
                return NAK+'Invalid AGC mode requested: %s' % m
            err = self.ic_put('agc_mode', 'SET_AGC', mm)
            if is_nak(err): return err
            self.agc_mode_v = m
            return ACK
        elif tp == T_GET:
            return self.agc_mode_v
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

    def af_gain(self,tp,rx,s=''):
#        response, self.af_gain_v = self.level_fn('af_gain',
#                'AF', self.af_gain_v,tp,rx,s)
        if tp == T_PUT:
            err = self.ic_put('af_gain', 'SET_AF', float(s))
            return err
        elif tp == T_GET:
            resp = self.ic_get('af_gain', 'GET_AF')
            return resp
        elif tp == T_TEST: return ACK
        else: return NOT_DEF

    def rf_gain(self,tp,rx,s=''):           # But not in R8500
#        response, self.rf_gain_v = self.level_fn('rf_gain',
#                'RF',self.rf_gain_v,tp,rx,s)
        if tp == T_PUT:
            err = self.ic_put('rf_gain', 'SET_RF', float(s))
            return err
        elif tp == T_GET:
            return self.ic_get('rf_gain', 'GET_RF')
        elif tp == T_TEST: return ACK
        else: return NOT_DEF
#        return response

    def squelch_level(self,tp,rx,s=''):
#        response, self.squelch_level_v = self.level_fn('squelch_level',
#                'SQL',self.squelch_level_v,tp,rx,s)
        if tp == T_PUT:
            err = self.ic_put('squelch_level', 'SET_SQL', float(s))
            return err
        elif tp == T_GET:
            return self.ic_get('squelch_level', 'SET_SQL')
        elif tp == T_TEST: return ACK
        else: return NOT_DEF
#        return response

# apf level exists in Icom rigs, but is not present in the Rigserve Backend definition.

# And then there are Twin PBT settings, which are "levels" in Icom, but 
# needs manipulation to fit into Rigserve's bandpass framework.

    def strength_raw(self,tp,rx,data=''):
        if tp == T_PUT:
            return NOT_DEF
        elif tp == T_GET:
#            thiscmd = ICOM_CMD['RD_STRENGTH']
#            f,err = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            resp = self.ic_get('strength_raw','RD_STRENGTH')
            if is_nak(resp): return resp
            return '%d' % int(resp*255.)
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

    def atten(self,tp,rx='',data=''):     # attenuation from list of allowed vals
        if tp == T_PUT:
            try:
                a = self.atten_dict[data]   # 0x00,10,20,30 for R8500 etc.
            except KeyError:
                return NAK+'Invalid attenuator request: %s' % data
#            thiscmd = ICOM_CMD['ATTN']
#            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN] + (a,))
            err = self.ic_put('atten', 'ATTN', (a,))
            if is_nak(err): return err
            self.atten_v = data
            return ACK
        elif tp == T_GET:               # must rely on local stored value
            return self.atten_v
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

    def squelch_open(self,tp,rx,s=''):  # return '1' if squelch open
        if tp == T_PUT:
            return NOT_DEF
        elif tp == T_GET:
#            thiscmd = ICOM_CMD['RD_SQL_STATUS']
#            ans,err = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            resp = self.ic_get('squelch_open', 'RD_SQL_STATUS') # resp=(ans,err)
            if is_nak(resp): return resp
            return '%1d' % ord(resp[2])  # '1' or '0'
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF            # No put option

    def rx_mode(self,tp,rx,mode=''):
        if tp == T_PUT:
#            thiscmd = ICOM_CMD['SET_MODE']
            try:
                code = self.mode_map[mode]  # translate name to numeric code
                # "code" is a 3-digit hex number (0xXXY), which will
                # translate into 2 bytes: 0xXX, and 0x0Y for the Icom mode
                # and passband info.
            except KeyError:
                return NAK+'Unknown mode requested: %s' % mode
#            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN] + 
#                                            (code >> 4, code & 0x0F))
            err = self.ic_put('rx_mode', 'SET_MODE', (code >> 4, code & 0x0F) )
            if is_nak(err): return err
            return ACK
        elif tp == T_GET:
#            thiscmd = ICOM_CMD['RD_OP_MODE']
#            ms,err = thiscmd[FN](self.ser, self.civ_address, thiscmd[BN])
            ms = self.ic_get('rx_mode', 'RD_OP_MODE')
            if is_nak(ms): return ms
            if len(ms) < 3: ms = ms + '\0'  # Omni6 & 735 (?) don't return bandwidth
            try:
                m = ord(ms[1]) << 4 | ord(ms[2])    # recompose code number
            except IndexError:
                return None, NAK+'get rx_mode, index error.'
            try:
                ans = self.mode_map_r[m]            # find mode name from code
            except KeyError:
                return None, NAK+'Unrecognized rx hex mode: 0x%X' % m
            return ans
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF

    def rx_ant(self,tp,rx='',data=''):     #### NOT TESTED MSE, 8/27/07 ####
        if tp == T_PUT:
            try:
                a = self.rx_ant_dict[data]  # a tuple!
            except KeyError:
                return NAK+'invalid antenna request: %s' % data
#            thiscmd = ICOM_CMD['ANT_STAT']
#            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN] + a)
            err = self.ic_put('rx_ant', 'ANT_STAT')
            if is_nak(err): return err
            self.rx_ant_v = data
            return ACK
        elif tp == T_GET:        
            return self.rx_ant_v        # For most rigs, could probably do a real read op.
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return NOT_DEF


### In most Icom rigs, bandpass is determined by PBT inner/outer, if available.
### In R8500 only, it is set by IF shift (see IC_r8500 class)

    def bandpass(self,tp,rx,c_w=''):
### Needs PBT-type routine to be written here!
        return NAK+'undefined bandpass operation'

########################################################################
## Icom_trx ##
# Icom_trx (transceiver) class is based on Icom class.  Every transceiver
# includes a receiver!

# With the capabilities mechanism, it is no longer particularly useful
# to have an Icom_trx class.  Everything can be put into the Icom class,
# with appropriate capabilities selected for receivers, transceivers, etc.
# Icom_trx may be withdrawn in a future release.

class Icom_trx(Icom):
    def __init__(self):
        Icom.__init__(self)
        self.tx_power = 0.
        self.tx_power_max = 100.    # Watts, will be rig dependent
        return

########### Remaining code in this class is UNTESTED.  Please report your results.

# In general, we ignore tx field (one tx only!)

    def transmit(self,tp,tx='',data=''):
        if tp == T_PUT:
            if data.strip() == '1': txc = 1       # input = '0' or '1'
            else: txc = 0
            resp = self.ic_put('transmit','SET_XMT_ON', (txc,))
            return resp          # NOT_DEF, if no capability, else ACK/NAK
        elif tp == T_GET:
            resp = self.ic_get('transmit','GET_XMT_ON') # resp=(txs,err)
            if is_nak(resp): return resp
            return '%1d' % ord(resp[0])      # Check me!
        elif tp == T_TEST: return ACK
        else: return NOT_DEF

    def power(self,tp,tx='',data=''):
        if tp == T_PUT:
            try:
                p = float(data)/self.tx_power_max   # range 0. - 1.
                p = max(0.0, min(1.0, p))
            except ValueError:
                return NAK+'Invalid power request: %s' % data
#            thiscmd = ICOM_CMD['SET_RF_POWER']
#            err=thiscmd[FN](self.ser, self.civ_address, thiscmd[BN], p)
            err = self.ic_put('power', 'SET_RF_POWER', p)
            if is_nak(err): return err
            self.tx_power = p
            return ACK
        elif tp == T_GET:
#            thiscmd = ICOM_CMD['GET_RF_POWER']
#            p,err = thiscmd[FN](self.data, self.civ_address, thiscmd[BN])*self.tx_power_max
            resp = self.ic_get('power', 'GET_RF_POWER')
            if is_nak(resp): return resp
            return '%.3f' % resp
        elif tp == T_TEST: return ACK
        else: return NOT_DEF

if __name__ == "__main__":
# This is the place to test the subclass and ic module routines.
# Not executed if this file is invoked by another Python routine.
    pass
