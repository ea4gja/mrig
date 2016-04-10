#!/usr/bin/env python
#
# File: mrigd_config.py
# Version: 1.0
#
# mrigd: configuration file
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


PYTHON="python"                                        # python interpreter
RIGSERVE="/home/german/bin/mrig_mrigd_rc2/mrigd/rigserve.py"  # rigserve.py


# rigserve initialization
#
RIG_NAME="radio_0"                              # logical name of the rig
RIG_BACKEND="YA_ft897d"                         # model of the rig
# RIG_INIT_STRING="remoterig 10.2.67.39 12678"  # remoterig example
                                                # (put IP address and UDP
                                                # command port of RemoteRig
                                                # radio site)
# RIG_INIT_STRING="/dev/ttyUSB0 38400"          # serial port example
                                                # (put device name and baud
                                                # rate)
RIG_INIT_STRING="/dev/ttyUSB0 38400"   # actual init string



# network configuration of simple (including listening interface and port)
#
# NEVER change it to a publicly reachable address and port
# ALWAYS use a VPN to connect to a remote site
#
# simple is NOT authenticated and is NOT prepared to be reachable
# from the Internet: YOU HAVE BEEN WARNED!
#
SIMPLE=True                      # set it to True/False to enable/disable simple
SIMPLE_LISTEN_ADDR="127.0.0.1" # local IP address simple will listen on
SIMPLE_TCP_PORT=14653            # local TCP port simple will listen on
SIMPLE_LOCAL_UDP_PORT=14655      # local UDP port simple will send updates from
SIMPLE_REMOTE_UDP_PORT=14654     # remote UDP port simple will send updates to
SIMPLE_STATIC_CLIENTS="127.0.0.1:20000" # more simple clients to be updated, comma-separated 
SIMPLE_NETWORK_LATENCY="low"     # set it to "low" for now ("high" is broken)



# network configuration of hamlib (including listening interface and port)
#
# NEVER change it to a publicly reachable address and port
# ALWAYS use a VPN to connect to a remote site
#
# hamlib is NOT authenticated and is NOT prepared to be reachable
# from the Internet: YOU HAVE BEEN WARNED!
#
HAMLIB=True                      # set it to True/False to enable/disable hamlib
HAMLIB_LISTEN_ADDR="127.0.0.1" # local IP address hamlib will listen on
HAMLIB_TCP_PORT=4532             # local TCP port hamlib will listen on



# network configuration of raw (including listening interface and port)
#
# NEVER change it to a publicly reachable address and port
# ALWAYS use a VPN to connect to a remote site
#
# raw is NOT authenticated and is NOT prepared to be reachable
# from the Internet: YOU HAVE BEEN WARNED!
#
RAW=True                         # set it to True/False to enable/disable raw
RAW_LISTEN_ADDR="127.0.0.1"    # local IP address raw will listen on
RAW_TCP_PORT=9999                # local TCP port raw will listen on
