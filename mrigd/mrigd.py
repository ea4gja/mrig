#!/usr/bin/env python
#
# File: mrigd.py
# Version: 1.0
#
# mrigd: easy-to-start frontend to set up the services
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


from mrigd_config import *

import socket
import multiprocessing
import sys
import os
import signal
import time



NAK_START = "? "

def send_to_rigserve(request):
    rigserve_socket.sendall(request + "\n")
    return rigserve_socket.recv(8192)


def gracefully_exit():
    if rigserve_pid:
        os.kill(rigserve_pid, signal.SIGTERM)
        time.sleep(0.5)
        os.kill(rigserve_pid, signal.SIGKILL)
    quit()


def signal_handler(signal_num, frame):
    if signal_num in [15]:
        gracefully_exit()


def install_signal_handler():
    signal.signal(signal.SIGTERM, signal_handler)


def abort(message):
    print sys.argv[0] + ": " + message + ", exiting"
    gracefully_exit()


def warning(message):
    print sys.argv[0] + ": warning: " + message



if __name__ == "__main__":
    rigserve_pid = None

    install_signal_handler()

    # start rigserve and rigserve services
    rigserve_pid = os.fork()
    if rigserve_pid == 0:
        os.execvp(PYTHON, [ PYTHON, RIGSERVE ])
        abort("cannot execute rigserve")
    else:
        rigserve_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rigserve_socket.setblocking(1)

        try:
            time.sleep(1)
            rigserve_socket.connect(("127.0.0.1", 14652))
            if len(rigserve_socket.recv(8192)) == 0:
                raise IOError
        except:
            print "waiting for rigserve to be available..."
            tries = 0
            is_done = False
            while tries < 150 and not is_done:
                time.sleep(1)
                tries = tries + 1
                is_done = True
                try:
                    rigserve_socket.connect(("127.0.0.1", RIGSERVE_PORT))
                    if len(rigserve_socket.recv(8192)) == 0:
                        raise IOError
                except:
                    is_done = False
            if not is_done:
                abort("cannot connect to rigserve")

        rigserve_socket.settimeout(4)

        cmds = [ ]
        cmds.append("open " + RIG_NAME + " " + RIG_BACKEND)
        cmds.append("put " + RIG_NAME + ".CONTROL.init " + RIG_INIT_STRING)
        if SIMPLE:
            cmd = "start " + RIG_NAME + ".simple "
            cmd += "listen_addr=" + SIMPLE_LISTEN_ADDR + " "
            cmd += "listen_tcp_port=" + str(SIMPLE_TCP_PORT) + " "
            cmd += "local_udp_port=" + str(SIMPLE_LOCAL_UDP_PORT) + " "
            cmd += "remote_udp_port=" + str(SIMPLE_REMOTE_UDP_PORT) + " "
            cmd += "static_clients=" + str(SIMPLE_STATIC_CLIENTS) + " "
            cmd += "latency=" + SIMPLE_NETWORK_LATENCY
            cmds.append(cmd)
        if HAMLIB:
            cmd = "start " + RIG_NAME + ".hamlib "
            cmd += "listen_addr=" + HAMLIB_LISTEN_ADDR + " "
            cmd += "listen_tcp_port=" + str(HAMLIB_TCP_PORT) + " "
            cmd += "simple_addr=" + SIMPLE_LISTEN_ADDR + " "
            cmd += "from_simple_if=" + SIMPLE_LISTEN_ADDR + " "
            cmd += "simple_local_udp_port=" + str(SIMPLE_REMOTE_UDP_PORT)
            cmds.append(cmd)
        if RAW:
            cmd = "start " + RIG_NAME + ".3rd_party "
            cmd += "listen_addr=" + RAW_LISTEN_ADDR + " "
            cmd += "listen_tcp_port=" + str(RAW_TCP_PORT)
            cmds.append(cmd)

        for cmd in cmds:
            response = send_to_rigserve(cmd)
            if response.startswith(NAK_START):
                abort("cmd " + cmd + " failed: " + response)
        print "mrigd: initialized!"

        try:
            os.wait()
        except KeyboardInterrupt:
            print "keyboard interrupt, terminating..."
        except:
            pass

        gracefully_exit()
