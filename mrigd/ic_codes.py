#!/usr/bin/env python
#
# File: ic_codes.py
# Version: 1.0
#
# mrigd: Icom CI-V codes
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

#
# NOTES:
# Icom CI-V reference:  Ekkehard Plicht, http://df4or.de/civ/
# Ten-Tec Omni VI and Omni VI Plus are based on 'Icom 735' commands.
#
# TO DO:
# - Check tables for accuracy
# - Implement more functions (with appropriate helper fns)
# - rationalize helper fn naming?
# - Consider what, if anything, to do about "1A" operations and
#   other specialized ops.


from globals import *

ICOM_ACK= "\xFB"    # OK byte (as 1-char string)
ICOM_NAK= "\xFA"    # NG byte
ICOM_EOC= "\xFD"    # End of command character
ICOM_EOC_int= 0xFD  # same, as integer

MAX_RD_DATA= 60     # limit size of received data from rig

# --------- BCD utilities ----------------
# pack 4 BCD digits (0-9) into a hex 2-tuple
# byte-reversed
def bcd4r(d1,d2,d3,d4): return (16*d3+d4, 16*d1+d2)
# non-reversed
def bcd4(d1,d2,d3,d4): return (16*d1+d2, 16*d3+d4)
# pack 2 BCD digits
def bcd2(d1,d2): return ( (16*d1+d2), )
# unpack 2 BCD digits to 2-tuple
def ubcd(c): return (ord(c)>>4, ord(c) & 0x0F)
# get a 4-bit nibble (digit) from a nibble string
def nib(s,i):
  k = ord(s[i/2])
  if i%2 == 0: k = k >> 4
  return k & 0xf

# ------- Icom communications routines ---------

def w_cmd0(ser,civ,tup):
    """
    w_cmd0 sends a "simple" command tuple, no further arguments.
    IN: arbitrary tuple of command bytes
    OUT: ACK/NAK
    """
    ser.flushInput()        # Flush serial input, to be sure.
    fullcmd = ( 0xFE, 0xFE, civ, 0xE0 ) + tup + (ICOM_EOC_int,)
    # source ad = 0xE0, dest ad = civ
    for i in fullcmd: 
        ser.write(chr(i))
    for i in fullcmd:
        a = ser.read()
        if a<>chr(i):
            return NAK+"w_cmd0: Command echo error"
    return ACK

def w_cmd(ser,civ,tup,tup2):
    """
    w_cmd takes an extra tuple to add to tup. (for consistency higher-
    level put_command call, where 4th arg can have different types)
    IN: two arbitrary tuples
    OUT: ACK/NAK
    """
    return w_cmd0(ser,civ,tup+tup2)

def get_response(ser):
    """
    get_response receives the response to a w_xxx command.  Data
    returned is a string of "binary" bytes - non-printable.
    IN: (none)
    OUT:  string of raw bytes read from rig or NAK;
    """
    preamble = ser.read(size=4)
    if not preamble[:3] == '\xFE\xFE\xE0':
        # check dest adr only, not source (which depends on civ)
        return NAK+'get_response: preamble error'
    a = ""
    for i in xrange(MAX_RD_DATA):
        c = ser.read(size=1)
        if c == ICOM_EOC: break
        a += c
#    print "len(a)=%d" % len(a),
#    for i in range(len(a)):
#    print "ord(a['%d'])=0x%x " % (i,ord(a[i])),
#    print
    return a    #### check: can start with a '?' --> error??

# ------- "helper functions" referenced in ICOM_CMD ------------

def w_level1(ser,civ,tup,val):  #     val = 0. - 1. floating
    """
    IN: tup cmd, floating value 0.0 - 1.0
    OUT: ACK/NAK
    """
    if val < 0. or val > 1.0:
        return NAK+'w_level1: Bad level range: %f' % val
    ival = int(255. * val)
    err = w_level2(ser,civ,tup,ival)
    return ACK

def w_level2(ser,civ,tup,ival): # ival 0 - 255 int
    """
    IN: tup cmd, int value 0 - 255
    OUT: ACK/NAK
    """
    if ival < 0 or ival > 255:
        return NAK+'w_level2: int level out of range.'
    s = "%04d" % ival
    err = w_cmd(ser,civ,tup,
            bcd4(int(s[0]),int(s[1]),int(s[2]),int(s[3]) ) )
    if get_response(ser) <> ICOM_ACK:
        return NAK+'w_level2: Bad response after Icom write.'
    return ACK

