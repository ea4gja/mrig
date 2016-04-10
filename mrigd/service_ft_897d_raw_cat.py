#!/usr/bin/env python
#
# File: service_ft_897d_raw_cat.py
# Version: 1.0
#
# mrigd: raw CAT network service for Yaesu FT-897D
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


from service import *
from multiprocessing import Process
from select import *
from socket import *
from time import *
from globals import *
from signal import *

class Service_FT_897d_Raw_CAT(Service):
    def __init__(self, rig_name):
        Service.__init__(self, rig_name)
        self.__parsed_args = {}
        self.__parsed_args["listen_addr"] = "127.0.0.1"
        self.__parsed_args["listen_tcp_port"] = "7790"
        self.__process = None
        self.__rig_name = rig_name
        self.__terminating = False
        self.__rigserve = None
        self.description = "basic 3rd-party software (such as Pocket RxTX for Android) compatibility support"

    def send_raw_cat(self, value):
        request = "put " + self.__rig_name + ".CONTROL.raw_cat " + value
        print "3rd party request: " + request
        self.__rigserve.sendall(request)

    def recv(self):
        response = self.__rigserve.recv(10240)
        response = response[:-1]
        print "3rd party response: " + response
        return response

    def __execute_raw_cmd(self, cmd):
        formatted = ""
        for f in range(5):
           hexadec = "%x" % cmd[f]
           formatted = formatted + " " + hexadec
        self.send_raw_cat(formatted)

        response = self.recv()
        if len(response) > 0:
           response = response.split(" ", 20)
           unformatted = bytearray(len(response))
           for i in range(len(response)):
              unformatted[i] = int(response[i], 16)

           return unformatted
        else:
           return None

    def __sigterm_handler(self, signalnum, frame):
        self.__terminating = True

    def __target(self):
        signal(SIGTERM, self.__sigterm_handler)

        PORT = 14652
        self.__rigserve = socket(AF_INET, SOCK_STREAM)
        self.__rigserve.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        counter = 0
        while True:
            try:
               counter = counter + 1
               self.__rigserve.connect(('127.0.0.1', PORT))
               if len(self.__rigserve.recv(8192)) == 0:
                   raise IOException
               break
            except:
               if counter < 65:
                   sleep(1)
               else:
                   print "3rd party compat. service: cannot connect to main rigserve server, exiting."
                   exit(1)

        listen_socket = socket(AF_INET, SOCK_STREAM)
        is_done = False
        tries = 0
        while not is_done and tries < 65:
            tries = tries + 1
            try:
                listen_socket.bind((self.__parsed_args["listen_addr"], int(self.__parsed_args["listen_tcp_port"])))
                is_done = True
            except:
                is_done = False
                sleep(1)
        if not is_done:
            return

        listen_socket.listen(5)

        clients = []
        buffers_dict = {}

        while not self.__terminating:
            selected = [listen_socket]
            for client in clients:
                selected.append(client)

            try:
                r, w, e = select(selected, [], [], 60)
            except:
                r = []
                w = []
                e = []
                self.__terminating = True

            if listen_socket in r:
                [new_socket, new_addr] = listen_socket.accept()
                new_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                new_socket.setblocking(1)
                buffers_dict[new_socket] = ""
                clients.append(new_socket)

            try:
                r, w, e = select(clients, [], [], 1)
            except:
                r = []
                w = []
                e = []
                self.__terminating = True

            for client in r:
                remove_this_client = False
                try:
                    cmd = [0, 0, 0, 0, 0]
                    for i in range(5):
                       cmd[i] = ord(client.recv(1)[0])
                    reply = self.__execute_raw_cmd(cmd)
                    if not reply is None:
                       client.sendall(reply)
                except:
                    remove_this_client = True

                if remove_this_client:
                    clients.remove(client)
                    del buffers_dict[client]
                    client.close()

        listen_socket.close()
        self.__rigserve.send("quit")
        self.__rigserve.close()

    def start_action(self, args):
        super(Service_FT_897d_Raw_CAT, self).start_action(args)
        split = args.split(" ", 256)
        for arg in split:
            if "=" in arg:
                split2 = arg.split("=", 2)
                if len(split2) != 2:
                    return NAK
                else:
                    current_key = split2[0]
                    current_val = split2[1]
                    self.__parsed_args[current_key] = current_val

        self.__process = Process(target=self.__target, args=())
        self.__process.daemon = True
        self.__process.start()

        return ACK

    def stop_action(self):
        super(Service_FT_897d_Raw_CAT, self).stop_action()
        self.__process.terminate()

        return ACK

    def status(self):
        if not self.__process:
            return ACK + str(False)
        return ACK + str(self.__process.is_alive())

