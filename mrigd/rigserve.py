#!/usr/bin/env python
#
# File: rigserve.py
# Version: 1.0
#
# mrigd: rigserve server
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


import sys, socket, time, os
import select

# v 0.1 initial release, 11/16/2006
# v 0.2 changes
#   Changed python calls with 'tp' argument for test/put/get select.
#   Clarified do_test function
#   Eliminate common.py
# v 0.21 changes
#   Clean up global defs.
#   Minor changes to test sequence
# v 0.22
#   Add cgi example

# User can define an arbitrary identifier string for a particular
# rig.  There can be multiple rigs of the same type with unique
# identifiers.

IDENT='rigserve-mrigd 1.0: 04/2008 AA6E, 02/2016 EA4GJA'
from globals import *

from service import *

# 'globals' includes SUPPORTED_RIGS structure and other common info.

# Dynamically built dictionaries of OPENED RIG namespaces (nameSp) and 
# BACKEND INSTANCES (backEnd).  The key is the rig identifier.
# The rig_type or module name (file name) must be the same as the 
# Python Class for the backend.  E.g.  TT_orion (.py) & class TT_orion

nameSp      = {}    # identifier:module namespace
backEnd     = {}    # identifier:backend object
openDrivers = []    # handles of opened rigs
openRigType = {}    # names of instantiated backend subclasses

# Services dictionary

services_dict = {"dummy": Service("rigserve")}

# Who can connect to us:  If null (''), allow anyone. Use 'localhost'
# to allow only connections from the same machine.
# Be careful before you open up your firewalls to telnet traffic!
# Eventually, we could support SSH connections.  Meanwhile, consider
# using SSH port tunneling for secure Internet access.
# NOTE: Connections to "::1" (IPv6 style) may not succeed.  Try 127.0.0.1
#       instead.
ALLOWED_IP = '127.0.0.1'     # Allow connect from anyone (subject to firewalls)
PORT    =14652      # Pick a memorable port number to listen on.
# ** End of Globals **     

# The "do_" routines are carrying out high-level commands coming in
# on the socket interface.

# input: "rig_id backend_id"
# The rig_id is an arbitrary name specified by the user and used as
# the key in the nameSp and backEnd dictionaries.
# Check if backend_id 'x' is in the list of supported rigs.  If so, import
# its module (as named in SUPPORTED_RIGS[x][0]) as namespace nameSp[rig_id].
# Then, execute/evaluate the class instantiation.
# Note: There may be several backends defined in a module.

def do_open(s):
    global nameSp, backEnd, openDrivers, openRigType
    split = s.split(None,1)
    if len(split) != 2:
        return NAK + "open needs two args."
    h = split[0]
    rig_type = split[1]
    # Do we know about the rig type?
    if not SUPPORTED_RIGS.has_key(rig_type):
        return NAK+"Rig type not found: %s" % rig_type
    # Import the module using function call, module namespace goes
    # into nameSp
    nameSp[h] = __import__(SUPPORTED_RIGS[rig_type][0])
    # Construct a python function name to be eval'd.  This will be
    # the backend class name, e.g. '<namespace>.TT_orion()'. There may
    # be a way to do this without the eval??
    cmd = "nameSp[h].%s(h)" % rig_type
    backEnd[h] = eval( cmd )            # Creates the backend object
    openDrivers += [ h ]                # keep track of opened rig IDs
    openRigType[h] = rig_type           # .. and backend names
    print '(Opening rig_type = %s)' % rig_type
    return SUPPORTED_RIGS[rig_type][1]  # return the text rig description

# input: "rig_id ..."
# Forget this particular rig_id, namespace, class instance.

def do_close(s):
    global nameSp, backEnd, openDrivers
    fields = s.split(None,1)    # check number of fields, returns list
    h = fields[0]
    if h in openDrivers:
        del backEnd[h]              # delete backend for garbage coll. ?
        del nameSp[h]               # delete module namespace
        del openRigType[h]          # delete rig's backend name
        openDrivers.remove(h)       # (for status cmd)
        return ACK
    else:
        return NAK + "not open."

