#!/usr/bin/env python
#
# File: service_ft_897d_simple_compat.py
# Version: 1.0
#
# mrigd: loader for simple server
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


import traceback
import service
import multiprocessing
import globals
import signal
import service_ft_897d_simple_compat_low_latency
import service_ft_897d_simple_compat_high_latency


class Service_FT_897d_Simple_Compat(service.Service):
    def __init__(self, rig_name):
        service.Service.__init__(self, rig_name)
	  
        self.__parsed_args = { }
        self.__parsed_args["listen_addr"] = "127.0.0.1"
        self.__parsed_args["listen_tcp_port"] = "14653"
        self.__parsed_args["remote_udp_port"] = "14654"
        self.__process = None
        self.__rig_name = rig_name
        self.__terminating = False
        self.__rigserve = None
        self.rigserve_port = 14652
        self.description = "UNSTABLE - supports the basic protocol"


    def start_action(self, args):
        super(Service_FT_897d_Simple_Compat, self).start_action(args)
        split = args.split(" ", 256)
        for arg in split:
            if "=" in arg:
                split2 = arg.split("=", 2)
                if len(split2) != 2:
                    return globals.NAK
                else:
                    current_key = split2[0]
                    current_val = split2[1]
                    self.__parsed_args[current_key] = current_val


        try:
            if "latency" in self.__parsed_args:
                latency = self.__parsed_args["latency"]
            else:
                return globals.NAK + "latency unspecified"
            if latency.upper() == "LOW":
                server = service_ft_897d_simple_compat_low_latency.server(self.__rig_name)
            elif latency.upper() == "HIGH":
                return globals.NAK + "high latency server is broken... sorry!"
                server = service_ft_897d_simple_compat_high_latency.server(self.__rig_name)
            else:
                return globals.NAK + "latency must be high or low"
        except:
            return globals.NAK + "unable to import simple compat module"

        my_args = [ ]
        for arg in self.__parsed_args:
            my_arg = arg + "=" + self.__parsed_args[arg]
            my_args.append(my_arg)

        self.__process = multiprocessing.Process(target=server.target, args=(my_args))
        self.__process.daemon = True
        self.__process.start()

        return globals.ACK


    def stop_action(self):
        super(Service_FT_897d_Simple_Compat, self).stop_action()
        self.__process.terminate()

        return globals.ACK


    def status(self):
        if not self.__process:
            return globals.ACK + str(False)
        return globals.ACK + str(self.__process.is_alive())

