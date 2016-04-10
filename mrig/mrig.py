#!/usr/bin/env python
#
# File: mrig.py
# Version: 1.0
#
# mrig: main program
# Copyright (c) 2016 German EA4GJA
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


from mrig_config import *
from gui_tkinter import *
import sys
import socket
import os
from Tkinter import Tk
import multiprocessing


tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
tcp.connect((REMOTE_SERVER, REMOTE_SERVER_TCP_PORT))
tcp.setblocking(1)

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind(("", LOCAL_UDP_PORT))
udp.setblocking(0)

root = Tk()
gui = gui_Tkinter(root, tcp=tcp, udp=udp)
root.mainloop()

tcp.close()
udp.close()