def make_cmd(sense, s):   # Parse sub-command & create backend fn call
    if not sense in ['put', 'get', 'test']:     # allowed options
        return NAK+"make call -- bad sense: %s" % sense
    parms = s.split(None,1)
    subcom = parms[0]                       # The sub-command part
    args = ''
    if len(parms)>1: args = parms[1]        # The arguments, if any
    if sense == 'put' and args == '':
        return NAK                          # puts require arguments
    split = subcom.split(".", 3)            # rig_id, main/sub/control, action
    if len(split) != 3:
        return NAK
    h = split[0]
    trv = split[1]
    cmd = split[2]
    # Check for valid trv?  Not here - we don't know what's valid.
    fn_name = cmd                           # e.g. af_gain
    if not h in backEnd:
        return NAK + "Radio not open."
    if dir(backEnd[h]).count(fn_name) == 0: # do we know about fn_name?
        return NAK+"function name not recognized: '%s'" % fn_name
    mode = { 'get':T_GET, 'put':T_PUT, 'test':T_TEST } [sense]
    cmd1 = "backEnd['%s'].%s(%d,'%s'" % (h,fn_name,mode,trv)
    if sense == 'put':                      # if 'put', add arguments
        cmd1 += ", '%s'" % args
    cmd1 += ')'
    return cmd1         # returns fully qualified function call in string

# input: "rig-command parameters"
# A rig-command has the form <rig_id>.<type>.<action>, where
# 'type' is rig-dependent, but typically 
# 'MAIN'/'SUB'/'VFOA'/'VFOB'/'CONTROL'. (Orion)
# 'action' is 'mode', 'af_gain', 'vfo_freq', etc.

def do_put(s):      # e.g., rig1.rx.af_gain value
    # use make_getput to construct the command with namespace, 
    # parameters, etc.: '<namespace>.put_<action> parameters'
    cmd = make_cmd('put',s)
    if cmd.startswith(NAK):
        return NAK+"put command unrecognized or needs argument: '%s'" % s
    resp = eval (cmd)           # execute the command, response passed up
    return resp

# like 'do_put', except no parameters and translates to get_<action>
def do_get(s):      # e.g., rig1.rx.af_gain
    cmd = make_cmd('get',s)
    if cmd.startswith(NAK) :
        return NAK+"get command not recognized: %s" % s
    resp = eval (cmd)           # pass response up
    return resp

def do_test(s):     # Test if a command is implemented for this rig
                    # parse s: rig.vrx.freq --> eg 'rig.vrx.freq'
                    # Note that vrx field is not verified here.
    parms = s.split(None,2)     # (will ignore any arguments after
    lst = parms[0].split('.',3)   # want exactly 3 fields
    if len(lst) < 3:
        return NAK+'Test 2: invalid format "%s"' % s
    h, vrx, cmd = lst
    sp = cmd.find(' ')                 # trim space & stuff at end
    if sp >= 0: cmd = cmd[:sp-1]
    if not backEnd.has_key(h):  
        return NAK+'Test 3: rig type unknown: "%s"' % h
    # Try to find the class where the command/method is first located,
    # if it exists at all.
    trial_cmd = 'backEnd[h].%s(T_TEST,"%s")' %(cmd, vrx)
    try:
        result = eval (trial_cmd)
    except AttributeError:
        # The method name is not even in backend - spelling error?
        return NAK+'Function unknown: %s' % parms[0]
    if result == None:
        # Method exists, but not implemented except in Backend. Fail.
        return NAK+'Function not implemented for this rig.'
        # Method was overlayed on Backend: command implemented. Success.
    return ACK