def r_level1(ser,civ,tup):
    """
    IN: tup
    OUT: float value 0.0 - 1.0 or ACK/NAK
    """
    data = r_level2(ser,civ,tup)
    if is_nak(data): return data
    return float(data)/255.0   # range 0.0 - 1.0

def r_level2(ser,civ,tup):
    """
    IN: tup
    OUT: int value 0 - 255 or ACK/NAK
    """
    err = w_cmd0(ser,civ,tup)        # err check?
    if is_nak(err): return NAK+'r_level2: w_cmd0 problem'
    v = get_response(ser)      # err check?
    if is_nak(v): return v
    try:
        u1 = ubcd(v[2])[1]
        ux = ubcd(v[3])
        ansi = u1*100 + ux[0]*10 + ux[1] # 000-255 bcd
    except IndexError: return NAK+'r_level2: index error'
    return ansi                # range 0 - 255

def r_data(ser,civ,tup):        # Send a command, get response data as string
    """
    IN: tup
    OUT: raw response bytes or ACK/NAK
    """
    err = w_cmd0(ser,civ,tup)
    if is_nak(err): return err
    return get_response(ser)

def w_byte(ser,civ,tup,byte):
    """
    IN: tup, raw command byte
    OUT: ACK/NAK
    """
    err = w_cmd(ser,civ,tup,(byte,))
    if is_nak(err): return err
    if not get_response(ser)[0] == ICOM_ACK:
        return NAK+'w_byte: Bad response after Icom write.'
    return ACK

def r_freq(ser,civ,tup):
    """
    IN: tup
    OUT: float frequency, Hz or ACK/NAK
    """
    err = w_cmd0(ser,civ,tup)
    if is_nak(err): return err
    ans = get_response(ser)
    if is_nak(ans): return ans
    f=0
    for k in [10,11,8,9,6,7,4,5,2,3]: 
        f=10*f + nib(ans,k)
    return float(f)

def r_freq_off(ser,civ,tup):        # works on Omni6 - verify for others
    """
    IN: tup
    OUT: float frequency offset, Hz or ACK/NAK
    """                  
    err = w_cmd0(ser,civ,tup)
    if is_nak(err): return err
    ans = get_response(ser)
    if is_nak(ans): return ans
    f=0
    for k in [2,3,0,1]: 
        f=10*f + nib(ans,k)
    f *= 10.
    if f >= 90000.:                 # 9's complement for negatives
        f = f - 100000.
    return float(f)

def w_freq(ser,civ,tup,freq):
    """
    IN: tup, float frequency Hz
    OUT: ACK/NAK
    """
    fs = "%010d" % int(freq)
    out  = bcd4(int(fs[8]),int(fs[9]),int(fs[6]),int(fs[7]))
    out += bcd4(int(fs[4]),int(fs[5]),int(fs[2]),int(fs[3]))
    out += bcd2(int(fs[0]),int(fs[1]))
    err = w_cmd(ser,civ,tup,out)
    if is_nak(err): return err
    if get_response(ser)[0] <> ICOM_ACK:
        return NAK+'w_freq: command not accepted by rig.'
    return ACK

def w_freq_off(ser,civ,tup,freq):   # Works for Omni6, must test for others
    """
    IN: tup, float frequency offset Hz
    OUT: ACK/NAK
    """
    ifreq = int(freq)
    if ifreq < 0:
        ifreq = 100000 + ifreq      # 9's complement
    fs = "%05d" % ifreq
    out = bcd4(int(fs[2]),int(fs[3]),int(fs[0]),int(fs[1]))
    err = w_cmd(ser,civ,tup,out)
    if is_nak(err): return err
    if get_response(ser)[0] <> ICOM_ACK:
        return NAK+'w_freq_off: command not accepted by rig.'
    return ACK

def noop(*parms):                 # Any parameter noop
    """
    IN: any
    OUT: None
    """
    return None

# Dictionary to provide default CIV address for each Icom rig.
# Some rigs allow the address to be changed.
# This list defines all possible rigs that can be supported, although many
# will not be supported unless there is particular interest.
# Note: IC-735 and Omni6 both use default setting 0x04.

