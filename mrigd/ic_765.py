#!/usr/bin/env python
#
# File: ic_765.py
# Version: 1.0
#
# mrigd: Icom IC-765 class definition
# Copyright (c) 2008 Martin Ewing
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

# This is the subclass of Icom_trx to handle the IC_IC765 receiver
#
# NOTES:

# TO DO:
# 


import sys, serial, time
from icom import *

IC765_VFO_LIST          = ['VFOA', 'VFOB']
IC765_RX_LIST           = ['MAIN','CONTROL']
IC765_TX_LIST           = ['TX']
IC765_BACKEND_ID        = "Icom IC765 Backend v. 0.01"
IC765_ADDRESS           = CIVAD['765']  # std address for the IC765 = 0x2c

# Supported frequency bands - valid VFO settings, Hz
#USA:
IC765_BANDS_0 = [ (30.e3, 29.99999e6) ]         # Receive
IC765_BANDS = { 'VFOA': IC765_BANDS_0, 'VFOB': IC765_BANDS_0 }
IC765_BANDS_TX_0 = [                            # Transmit (from Hamlib)
    (1.8e6,1.999999e6), (3.4e6,4.099999e6), (6.9e6,7.49999e6),
    (9.9e6,10.49999e6), (17.9e6,18.49999e6), (20.9e6,21.49999e6),
    (24.4e6,25.09999e6), (28.e6,29.99999e6) ]
IC765_BANDS_TX = { 'VFOA': IC765_BANDS_TX_0, 'VFOB': IC765_BANDS_TX_0 }

# Reverse mode map (note change to hex)
IC765_MODE_MAPr       = { 0x01:'LSB', 0x11:'USB',
                        0x21:'AM', 0x22:'AMN', 0x31:'CW', 0x32:'CWN', 
                        0x42:'RTTYN', 0x41:'RTTY', 0x51:'FM'
                        }
# Calculate the forward-going mode map from the reverse.
IC765_MODE_MAP      = {}
for x in IC765_MODE_MAPr:
    IC765_MODE_MAP[IC765_MODE_MAPr[x]] = x

# Capabilities for this rig
#IC765_CAPABILITIES = IC_COMMON_CAPABILITIES | \
#    set(['VFO_A', 'VFO_B', 'VFO_B2A', 'MEM_CLR', 'SCN_STOP', 
#    'SCN_PROGM_START', 'SPLIT_OFF', 'SPLIT_ON'])
IC765_CAPABILITIES = udict( IC_COMMON_CAPABILITIES, 
    { 'vfo_select':'w', 'memory_channel':'rw', 'vfo_memory':'rw'} )
# Some day could support vfob2a, mem_clear, scan_start/stop, Split on/off

GETPUT = ['GET', 'PUT']

# The IC-765 defines an older transceiver class w/o T/R control, etc.
# They implement the 0x07, 0x08, 0x09 commands (mostly)
# Other similar models: 725-729, 735, 737, ???

class IC_765(Icom):
    def __init__(self):
        Icom.__init__(self)
        self.civ_address =  IC765_ADDRESS
        self.bands =        IC765_BANDS
        self.backend_id =   IC765_BACKEND_ID
        self.vfo_list=      IC765_VFO_LIST
        self.bands =        IC765_BANDS
        self.bands_tx =     IC765_BANDS_TX
        self.rx_list =      IC765_RX_LIST
        self.tx_list =      IC765_TX_LIST
        self.mode_list =    IC765_MODE_MAP.keys()
        self.mode_map =     IC765_MODE_MAP
        self.mode_map_r =   IC765_MODE_MAPr
        self.capabilities = IC765_CAPABILITIES
        return

#    def info(self,tp,rx='',data=''): 
#        if tp == T_GET:
#            return Backend.info(self,T_GET,'','')
#        elif tp == T_TEST: return ACK   # Yes, the method is defined.
#        else: return NOT_DEF

if __name__ == "__main__":
# This is the place to test the subclass and ic module routines.
# Not executed if this file is invoked by another Python routine.

    rig = IC_765()
#    print rig.info(T_GET)
    print   "init:",        rig.init(T_PUT, data='/dev/ham.8500 1200')
    print   "info:",        rig.info(T_GET)
#    print                   rig.freq(T_PUT,'VFOA','14100e3')
    print   "freq=",        rig.freq(T_GET,'VFOA')
    print   "freq set:",    rig.freq(T_PUT,'VFOA','14123456')
    print   "freq=",        rig.freq(T_GET,'VFOA')
    print   "mode=",        rig.rx_mode(T_GET,'MAIN')
#    print                   rig.rx_mode(T_PUT,'MAIN','CW')
#    print                   rig.select_vfo(T_PUT,'VFOB')
#    print                   rig.rit(T_PUT,'MAIN', '130')
#    time.sleep(0.1)
#    print                   rig.rit(T_GET,'MAIN')
#    print                   rig.rit(T_PUT,'MAIN','7930')
    