# Provide status of this server (not the rig)
def do_status(s):
    global nameSp, backEnd, openDrivers
    r = 'Known rig backends:'
    xx = SUPPORTED_RIGS.keys()    # list of supported rigs
    xx.sort()       # sort it
    for x in xx:    # print known backends and whether they are loaded
        if x in openRigType.values():    # are we using this backend now?
            stat = 'OPEN'
        else:
            stat = 'available'
        r += '\n%9s - %s: %s' % (stat,x,SUPPORTED_RIGS[x][1])
    r += '\n\nsys.platform: %s' % sys.platform
    r += '\nos.getcwd(): %s' % os.getcwd()
    r += '\nsys.path: %s' % ( [sys.path[z] 
        for z in range( min(6,len(sys.path)) )] + ['truncated...'])

    r += "\n\n"
    r += "Open rig list:\n"
    for rig in backEnd:
        if "TRUE" in backEnd[rig].init(T_GET).upper():
            r += "\tInited     "
        else:
            r += "\tNon-inited "
        r += rig + " (" + backEnd[rig].backend_id + ")\n"
    r += "End of open rig list"

    r += "\n\n"
    r += "Service list:\n"
    scopes = ["rigserve"]
    for rig in backEnd:
        scopes.append(rig)
    for scope in scopes:
        if scope is "rigserve":
            my_dict = services_dict
        else:
            my_dict = backEnd[scope].get_services_dict()
        for service_name in my_dict:
            service = my_dict[service_name]
            if "TRUE" in service.status().upper():
                r += "\tStarted "
                args = "(" + service.args + ") "
            else:
                r += "\tStopped "
                args = ""
            r += scope + "." + service_name + args + " - " + service.description + "\n"
    r += "End of service list\n"

    r += "\n** End of status info."
    return r

# Provide some text information.
def do_help(s):
    result = '''
    Rigserve 0.20 responds to the following commands, with typical arguments:

    open rig1 TT_orion                                 - instantiate a rig object for a particular rig type.
    close rig1                                         - release a rig's resources.
    put rig1.CONTROL.init /dev/ttyUSB0 4800            - attach serial port /dev/ttyUSB0 (4800 baud) to rig1
    put rig1.CONTROL.init remoterig 10.3.73.128 12337  - attach remoterig at IP address 10.3.73.128 (UDP port 12337) to rig1
    put rig1.VFOA.freq 14.05e6                         - send a value to rig/vfo/frequency
    get rig1.VFOA.freq                                 - get current freq. for rig/vfo
    test put rig1.MAIN.rx_mode                         - Check if command is implemented for this rig
    status                                             - Get some status info for the server
    start rigserve.global_service_name                 - Start a rigserve-wide service
    start rig1.rig_service_name                        - Start a rig-wide service
    stop rigserve.global_service_name                  - Stop a rigserve-wide service
    stop rig1.rig_service_name                         - Stop a rig-wide service
    help                                               - Get this message 

    A typical session would:
       1) open a rig
       2) attach a serial port or a remoterig to the rig
       3) optionally, start some services
       4) issue get and put commands
       5) stop the services
       6) close the rig


    -- IMPORTANT NOTICE -- BE VERY CAREFUL --

    Do NOT set any network services to listen in a publicly
    available network interface. They are NOT authenticated and
    they are NOT safe.

    Your rig would be available to ANYONE all over the Internet!

    You have been warned!
'''
    return result

def do_start(s):
    split = s.split(".", 1)

    scope = split[0]
    if scope == "rigserve":
        scope_services_dict = services_dict
    elif scope in backEnd:
        scope_services_dict = backEnd[scope].get_services_dict()
    else:
        return NAK + "Rig " + scope + " is not open."

    start_str = split[1]
    split = start_str.split(" ", 1)
    service_name = split[0]
    if len(split) > 1:
        args = split[1]
    else:
        args = ""
    if service_name in scope_services_dict:
        service = scope_services_dict[service_name]
        return service.start(args)
    else:
        return NAK + "Unknown service " + scope + "." + service_name + "."

def do_stop(s):
    split = s.split(".", 1)

    scope = split[0]
    if scope == "rigserve":
        scope_services_dict = services_dict
    elif scope in backEnd:
        scope_services_dict = backEnd[scope].get_services_dict()
    else:
        return NAK + "Rig " + scope + " is not open."

    service_name = split[1]
    if service_name in scope_services_dict:
        service = scope_services_dict[service_name]
        return service.stop()
    else:
        return NAK + "Unknown service " + scope + "." + service_name + "."


# Major command recognition -> call corresponding function
# 'command' accepts a raw input string from the control port (local or
# socket), recognizes the 'major command', and executes it.

command_dict = { 'o':do_open, 'c':do_close, 't':do_test,
                'p':do_put, 'g':do_get, 's':do_status, 'h':do_help,
                'start':do_start, 'stop':do_stop }
