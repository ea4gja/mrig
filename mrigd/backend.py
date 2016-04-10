#!/usr/bin/env python
#
# File: backend.py
# Version: 1.0
#
# mrigd: backend base class definition
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


import time
from globals import *
from service import *
from service_hamlib_compat import *

# This is a class from which all rig backends are subclassed.
#
# Most class variables are kept as space-delimited strings, lists
# of strings, or dictionaries with string values.

class Backend(object):
    def __init__(self, rig_name):
        self.rig_name = rig_name

        self.port_type      = "S"   # (S)erial, (P)parallel, (U)SB, etc.
        self.port           = ''    # device name

        # Rig-wide definitions
        self.bands          = {}    # allowed bands, per VFO (sorry Orion)
        self.bands_tx       = {}    # bands for Tx, if different from Rx
        self.memory_range   = [1,1] # low, high channels
        self.services_dict = {"dummy": Service(rig_name), "hamlib": Service_Hamlib_Compat(rig_name)}   # available services

        # Backend capabilities
        self.backend_id     = ''
        self.vfo_list       = []    # definitions of VFO's in rig
                                    # NB: No embedded spaces!
        self.vfo_step_list  = []    # allowed step sizes, int Hz
        self.rx_list        = []    # definition of Rx's in rig
        self.atten_dict     = {}    # allowed attenuator settings
            # assuming same atten list is valid for all rx's ...?
        self.tx_list        = []    # definition of Tx's in rig
        self.mode_list      = []    # rig's supported modes
        self.bandpass_dict  = {}    # supported fixed passbands
        self.agc_mode_list  = []    # supported fixed/programmable AGC
        self.mic_source_list= []    # supported mic inputs
        self.rx_ant_list    = []    # supported rx antennas
        self.tx_ant_list    = []    # supported tx antennas
        self.capabilities   = {}    # methods supported by the rig(*)
        return None

    def get_services_dict(self):
        return self.services_dict

# (*) Families of rigs (e.g., Icom) may define many methods, but individual
# rig models won't support all of them.  The capabilities dictionary has the
# form { 'method-name':'rw' } to signify that this model supports a particular
# method.

# The "info" operation is provided in the Backend class so we can
# be sure to provide the client with data about the particular rig's
# capabilities in a standardized format that the client can decode
# without "too much" trouble.  In general, you get a line like
# <data_item>= <Python text representation>
# Having it here in Backend assures that all rig backends use the same
# info report format.

    def info(self,tp,rx='',data=''):   # Tell client about this rig
        if tp == T_PUT: return NO_WRITE
        elif tp == T_GET:
            r  = "INFO=  '%s'"   % self.backend_id
            r += "\nUTC=   '%s'" % time.asctime(time.gmtime())
            r += '\nCAPABILITIES= ' + str(self.capabilities)
            r += '\nVFOS=  ' + str(self.vfo_list)
            r += '\nBANDS= ' + str(self.bands)
            r += '\nRX=    ' + str(self.rx_list)
            r += '\nATTEN= ' + str(self.atten_dict)
            r += '\nTX=    ' + str(self.tx_list)
            r += '\nMODE=  ' + str(self.mode_list)
            r += '\nBP=    ' + str(self.bandpass_dict)
            r += '\nAGC=   ' + str(self.agc_mode_list)
            r += '\nMICSR= ' + str(self.mic_source_list)
            r += '\nRXANT= ' + str(self.rx_ant_list)
            r += '\nTXANT= ' + str(self.tx_ant_list)
            r += '\nMEMCH= ' + str(self.memory_range)
            return r
        elif tp == T_TEST: return ACK   # Yes, the method is defined.
        else: return TP_INVALID
##
# This is a compact definition of the entire supported Backend
# command set.  These methods are to be overloaded by rig subclass
# methods.
# If they are called, they return 'None', signifying they are not
# implemented for current rig class.
#
# Argument 1 (pointer to self - class ID)
# Argument 2 a2 = type (T_TEST|T_GET|T_PUT|T_INFO|...)
# Argument 3 a3 = vfo/rx/tx identifier
# Argument 4 data = data for "put" commands
#
# Rig control
# Argument 3 (ignore)
# Argument 4 (data for put cmds)

    def init(self,a2,a3,data=''): return None
        # put - initialize serial port (or other available port)
        # get - provide rig's response to init, if available.
        # a3 (rx) is ignored, may be blank
    def operate(self,a2,a3,data=''): return None
        # put - place rig in operate (True) or standby mode
        # get - rig mode - operate (True) or standby (False), if available
        # a3 (rx) is ignored, may be blank
    def status(self,a2,a3,data=''): return None
        # get - rig firmware version, etc.
        # a3 (rx) is ignored, may be blank
    def transmit(self,a2,a3,data=''): return None
        # put/get PTT (True = transmit mode)
        # a3 (tx) must be a transmitter code, e.g. TX
