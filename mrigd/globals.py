#!/usr/bin/env python
#
# File: backend_globals.py
# Version: 1.0
#
# mrigd: global definitions
# Copyright (c) 2006-2008 Martin Ewing, 2016 German EA4GJA
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

# ** GLOBALS **

# Available rig backend dictionary.  
# Each backend is a Python module (imported
# into its own namespace), with a filename of <module_name>.py.
# Dictionary: {class name: (module, TextIdentifier), ...}

SUPPORTED_RIGS = { 
    'TT_orion':     ('tt_orion', 'Ten-Tec 565/566 (Orion) transceiver'),
    'TT_orion_v1':  ('tt_orion', 'Ten-Tec 565 with v1 firmware'),
    'TT_orion_v2':  ('tt_orion', 'Ten-Tec 566 and 565 with v2 firmware'),
    'TT_omni6':     ('tt_omni6', 'Ten-Tec 563/564 (Omni VI, VI Plus) transceiver'),
    'IC_765':       ('ic_765',   'Icom 765 HF transceiver'),
    'IC_r75':       ('ic_r75',   'Icom R75   communications receiver'),
    'IC_r8500':     ('ic_r8500', 'Icom R8500 communications receiver'),
    'YA_ft897d':    ('ya_ft897d', 'Yaesu FT-897D transceiver'),
    'Dummy':        ('dummy',    'Dummy backend for testing') 
    }

ACK     = 'OK'
NAK     = '? '  # Note space
NAK1    = '?'   # for error checks
T_TEST = 0
T_GET  = 1
T_PUT  = 2
TP_INVALID =    NAK+'Operation not defined.'
NO_WRITE =      NAK+'Write attempted to read-only function'
NO_READ =       NAK+'Read attempted to write-only function'
NOT_DEF =       NAK+'Operation not defined.'

NULL_TUP = ()

# Auxilliary routines

def in_range(rangelist,val):   # is val in rangelist[0],[1]?
    return ( val >= rangelist[0] ) and (val <= rangelist[1] )

def in_band(bands,f):      # Is f in a supported band?
    # bands is a list of tuples describing lower & upper band edges.
    for b in bands:
        if in_range(b,f):
            return True
    return False

def cnc(s1,s2):     # concatenate two strings, with blank separator
    return '%s %s' % (s1,s2)

def udict(*dicts):  # Make a union of dictionaries
    ans = {}
    for d in dicts:
        for q in d:
            ans[q] = d[q]
    return ans

def is_nak(x):      # argument has arbitrary type, is it a NAK message?
    if type(x)==type(NAK):  # i.e., is it a string type?
        if x[0] == NAK1:
            return True
    else:
        return False

