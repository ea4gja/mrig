#!/usr/bin/env python
#
# File: service.py
# Version: 1.0
#
# mrigd: base class for all the services
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


from globals import *

class Service(object):
    def __init__(self, rig_name):
        self.description = "Base service class"
        self.__running = False
        self.rig_name = rig_name
        self.args = ""

    def start_action(self, args):
        self.args = args
        return ACK

    def stop_action(self):
        return ACK

    def start(self, args = ""):
        if "TRUE" in self.status().upper():
            return NAK + "Already running."
        else:
            self.__running = True
            return self.start_action(args)

    def stop(self):
        if "TRUE" in self.status().upper():
            self.__running = False
            return self.stop_action()
        else:
            return NAK + "Not running."

    def status(self):
        return str(self.__running)