# VFO-related
# Argument 3 must be a VFO ID (e.g., VFOA|VFOB|...)
    def freq(self,a2,a3,data=''): return None
        # put/get VFO freq in Hz
    def memory_channel(self,a2,a3,data=''): return None
        # put/get current memory channel number in valid range
    def vfo_step(self,a2,a3,data=''): return None
        # put/get current VFO step size, Hz (e.g., 10, 100, etc.)
    def vfo_memory(self,a2,a3,data=''): return None
        # put/get indicated VFO to current memory channel.
        # memory_channel must be called first.
    def vfo_select(self,a2,a3,data=''): return None
        # Select current VFO
# Receiver
# Argument 3 must be a RX ID (e.g., MAIN|SUB|...)
    def af_gain(self,a2,a3,data=''): return None
        # put/get audio gain (0.0 - 1.0)
    def agc_mode(self,a2,a3,data=''): return None
        # put/get current agc mode (e.g., FAST|MEDIUM|...)
    def agc_user(self,a2,a3,data=''): return None
        # put/get user programmable agc parameters
        # time const (sec), hold time (sec), threshold (uV) - floating
    def atten(self,a2,a3,data=''): return None
        # put/get attenuator setting (by string, e.g., 'OFF','10dB', etc.)
    def bandpass_limits(self,a2,a3,data=''): return None
        # put/get bandpass in terms of lower/upper freq. edges
        # e.g. '0.0 2400.0' for SSB
    def bandpass(self,a2,a3,data=''): return None
        # put/get bandpass in terms of offset (pbt) and width
        # e.g. '200 2200' for bass-cut SSB
    def bandpass_standard(self,a2,a3,data=''): return None
        # set bandpass according to standard settings list
        # e.g. 'MEDIUM' for std SSB
    def noise_blank(self,a2,a3,data=''): return None
        # put/get noise blanker strength, float 0.0 - 1.0 (0 = off)
    def noise_reduce(self,a2,a3,data=''): return None
        # put/get noise reduction strength, float 0.0 - 1.0 (0 = off)
    def notch_auto(self,a2,a3,data=''): return None
        # put/get auto notch strength, float 0.0 - 1.0 (0 = off)
    def notch(self,a2,a3,data=''): return None
        # put/get notch settings (strength[0.0 - 1.0], center[Hz], width[Hz])
        # e.g.  '1.0 1000 200'
    def preamp(self,a2,a3,data=''): return None
        # put/get preamp on/off (boolean int)
    def rf_gain(self,a2,a3,data=''): return None
        # put/get RF gain, float 0.0 - 1.0
    def rit(self,a2,a3,data=''): return None
        # put/get receiver incremental tuning, float Hz
    def rx_ant(self,a2,a3,data=''): return None
        # put/get receiver antenna selection from list, e.g. 'ANT1'
    def rx_mode(self,a2,a3,data=''): return None
        # put/get receiver mode from list, e.g., 'CW', 'USB', etc.
    def squelch_level(self,a2,a3,data=''): return None
        # put/get squelch setting (0.0 - 1.0)  [ could be microvolts?]
    def squelch_open(self,a2,a3,data=''): return None
        # get only - squelch open true/false Bool int
    def strength(self,a2,a3,data=''): return None
        # get only - signal strength, calibrated in dB relative to S9
    def strength_raw(self,a2,a3,data=''): return None
        # get only - signal strength, rig-specific units (uncalibrated)
# Transmitter
# Argument 3 TX ID (TXA|...) - if there are multi-tx rigs - e.g.,
#   an Icom daisy-chain?
    def mic_gain(self,a2,a3,data=''): return None
        # put/get microphone gain, 0.0 - 1.0
    def mic_source(self,a2,a3,data=''): return None
        # put/get microphone selection from list, e.g. 'NORMAL'/'ALTERNATE'
    def power(self,a2,a3,data=''): return None
        # put/get output power (Watts), approximate
    def speech_proc(self,a2,a3,data=''): return None
        # put/get speech processor setting, float 0.0 - 1.0 (0 = off)
    def swr(self,a2,a3,data=''): return None
        # get only in tx mode - standing wave ratio (float, 1.0 - 9.99 or higher)
    def swr_raw(self,a2,a3,data=''): return None
        # get only in tx mode - Standing wave ratio, rig-specific units
    def tx_ant(self,a2,a3,data=''): return None
        # put/get select transmit antenna from list e.g., 'ANT1'
    def tx_mode(self,a2,a3,data=''): return None
        # put/get transmit mode from list 'USB', 'LSB' etc.
        # Note: often must be same as one of the receiver modes
    def xit(self,a2,a3,data=''): return None
        # put/get transmit incremental tuning, float Hz. (0 = off)
##
## End of Backend Class

