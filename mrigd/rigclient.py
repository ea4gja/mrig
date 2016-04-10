#!/usr/bin/env python
#
# File: rigclient.py
# Version: 1.0
#
# mrigd: rigclient test program
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

# Send commands to the listener's port and listen for replies.
#
#from common import *


PORT    =14652      # Pick a memorable port number to listen on.

import socket, sys

print 'rigclient.py v. 0.22'
print 'Using Port', PORT
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', PORT))
print 'Connected to server'
print s.recv(1024)      # Welcome message
try:
  while True:
    cmd = raw_input(' $')
    s.sendall(cmd)
    resp = s.recv(10240)
    print '....resp:',resp
    if cmd == 'quit': break
finally:
  s.close()
  print 'client socket closed'