def command(cmd):
    global command_dict
    # These are the major commands, all unique in their first letter.
    # remove terminal cr-lf, if present.  E.g., from telnet input.
    p = cmd.find('\r\n')
    if p >= 0: cmd = cmd[:p]
    split = cmd.split(None,1)   # Parse the line into command + arguments
    if split == []:
        return ACK              # We got a null command.
    m = split[0]
    args =''
    if len(split) > 1: args = split[1]
    try:
        if m in command_dict:
            func = command_dict [ m ]
        else:
            func = command_dict[ m[0] ] # Call the command handler
    except KeyError:
        result = NAK+'Major command not recognized: "%s"' % m[0]
    else:
        result = func(args)
    return result
#
# MAIN PROGRAM
#
if __name__ == '__main__':

##############################################################
## for normal operation with rigserve, set test_mode=False. ##
    test_mode = False
##############################################################

# Define options for test mode, if needed.
#
    if not test_mode:
    # Normal execution: communicate with client over PORT

    # Note: after program terminates, you cannot restart and use bind
    # until after a 60 sec timeout, due to OS (Linux).  There is an 
    # "SO_REUSEADDR" option in Linux, but we probably need to use 
    # the more complicated Python SocketServer facility to get it.
    # Future: communicate on multiple ports at once!

        print IDENT

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        counter = 0
        while True:
            try:
                counter = counter + 1
                s.bind((ALLOWED_IP, PORT))
                break
            except socket.error:
                if counter == 1:
                    print "Can't open IP Port. Waiting until available..."
                elif counter > 66:
                    print "the IP port is not avaliable, exiting"
                    exit(1)
                time.sleep(1)
        s.listen(5)
        clients = []
        addrs_dict = {}

        for arg in sys.argv[1:len(sys.argv)]:
            try:
                my_file = open(arg, "r")
            except:
                print "File " + arg + " not found, skipping..."
                continue
            while True:
                my_line = my_file.readline()
                if my_line == "":
                    break
                my_line = my_line.rstrip().lstrip()
                print my_line
                reply = str(command(my_line))
                print ".... returned " + reply
        print "End of file processing."

        try:
            new_socket = 0
            while True:
               to_be_selected = [s]
               for client in clients:
                  to_be_selected.append(client)

               [r, w, e] = select.select(to_be_selected, [], [], 40)

               if s in r:
                  new_socket, addr = s.accept()
                  new_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                  clients.append(new_socket)
                  addrs_dict[new_socket] = addr
                  print time.asctime(),' Connected from', addr
                  new_socket.sendall('Welcome to Rigserve!\n')

               for c in r:
                  if not c is s:
                     try:
                        rData = c.recv(8192)
                        rData = rData.rstrip().lstrip()
                        #print "rcv:", rData, "from:", addrs_dict[c]
                        if rData.upper().startswith("QUIT"):
                           if c in w:
                              c.sendall("QUIT\n")
                           c.close()
                           print time.asctime(), " Disconnected from", addrs_dict[c]
                           clients.remove(c)
                           del addrs_dict[c]
                        else:
                           reply = str(command(rData))
                           #print "snd:", reply, "to:", addrs_dict[c]
                           c.sendall(reply + "\n")
                     except socket.error:
                        c.close()
                        clients.remove(c)
                        del addrs_dict[c]
        except KeyboardInterrupt:
             for c in clients:
                 c.close()
             s.close()
             print "All closed"
    else:

# Place diagnostic calls below -- executed when test_mode == True
# Rig "acceptance" tests
# These may be deleted as you wish.
	print "THIS IS DEBUG MODE"
        def q(s):
            time.sleep(0.2)
            print "cmd:",s
            print "...resp:",command(s)
        q('open RIG1 TT_orion_v1')
# Note: /dev/ham.orion is a symlink to /dev/ttyUSB2 at AA6E.  Comment out
# this line and uncomment the following one for standard port name.
        q('put RIG1.CONTROL.init /dev/ham.orion 57600')