CIVAD = { '271':0x20, '275':0x10, '375':0x12, '471':0x22, '475':0x14, '575':0x16,
    '7000':0x70, '703':0x68, '706':0x48, '706MKII':0x4E, '706MKIIG':0x58, '707':0x3E,
    '718':0x5E, '725':0x28, '726':0x30, '728':0x38, '729':0x3A, '735':0x04, '736':0x40,
    '737':0x3C, '738':0x44, '746PRO':0x66, '746':0x56, '751A':0x1C, '756':0x50,
    '756PRO':0x5C, '756PROII':0x64, '756PROIII':0x6E, '761':0x1E, '765':0x2C, '775':0x46,
    '78':0x62, '7800':0x6A, '781':0x26, '820':0x42, '821':0x4C, '910':0x60, '7700':0x74,
    '970':0x2E, '1271':0x24, '1275':0x18, 'R10':0x52, 'R20':0x6C, 'R71':0x1A, 'R72':0x32,
    'R75':0x5A, 'R7000':0x08, 'R7100':0x34, 'R8500':0x4A, 'R9000':0x2A, 'R9500':0x72,
    'OMNI6':0x04 }

MODE = { 'LSB':0x00, 'USB':0x01, 'AM':0x02, 'CW':0x03, 'RTTY':0x04, 'FM':0x05,
    'WFM':0x06, 'CW-R':0x07, 'RTTY-R':0x08, 'S-AM':0x11, 'PSK':0x12, 'PSK-R':0x12,
    'SSB':0x0500 } # SSB is for R7000 only; 0x04=FM on IC-910
PASS = { 'WIDE':0x01, 'NORM':0x02, 'NARR':0x03 }

# Calculate inverse dictionaries, too:  CIVADr, MODEr and PASSr
CIVADr = {}
for x in CIVAD: CIVADr[CIVAD[x]] = x
MODEr = {}
for x in MODE: MODEr[MODE[x]] = x
PASSr = {}
for x in PASS: PASSr[PASS[x]] = x

BN=     0   # Binary tuple spec
FN=     1   # Function spec
AS=     2   # Ascii text descriptor
CAP=    3   # Capability List of rigs supporting this command

# The ICOM_CMD dictionary is effectively a separate namespace for the command names.
# Fields:
#  BN (0) - Hardware hex command tuple (length 1 or 2?)
#  FN (1) - Function for data transfer (read or write), if any.
#           "noop" generally means a not yet implemented operation.
#  AS (2) - Text description of command