#        q('put RIG1.CONTROL.init /dev/ttyS0 57600')
        q('get RIG1.CONTROL.init')
        q('put RIG1.TX.transmit 0')     # Be sure we're receiving!
        q('get RIG1.CONTROL.status')
        q('test RIG1.VFOA.operate')
        q('status')
        q('help')
        q('get RIG1.CONTROL.info')
        for r in ['MAIN','SUB']:
            for mm in ['USB','CW','CWR','AM','FM','RTTY','LSB']:
                q('put RIG1.%s.rx_mode %s' % (r,mm))
                q('get RIG1.%s.rx_mode' % r)
        q('put RIG1.TX.tx_mode USB')
        q('get RIG1.TX.tx_mode')
        for i in ['VFOA', 'VFOB']:
            for iif in range(2):
                f = iif*1e4 + 21.05e6
                q('put RIG1.%s.freq %.1f' % (i,f))
                q('get RIG1.%s.freq' % i)
        q('put RIG1.MAIN.af_gain 0.5')
        q('get RIG1.MAIN.af_gain  ')
        q('put RIG1.MAIN.rf_gain 0.4')
        q('get RIG1.MAIN.rf_gain')
        q('put RIG1.VFOA.freq 14031234')
        q('get RIG1.VFOB.freq')
        q('get RIG1.VFOA.freq')
        q('put RIG1.VFOA.vfo_step 1000.')
        q('get RIG1.VFOA.vfo_step')
        q('put RIG1.MAIN.bandpass_limits 300. 600.')
        q('get RIG1.MAIN.bandpass_limits')
        q('get RIG1.MAIN.bandpass')
        q('put RIG1.MAIN.bandpass 400. 200.')
        q('get RIG1.MAIN.bandpass')
        q('get RIG1.MAIN.bandpass_limits')
        q('put RIG1.MAIN.bandpass_standard NARROW')
        q('get RIG1.MAIN.bandpass')
        q('put RIG1.MAIN.agc_mode FAST')
        q('get RIG1.MAIN.agc_mode')
        q('get RIG1.MAIN.agc_user')
        q('put RIG1.MAIN.agc_user 0.2 0.10 8.0')
        q('get RIG1.MAIN.agc_user')
        q('put RIG1.MAIN.agc_mode MEDIUM')
        q('get RIG1.MAIN.squelch_open')
        q('put RIG1.MAIN.squelch_level 0.5')
        q('get RIG1.MAIN.squelch_level')
        q('test RIG1.MAIN.squelch_level')
        q('test RIG1.MAIN.squelch_open')
        q('test RIG1.MAIN.rit')
        q('put RIG1.MAIN.rit -100.')
        q('get RIG1.MAIN.rit')
        q('put RIG1.TX.xit -200.')
        q('get RIG1.TX.xit')
        q('put RIG1.TX.mic_gain 0.1')
        q('get RIG1.TX.mic_gain')
        q('put RIG1.TX.speech_proc 0.2')
        q('get RIG1.TX.speech_proc')
        q('put RIG1.MAIN.noise_blank 0.5')
        q('get RIG1.MAIN.noise_blank')
        q('put RIG1.MAIN.noise_reduce 0.5')
        q('get RIG1.MAIN.noise_reduce')
        q('put RIG1.MAIN.notch_auto 0.5')
        q('get RIG1.MAIN.notch_auto')
        q('put RIG1.MAIN.rx_mode AM')
        q('get RIG1.TX.transmit')
        test_transmit = False        # Be sure we're on a dummy load??
        if test_transmit: 
            q('put RIG1.TX.transmit 1')
            q('get RIG1.TX.transmit')
            time.sleep(2)
            q('get RIG1.TX.swr_raw')
            q('get RIG1.TX.swr')
            q('put RIG1.TX.transmit 0')
        q('put RIG1.TX.power 56')
        q('get RIG1.TX.power')
        q('get RIG1.MAIN.strength_raw')
        q('get RIG1.MAIN.strength')
        q('put RIG1.MAIN.memory_channel 23')
        q('put RIG1.VFOA.vfo_memory 7.123e6')
        q('put RIG1.MAIN.memory_channel 24')
        q('put RIG1.VFOA.vfo_memory 7.234e6')
        q('get RIG1.VFOA.vfo_memory')
        q('close RIG1')