ICOM_CMD = {
    'TR_FREQ':      ((0x00,),       w_freq, 'Transfer operating freq. data (no reply)'),
    'TR_MODE':      ((0x01,),       noop,   'Transfer operating mode (no reply)'),
    'RD_FRQ_EDGES': ((0x02,),       noop,   'Read lower/upper freqs.'),
    'RD_OP_FRQ':    ((0x03,),       r_freq, 'Read operating freq.'),
    'RD_OP_MODE':   ((0x04,),       r_data, 'Read operating mode & passband'),
    'SET_FREQ':     ((0x05,),       w_freq, 'Write operating freq.'),
    'SET_MODE':     ((0x06,),       w_cmd,  'Set operating mode & passband (generic)'),

# 0x07
    'VFO_MODE':     ((0x07,),       noop,   'Write VFO mode (generic)'),
    'VFO_A':        ((0x07, 0x00),  w_cmd,   'Select VFO A'),
    'VFO_B':        ((0x07, 0x01),  w_cmd,   'Select VFO B'),
    'VFO_B2A':      ((0x07, 0xA0),  noop,   'VFO A = VFO B (A <- B?)'),
    'VFO_XAB':      ((0x07, 0xB0),  noop,   'Exchange VFO A/B or MAIN/SUB'),
    'VFO_SUB2MAIN': ((0x07, 0xB1),  noop,   'VFO SUB -> MAIN'),
    'VFO_DWTCHOFF': ((0x07, 0xC0),  noop,   'Dual watch off'),
    'VFO_DWTCHON':  ((0x07, 0xC1),  noop,   'Dual watch on'),
    'VFO_MAINBAND': ((0x07, 0xD0),  noop,   'Select Main band'),
    'VFO_SUBBAND':  ((0x07, 0xD1),  noop,   'Select Sub band'),
    'VFO_FRONTW':   ((0x07, 0xE0),  noop,   'Select front window'),

# 0x08
    'SEL_CHAN':     ((0x08,),       noop,   'Select memory channel +mc'),
    'SEL_BANK':     ((0x08, 0xA0),  noop,   'Select memory bank +bn'),

# 0x09 - 0x0D
    'MEM_WRITE':    ((0x09,),       noop,   'Memory write'),
    'MEM2VFO':      ((0x0A,),       noop,   'Memory to VFO'),
    'MEM_CLR':      ((0x0B,),       noop,   'Memory clear'),
    'RD_OFF_FREQ':  ((0x0C,),       r_freq_off,   'Read duplex offset freq.'),
    'SET_OFF_FREQ': ((0x0D,),       w_freq_off,   'Write duplex offset freq.'),

# 0x0E
    'SCN_STOP':         ((0x0E, 0x00),  noop,   'Stop scan'),
    'SCN_PROGM_STRT':   ((0x0E, 0x01),  noop,   'Start programmed scan/ memory scan'),
    'SCN_PROG_STRT':    ((0x0E, 0x02),  noop,   'Start programmed scan -only scan group 0'),
    'SCN_DF_STRT':      ((0x0E, 0x03),  noop,   'Start delta-f scan'),
    'SCN_AUTO_W_STRT':  ((0x0E, 0x04),  noop,   'Start auto memory-write scan -only scan group 0'),
    'SCN_FINEP_STRT':   ((0x0E, 0x12),  noop,   'Start fine programmed scan'),
    'SCN_FINEM_STRT':   ((0x0E, 0x13),  noop,   'Start fine delta-f scan'),
    'SCN_MEM_STRT':     ((0x0E, 0x22),  noop,   'Start memory scan after bank or mode cmd'),
    'SCN_SEL_STRT':     ((0x0E, 0x23),  noop,   'Start selected mode memory scan after bank or mode cmd'),
    'SCN_MODE_STRT':    ((0x0E, 0x24),  noop,   'after bank or mode cmd'),
    'SCN_PRIO':         ((0x0E, 0x42),  noop,   'Start priority / window scan'),
    'SCN_UNFIXCTR':     ((0x0E, 0xA0),  noop,   'Unfix center freq. for delta-f scan'),
    'SCN_FIXCTR':       ((0x0E, 0xAA),  noop,   'Fix center freq. for delta-f scan'),
    'SCN_DF2R5':        ((0x0E, 0xA1),  noop,   'Set delta-f to +/- 2.5 kHz'),
    'SCN_DF5':          ((0x0E, 0xA2),  noop,   'Set delta-f to +/- 5 kHz'),
    'SCN_DF10':         ((0x0E, 0xA3),  noop,   'Set delta-f to +/- 10 kHz'),
    'SCN_DF20':         ((0x0E, 0xA4),  noop,   'Set delta-f to +/- 20 kHz'),
    'SCN_DF50':         ((0x0E, 0xA5),  noop,   'Set delta-f to +/- 50 kHz'),
    'SCN_DF500':        ((0x0E, 0xA6),  noop,   'Set delta-f to +/- 100 kHz'),
    'SCN_DF1000':       ((0x0E, 0xA7),  noop,   'Set delta-f to +/- 1000 kHz'),
    'SCN_INCL':         ((0x0E, 0xB0),  noop,   'Include memory for scan (*)'),
    'SCN_EXCL':         ((0x0E, 0xB1),  noop,   'Exclude memory from scan'),
    'VSC_OFF':          ((0x0E, 0xC0),  noop,   'VSC off'),
    'VSC_ON':           ((0x0E, 0xC1),  noop,   'VSC on'),
    'SCN_RES_INF':      ((0x0E, 0xD0),  noop,   'Scan resume indefinite (*)'),
    'SCN_RES_OFF':      ((0x0E, 0xD1),  noop,   'Scan resume off'),
    'SCN_RES_B':        ((0x0E, 0xD2),  noop,   'Scan resume B'),
    'SCN_RES_A':        ((0x0E, 0xD3),  noop,   'Scan resume A (*)'),

# 0x0F
    'SPLT_OFF':     ((0x0F, 0x00),  noop,   'Cancel split freq. operation'),
    'SPLT_ON':      ((0x0F, 0x01),  noop,   'Start split freq. operation'),
    'DUPL_OFF':     ((0x0F, 0x10),  noop,   'Cancel duplex operation'),
    'DUPL_MINUS':   ((0x0F, 0x11),  noop,   'Select duplex - operation'),
    'DUPL_PLUS':    ((0x0F, 0x12),  noop,   'Select duplex + operation'),

# 0x10
    'TSTEP':    ((0x10,),       w_byte, 'Tuning step - calculated'),
#    'TSMIN':    ((0x10, 0x00),  noop,   'Tuning step - minimum'),
#    'TS1':      ((0x10, 0x01),  noop,   'Tuning step 1'),
#    'TS2':      ((0x10, 0x02),  noop,   'Tuning step 2'),
#    'TS3':      ((0x10, 0x03),  noop,   'Tuning step 3'),
#    'TS4':      ((0x10, 0x04),  noop,   'Tuning step 4'),
#    'TS5':      ((0x10, 0x05),  noop,   'Tuning step 5'),
#    'TS6':      ((0x10, 0x06),  noop,   'Tuning step 6'),
#    'TS7':      ((0x10, 0x07),  noop,   'Tuning step 7'),
#    'TS8':      ((0x10, 0x08),  noop,   'Tuning step 8'),
#    'TS9':      ((0x10, 0x09),  noop,   'Tuning step 9'),
#    'TS10':     ((0x10, 0x10),  noop,   'Tuning step 10'),
#    'TS11':     ((0x10, 0x11),  noop,   'Tuning step 11'),
#    'TS12':     ((0x10, 0x12),  noop,   'Tuning step 12'),
#    'TS13':     ((0x10, 0x13),  noop,   'Tuning step 13'),

# 0x11
    'ATTN':     ((0x11,),       w_cmd, 'Attenuator, calculated'),
    'ATTN_OFF': ((0x11, 0x00),  noop,   'Attenuator off'),
#    'ATTN_3':   ((0x11, 0x01),  noop,   'Atten 3dB'),
#    'ATTN_6':   ((0x11, 0x02),  noop,   'Atten 6dB'),
#    'ATTN_9':   ((0x11, 0x03),  noop,   'Atten 9dB'),
#    'ATTN_12':  ((0x11, 0x04),  noop,   'Atten 12dB'),
#    'ATTN_15':  ((0x11, 0x05),  noop,   'Atten 15dB'),
#    'ATTN_6':   ((0x11, 0x06),  noop,   'Atten 6dB'),
#    'ATTN_21':  ((0x11, 0x07),  noop,   'Atten 21dB'),
#    'ATTN_10':  ((0x11, 0x10),  noop,   'Atten 10dB'),
#    'ATTN_12':  ((0x11, 0x12),  noop,   'Atten 12dB'),
#    'ATTN_18':  ((0x11, 0x18),  noop,   'Atten 18dB'),
#    'ATTN_20':  ((0x11, 0x20),  noop,   'Atten 20dB'),
#    'ATTN_30':  ((0x11, 0x30),  noop,   'Atten 30dB'),

# 0x12
    'ANT_STAT':         ((0x12,),       w_cmd,  'Read current antenna selection'),
#    'ANT_1':            ((0x12, 0x00),  noop,   'Select ant. 1 (*)'),
#    'ANT_1_RXA_OFF':    ((0x12, 0x00, 0x00),    noop,   'Sel. ant. 1, RXA off'),
#    'ANT_1_RXA_ON':     ((0x12, 0x00, 0x01),    noop,   'Sel. ant. 1, RXA on'),
#    'ANT_2':            ((0x12, 0x01),  noop,   'Select ant. 2 (*)'),
#    'ANT_2_RXA_OFF':    ((0x12, 0x01, 0x00),    noop,   'Sel. ant. 2, RXA off'),
#    'ANT_2_RXA_ON':     ((0x12, 0x01, 0x01),    noop,   'Sel. ant. 2, RXA on'),
#    'ANT_2':            ((0x12, 0x02),  noop,   'Select ant. 2'),
#    'ANT_3_RXA_OFF':    ((0x12, 0x02, 0x00),    noop,   'Sel. ant. 3, RXA off'),
#    'ANT_3_RXA_ON':     ((0x12, 0x02, 0x01),    noop,   'Sel. ant. 3, RXA on'),
#    'ANT_4_RXA_OFF':    ((0x12, 0x03, 0x00),    noop,   'Sel. ant. 4, RXA off'),
#    'ANT_4_RXA_ON':     ((0x12, 0x03, 0x01),    noop,   'Sel. ant. 4, RXA on'),

# 0x13
    'ANN_ALL':  ((0x13, 0x00),  noop,   'Announce all data'),
    'ANN_FREQ': ((0x13, 0x01),  noop,   'Announce freq. and S-meter'),
    'ANN_RX':   ((0x13, 0x02),  noop,   'Announce Rx mode'),

# 0x14
    'SET_LVL':          ((0x14,),       noop,       'Set AF, RF, SQL gains (*)'),   # R9000, R7100 ??
    'SET_AF':           ((0x14, 0x01),  w_level1,    'Set AF level'),
    'SET_RF':           ((0x14, 0x02),  w_level1,    'Set RF level'),
    'SET_SQL':          ((0x14, 0x03),  w_level1,    'Set SQL level'),
    'SET_IF_SHIFT':     ((0x14, 0x04),  w_level1,    'Set IF shift'),    # R8500
    'SET_APF':          ((0x14, 0x05),  w_level1,    'Set APF level'),   # R8500, 7800
    'SET_NR':           ((0x14, 0x06),  w_level1,    'Set NR level'),
    'SET_PBT_IN':       ((0x14, 0x07),  w_level1,    'Set Twin PBT (inner)'),
    'SET_PBT_OUT':      ((0x14, 0x08),  w_level1,    'Set Twin PBT (outer)'),
    'SET_CW_PITCH':     ((0x14, 0x09),  w_level2,    'Set CW Pitch'),
    'SET_RF_POWER':     ((0x14, 0x0A),  w_level2,    'Set RF power'),
    'SET_MIC_GAIN':     ((0x14, 0x0B),  w_level1,    'Set microphone gain'),
    'SET_KEY_SPEED':    ((0x14, 0x0C),  w_level2,    'Set keyer speed'),
    'SET_NOTCH_FREQ':   ((0x14, 0x0D),  w_level2,    'Set notch freq.'),
    'SET_COMPRESS':     ((0x14, 0x0E),  w_level1,    'Set compressor level'),
    'SET_BK_DEL':       ((0x14, 0x0F),  w_level2,    'Set break-in delay'),
    'SET_BALANCE':      ((0x14, 0x10),  w_level1,    'Set balance (dual watch)'),
    'SET_AGC':          ((0x14, 0x11),  w_level1,    'Set AGC'),
    'SET_NB':           ((0x14, 0x12),  w_level1,    'Set NB level'),
    'SET_DIGI_SEL':     ((0x14, 0x13),  w_level1,    'DIGI-SEL setting'),
    'SET_DRIVE':        ((0x14, 0x14),  w_level1,    'Set DRIVE'),
    'SET_MONITOR':      ((0x14, 0x15),  w_level1,    'Set monitor level'),
    'SET_VOX':          ((0x14, 0x16),  w_level1,    'Set VOX gain'),
    'SET_ANTI_VOX':     ((0x14, 0x17),  w_level1,    'Set Anti-VOX level'),
    'SET_LCD_CONTR':    ((0x14, 0x18),  w_level1,    'Set LCD contrast'),
    'SET_LCD_BRITE':    ((0x14, 0x19),  w_level1,    'Set LCD brightness'),
    'SET_NOTCH_2':      ((0x14, 0x1A),  w_level2,    'Set Notch filter 2'),  # 7000

# None of the GET_ series works on R8500
    'GET_AF':           ((0x14, 0x01),  r_level1,    'Get AF level'),
    'GET_RF':           ((0x14, 0x02),  r_level1,    'Get RF level'),
    'GET_SQL':          ((0x14, 0x03),  r_level1,    'Get SQL level'),
    'GET_IF_SHIFT':     ((0x14, 0x04),  r_level1,    'Get IF shift'),
    'GET_APF':          ((0x14, 0x05),  r_level1,    'Get APF level'),
    'GET_NR':           ((0x14, 0x06),  r_level1,    'Get NR level'),
    'GET_PBT_IN':       ((0x14, 0x07),  r_level1,    'Get Twin PBT (inner)'),
    'GET_PBT_OUT':      ((0x14, 0x08),  r_level1,    'Get Twin PBT (outer)'),
    'GET_CW_PITCH':     ((0x14, 0x09),  r_level1,    'Get CW Pitch'),
    'GET_RF_POWER':     ((0x14, 0x0A),  r_level1,    'Get RF power'),
    'GET_MIC_GAIN':     ((0x14, 0x0B),  r_level1,    'Get microphone gain'),
    'GET_KEY_SPEED':    ((0x14, 0x0C),  r_level1,    'Get keyer speed'),
    'GET_NOTCH_FREQ':   ((0x14, 0x0D),  r_level1,    'Get notch freq.'),
    'GET_COMPRESS':     ((0x14, 0x0E),  r_level1,    'Get compressor level'),
    'GET_BK_DEL':       ((0x14, 0x0F),  r_level1,    'Get break-in delay'),
    'GET_BALANCE':      ((0x14, 0x10),  r_level1,    'Get balance (dual watch)'),
    'GET_AGC':          ((0x14, 0x11),  r_level1,    'Get AGC'),
    'GET_NB':           ((0x14, 0x12),  r_level1,    'Get NB level'),
    'GET_DIGI_SEL':     ((0x14, 0x13),  r_level1,    'DIGI-SEL setting'),
    'GET_DRIVE':        ((0x14, 0x14),  r_level1,    'Get DRIVE'),
    'GET_MONITOR':      ((0x14, 0x15),  r_level1,    'Get monitor level'),
    'GET_VOX':          ((0x14, 0x16),  r_level1,    'Get VOX gain'),
    'GET_ANTI_VOX':     ((0x14, 0x17),  r_level1,    'Get Anti-VOX level'),
    'GET_LCD_CONTR':    ((0x14, 0x18),  r_level1,    'Get LCD contrast'),
    'GET_LCD_BRITE':    ((0x14, 0x19),  r_level1,    'Get LCD brightness'),
    'GET_NOTCH_2':      ((0x14, 0x20),  r_level1,    'Get Notch filter 2'),

# 0x15
    'RD_SQL_STATUS':    ((0x15, 0x01),  r_data,  'Read Squelch status'),
    'RD_STRENGTH':      ((0x15, 0x02),  r_level1, 'Read signal strength'),
    'RD_RF_PWR':        ((0x15, 0x11),  r_data, 'Read RF power'),
    'RD_SWR':           ((0x15, 0x12),  r_data, 'Read SWR meter'),
    'RD_ALC':           ((0x15, 0x13),  r_data, 'Read ALC meter'),
    'RD_COMP':          ((0x15, 0x14),  r_data, 'Read COMP meter'),
    'RD_VD':            ((0x15, 0x15),  r_data, 'Read drain voltage'),
    'RD_ID':            ((0x15, 0x16),  r_data, 'Read drain current'),

# 0x16  Some of these also support GET_ operations, but only on some models.
# We will only support the SET operations at this time.
    'WR_PREAMP':    ((0x16, 0x02),  w_byte, 'Preamp setting: 0,1, or 2'),
    'SET_AGC_SLOW': ((0x16, 0x10),  w_cmd,  'Auto gain control slow'), # R8500
    'SET_AGC_FAST': ((0x16, 0x11),  w_cmd,  'Auto gain control fast'), # R8500
    'SET_AGC':      ((0x16, 0x12),  w_byte, 'Auto gain control off/fast/med/slow: 0,1,2,3'), # not R8500
    'SET_NB_OFF':   ((0x16, 0x20),  noop,   'Set Noise Blanker off'),
    'SET_NB_ON':    ((0x16, 0x21),  noop,   'Set Noise Blanker on'),
    'SET_NB':       ((0x16, 0x22),  w_byte, 'Noise blanker off/on: 0-1'),
    'SET_APF_OFF':  ((0x16, 0x30),  noop,   'Audio Peak Filter off'),
    'SET_APF_ON':   ((0x16, 0x31),  noop,   'Audio Peak Filter on'),
    'SET_APF':      ((0x16, 0x32),  w_byte, 'Audio Peak Filter setting: 0-1'),
    'SET_NR':       ((0x16, 0x40),  w_byte, 'Noise Reduction off/on: 0-1 (DSP)'),
    'SET_AN':       ((0x16, 0x41),  w_byte, 'Auto notch off/on: 0-1 (DSP)'),
    'SET_RPT_TONE': ((0x16, 0x42),  w_byte, 'Repeater tone off/on: 0-1'),
    'SET_TSQL':     ((0x16, 0x43),  w_byte, 'Tone Squelch off/on: 0-1'),
    'SET_COMP':     ((0x16, 0x44),  w_byte, 'Compression off/on: 0-1'),
    'SET_MONI':     ((0x16, 0x45),  w_byte, 'Monitor off/on: 0-1'),
    'SET_VOX':      ((0x16, 0x46),  w_byte, 'VOX off/on: 0-1'),
    'SET_BRKIN':    ((0x16, 0x47),  w_byte, 'Set break-in off/semi/full: 0,1,2'),
    'SET_NOTCH':    ((0x16, 0x48),  w_byte, 'Set manual notch off/on: 0-1'),
    'SET_RTTY_FILT':((0x16, 0x49),  w_byte, 'Set RTTY filter off/on: 0-1'),
    'SET_AFC':      ((0x16, 0x4A),  w_byte, 'Set Auto Freq Control off/on: 0-1'),
    'SET_DTCS':     ((0x16, 0x4B),  w_byte, 'Set Digital Tone Squelch off/on: 0-1'),
    'SET_VSC':      ((0x16, 0x4C),  w_byte, 'Set VSC (voice squelch) off/on: 0-1'),
    'SET_AGC_MAN':  ((0x16, 0x4D),  w_byte, 'Set manual AGC off/on: 0-1'),
    'SET_DIGISEL':  ((0x16, 0x4E),  w_byte, 'Set DIGI-SEL off/on: 0-1'),
    'SET_TPF':      ((0x16, 0x4F),  w_byte, 'Set Twin peak filter off/on: 0-1'),
    'SET_DIAL_LOCK':((0x16, 0x50),  w_byte, 'Set dial lock off/on: 0-1'),
    'SET_MAN_NOTCH':((0x16, 0x51),  w_byte, 'Set manual notch off/on: 0-1'),
    'SET_XMT_OMNI6':((0x16,),       w_cmd,  'Set transmit: 1-2, Omni6'),

# 0x17
    'SEND_CW':      ((0x17,),       noop,   'Send CW characters'),  # 775DSP

# 0x18
    'PWR_OFF':      ((0x18, 0x00),  w_cmd,   'Receiver pwr off (*)'), # R75, R8500
    'PWR_ON':       ((0x18, 0x01),  w_cmd,   'Receiver pwr on (*)'), # R75, R8500

# 0x19
    'GET_ID':       ((0x19, 0x00),  r_data, 'Read *default* CI-V addr'),

# 0x1A
#    'MISC0':        ((0x1A, 0x00),  noop,   'model dependent'),

# 0x1B
    'SET_TONE_FREQ':    ((0x1B, 0x01), noop,  'Set freq for tone squelch'),
    'SET_DTCS_CODE':    ((0x1B, 0x02), noop,  'Set DTCS code/polarity'), # 746PRO, 7000
    'GET_TONE_FREQ':    ((0x1B, 0x01), r_data,  'Get freq for tone squelch'),
    'GET_DTCS_CODE':    ((0x1B, 0x02), r_data,  'Get DTCS code/polarity'), # 746PRO, 7000

# 0x1C
    'SET_XMT_ON':       ((0x1C,0x00),   w_cmd, 'Set transmit off/on: 0/1'),
    'SET_ANT_TUNER':    ((0x1C, 0x01),  w_byte, 'Set ant. tuner off/on/trigger: 0, 1, 2'), # 746PRO, 756PRO3, 7800, 7000
    
    'GET_XMT_ON':       ((0x1c, 0x00),  r_data, 'Get transmit off/on: 0/1')
}

