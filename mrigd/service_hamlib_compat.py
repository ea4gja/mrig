#!/usr/bin/env python
#
# This file is still incomplete and most features do not work
#
# File: service_hamlib_compat.py
# Version: 1.0
#
# mrigd: hamlib/rigctl-compatible server (still incomplete)
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
import traceback

class Service_Hamlib_Compat(Service):
    def __init__(self, rig_name):
        Service.__init__(self, rig_name)
        self.__parsed_args = { }
        self.__parsed_args["listen_addr"] = "127.0.0.1"
        self.__parsed_args["listen_tcp_port"] = "4532"
        self.__parsed_args["simple_addr"] = "127.0.0.1"
        self.__parsed_args["from_simple_if"] = "127.0.0.1"
        self.__parsed_args["simple_tcp_port"] = "14653"
        self.__parsed_args["simple_local_udp_port"] = "14654"
        self.__process = None
        self.__state = {
            "tick":      -1,
            "ptt":       None,
            "freq":      None,
            "mode":      None,
            "vfo":       None,
            "s-meter":   None,
            "nom-power": None
        }
        self.__s_meter = {
            "0": "-54",
            "1": "-48",
            "2": "-42",
            "3": "-36",
            "4": "-30",
            "5": "-24",
            "6": "-18",
            "7": "-12",
            "8": "-6",
            "9": "0",
            "+10dB": "10",
            "+20dB": "20",
            "+30dB": "30",
            "+40dB": "40",
            "+50dB": "50",
            "+60dB": "60" 
        }
        self.__terminating = False
        self.description = "UNSTABLE - basic hamlib (rigctl / rigctld) compatibility support with cache"


    def execute_hamlib_cmd(self, hamlib_cmd):
        op_code = hamlib_cmd[0]
        if len(hamlib_cmd) > 1:
            args = hamlib_cmd[1:]
        else:
            args = [ ]

        simple_eol = "\n"
        hamlib_eol = "\n"
        hamlib_ok = "RPRT 0"
        hamlib_einternal = "RPRT -7"
        hamlib_einval = "RPRT -1"
        hamlib_enavail = "RPRT -11"
        try:
            if op_code == "f" or op_code == "\\get_freq":
                freq = self.__state["freq"]
                if freq and freq != "?":
                    return freq + hamlib_eol
                else:
                    return hamlib_einternal + hamlib_eol
            elif op_code == "F" or op_code == "\\set_freq":
                freq = args[0].lstrip().rstrip()
                try:
                    freq = str(int(float(freq)))
                    self.__to_simple.sendall("freq: " + freq + simple_eol)
                except:
                    return hamlib_einternal + hamlib_eol
                self.__state["freq"] = freq
                return hamlib_ok + hamlib_eol
            elif op_code == "m" or op_code == "\\get_mode":
                mode = self.__state["mode"]
                if mode and mode != "?":
                    return mode + hamlib_eol + "0" + hamlib_eol
                else:
                    return hamlib_einternal + hamlib_eol
            elif op_code == "M" or op_code == "\\set_mode":
                mode = args[0]
                try:
                    self.__to_simple.sendall("mode: " + mode + simple_eol)
                except:
                    return hamlib_einternal + hamlib_eol
                self.__state["mode"] = mode
                return hamlib_ok + hamlib_eol
            elif op_code in ("v", "\\get_vfo"):
                vfo = self.__state["vfo"]
                if vfo and vfo != "?":
                    return vfo + hamlib_eol
                else:
                    return hamlib_einternal + hamlib_eol
            elif op_code in ("V", "\\set_vfo"):
                vfo = args[0]
                vfo = vfo.lstrip()
                vfo = vfo.rstrip()
                try:
                    self.__to_simple.sendall("vfo: " + vfo + simple_eol)
                except:
                    return hamlib_einternal + hamlib_eol
                self.__state["vfo"] = vfo
                return hamlib_ok + hamlib_eol
            elif op_code in ("t", "\\get_ptt"):
                ptt = self.__state["ptt"]
                if ptt and ptt != "?":
                    if "TRUE" in ptt.upper():
                        return "1" + hamlib_eol
                    else:
                        return "0" + hamlib_eol
                else:
                    return hamlib_einternal + hamlib_eol
            elif op_code in ("T", "\\set_ptt"):
                ptt = args[0].lstrip().rstrip()
                try:
                    if ptt == "1":
                        self.__to_simple.sendall("ptt: True" + simple_eol)
                    elif ptt == "0":
                        self.__to_simple.sendall("ptt: False" + simple_eol)
                    else:
                        return hamlib_einval + hamlib_eol
                except:
                    return hamlib_einternal + hamlib_eol
                if ptt == "1":
                    self.__state["ptt"] = "True"
                elif ptt == "0":
                    self.__state["ptt"] = "False"
                return hamlib_ok + hamlib_eol
            elif op_code in ("l", "\\get_level"):
                args = args[0].rstrip()
                args = args.lstrip()
                args = args.upper()
                if "RFPOWER" in args:
                    nom_power = self.__state["nom-power"]
                    if nom_power and nom_power != "?":
                        try:
                            relative_power = int(nom_power) / 100.0
                        except:
                            return hamlib_einternal + hamlib_eol
                        return str(relative_power) + hamlib_eol
                    else:
                        return hamlib_einternal + hamlib_eol
                elif "STRENGTH" in args:
                    s_meter = self.__state["s-meter"]
                    if s_meter and s_meter != "?":
                        return self.__s_meter[s_meter] + hamlib_eol
                    return hamlib_einternal + hamlib_eol
                else:
                    return hamlib_enavail + hamlib_eol
            elif op_code in ("2", "power2mW"):
                if len(args) != 3:
                    return hamlib_enavail + hamlib_eol
                else:
                    str_val = args[0]
                    str_val = str_val.lstrip()
                    str_val = str_val.rstrip()
                    try:
                        float_val = float(str_val)
                    except:
                        return hamlib_enavail + hamlib_eol

                    float_val = float_val * 100  # to W
                    float_val = float_val * 1000  # to mW
                    return str(float_val) + hamlib_eol
            elif op_code == "\\dump_state":
                return \
                   "0\n" + \
                   "123\n" + \
                   "2\n" + \
                   "100000.000000 56000000.000000 0xbf -1 -1 0x0 0x0\n" + \
                   "76000000.000000 108000000.000000 0x40 -1 -1 0x0 0x0\n" + \
                   "118000000.000000 164000000.000000 0xbf -1 -1 0x0 0x0\n" + \
                   "420000000.000000 470000000.000000 0xbf -1 -1 0x0 0x0\n" + \
                   "0 0 0 0 0 0 0\n" + \
                   "1800000.000000 2000000.000000 0x3f 10000 100000 0x3 0x0\n" + \
                   "3500000.000000 4000000.000000 0x3f 10000 100000 0x3 0x0\n" + \
                   "7000000.000000 7300000.000000 0x3f 10000 100000 0x3 0x0\n" + \
                   "10100000.000000 10150000.000000 0x3f 10000 100000 0x3 0x0\n" + \
                   "14000000.000000 14350000.000000 0x3f 10000 100000 0x3 0x0\n" + \
                   "18068000.000000 18168000.000000 0x3f 10000 100000 0x3 0x0\n" + \
                   "21000000.000000 21450000.000000 0x3f 10000 100000 0x3 0x0\n" + \
                   "24890000.000000 24990000.000000 0x3f 10000 100000 0x3 0x0\n" + \
                   "28000000.000000 29700000.000000 0x3f 10000 100000 0x3 0x0\n" + \
                   "1800000.000000 2000000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "3500000.000000 4000000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "7000000.000000 7300000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "10100000.000000 10150000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "14000000.000000 14350000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "18068000.000000 18168000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "21000000.000000 21450000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "24890000.000000 24990000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "28000000.000000 29700000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "144000000.000000 148000000.000000 0x3f 5000 50000 0x3 0x0\n" + \
                   "144000000.000000 148000000.000000 0x1 2500 25000 0x3 0x0\n" + \
                   "430000000.000000 440000000.000000 0x3f 2000 20000 0x3 0x0\n" + \
                   "430000000.000000 440000000.000000 0x1 500 5000 0x3 0x0\n" + \
                   "0 0 0 0 0 0 0\n" + \
                   "0x8e 10\n" + \
                   "0x8e 100\n" + \
                   "0x21 10\n" + \
                   "0x21 100\n" + \
                   "0 0\n" + \
                   "0 0\n" + \
                   "9990\n" + \
                   "0\n" + \
                   "0\n" + \
                   "0\n" + \
                   "\n" + \
                   "\n" + \
                   "0x0\n" + \
                   "0x10030\n" + \
                   "0x54001000\n" + \
                   "0x0\n" + \
                   "0x0\n" + \
                   "0x0"
            else:
#                print "Hamlib command " + hamlib_cmd + " not supported."
                return hamlib_enavail + hamlib_eol
        except:
            return hamlib_einternal + hamlib_eol
        return hamlib_enavail + hamlib_eol


    def __sigterm_handler(self, signalnum, frame):
        self.__terminating = True


    def __parse_hamlib_cmds(self, raw_buffer):
        num_args_dict = { }
        num_args_dict["q"] = 0
        num_args_dict["F"] = 1
        num_args_dict["f"] = 0
        num_args_dict["M"] = 2
        num_args_dict["m"] = 0
        num_args_dict["I"] = 1
        num_args_dict["i"] = 0
        num_args_dict["X"] = 2
        num_args_dict["x"] = 0
        num_args_dict["S"] = 2
        num_args_dict["s"] = 0
        num_args_dict["N"] = 1
        num_args_dict["n"] = 0
        num_args_dict["L"] = 2
        num_args_dict["l"] = 1
        num_args_dict["U"] = 2
        num_args_dict["u"] = 1
        num_args_dict["P"] = 2
        num_args_dict["p"] = 1
        num_args_dict["G"] = 1
        num_args_dict["g"] = 2
        num_args_dict["A"] = 1
        num_args_dict["a"] = 0
        num_args_dict["R"] = 1
        num_args_dict["r"] = 0
        num_args_dict["O"] = 1
        num_args_dict["o"] = 0
        num_args_dict["C"] = 1
        num_args_dict["c"] = 0
        num_args_dict["D"] = 1
        num_args_dict["d"] = 0
        num_args_dict["V"] = 1
        num_args_dict["v"] = 0
        num_args_dict["T"] = 1
        num_args_dict["t"] = 0
        num_args_dict["E"] = 1
        num_args_dict["e"] = 0
        num_args_dict["H"] = 1
        num_args_dict["h"] = 1
        num_args_dict["B"] = 1
        num_args_dict["_"] = 0
        num_args_dict["J"] = 1
        num_args_dict["j"] = 0
        num_args_dict["Z"] = 1
        num_args_dict["z"] = 0
        num_args_dict["Y"] = 1
        num_args_dict["y"] = 0
        num_args_dict["*"] = 1
        num_args_dict["w"] = 1
        num_args_dict["b"] = 1
        num_args_dict["2"] = 3
        num_args_dict["4"] = 3
        num_args_dict["1"] = 0
        num_args_dict["3"] = 0
        num_args_dict["\\set_freq"] = 1
        num_args_dict["\\get_freq"] = 0
        num_args_dict["\\set_mode"] = 2
        num_args_dict["\\get_mode"] = 0
        num_args_dict["\\set_split_freq"] = 1
        num_args_dict["\\get_split_freq"] = 0
        num_args_dict["\\set_split_mode"] = 2
        num_args_dict["\\get_split_mode"] = 0
        num_args_dict["\\set_split_vfo"] = 2
        num_args_dict["\\get_split_vfo"] = 0
        num_args_dict["\\set_ts"] = 1
        num_args_dict["\\get_ts"] = 0
        num_args_dict["\\set_level"] = 2
        num_args_dict["\\get_level"] = 1
        num_args_dict["\\set_func"] = 2
        num_args_dict["\\get_func"] = 1
        num_args_dict["\\set_parm"] = 2
        num_args_dict["\\get_parm"] = 1
        num_args_dict["\\vfo_op"] = 1
        num_args_dict["\\scan"] = 2
        num_args_dict["\\set_trn"] = 1
        num_args_dict["\\get_trn"] = 0
        num_args_dict["\\set_rptr_shift"] = 1
        num_args_dict["\\get_rptr_shift"] = 0
        num_args_dict["\\set_rptr_offs"] = 1
        num_args_dict["\\get_rptr_offs"] = 0
        num_args_dict["\\set_ctcss_tone"] = 1
        num_args_dict["\\get_ctcss_tone"] = 0
        num_args_dict["\\set_dcs_code"] = 1
        num_args_dict["\\get_dcs_code"] = 0
        num_args_dict["\\set_ctcss_sql"] = 1
        num_args_dict["\\get_ctcss_sql"] = 0
        num_args_dict["\\set_dcs_sql"] = 1
        num_args_dict["\\get_dcs_sql"] = 0
        num_args_dict["\\set_vfo"] = 1
        num_args_dict["\\get_vfo"] = 0
        num_args_dict["\\set_ptt"] = 1
        num_args_dict["\\get_ptt"] = 0
        num_args_dict["\\set_mem"] = 1
        num_args_dict["\\get_mem"] = 0
        num_args_dict["\\set_channel"] = 1
        num_args_dict["\\get_channel"] = 1
        num_args_dict["\\set_bank"] = 1
        num_args_dict["\\get_info"] = 0
        num_args_dict["\\set_rit"] = 1
        num_args_dict["\\get_rit"] = 0
        num_args_dict["\\set_xit"] = 1
        num_args_dict["\\get_xit"] = 0
        num_args_dict["\\set_ant"] = 1
        num_args_dict["\\get_ant"] = 0
        num_args_dict["\\set_powerstat"] = 1
        num_args_dict["\\get_powerstat"] = 0
        num_args_dict["\\send_dtmf"] = 1
        num_args_dict["\\recv_dtmf"] = 0
        num_args_dict["\\reset"] = 1
        num_args_dict["\\send_cmd"] = 1
        num_args_dict["\\send_morse"] = 1
        num_args_dict["\\get_dcd"] = 0
        num_args_dict["\\power2mW"] = 3
        num_args_dict["\\mW2power"] = 3
        num_args_dict["\\dump_caps"] = 0
        num_args_dict["\\dump_conf"] = 0
        num_args_dict["\\dump_state"] = 0
        num_args_dict["\\chk_vfo"] = 0
        num_args_dict["\\halt"] = 0

        my_buffer = raw_buffer
        my_buffer = my_buffer.replace("\r", " ")
        my_buffer = my_buffer.replace("\n", " ")
        
        spl = my_buffer.split(" ")
        words = [ ]
        for s in spl:
            if s != "":
                words.append(s)
        if not words:
            return [ ], ""

        just_one_char_opcode = not words[0].startswith("\\")
        if just_one_char_opcode:
            first_opcode = words[0][0]
        else:
            first_opcode = words[0]

        try:
            num_args_first_command = num_args_dict[first_opcode]
        except:
            if just_one_char_opcode:
                if len(my_buffer) == 1:
                    return [ ], ""
                else:
                    return self.__parse_hamlib_cmds(my_buffer[1:])
            else:
                if len(words) == 1:
                    return [ ], words[0]
                else:
                    my_str = ""
                    for i in range(1, len(words)):
                        my_str = my_str + " " + words[i]
                    my_str = my_str.lstrip()
                    return self.__parse_hamlib_cmds(my_str)

        if just_one_char_opcode and num_args_first_command > 0 and len(words[0]) > 1:
            print "cached hamlib compat. service: unknown hamlib command format, exiting."
            print "cached hamlib compat. service: (offending words " + words[0] + ")"
            quit()
        if just_one_char_opcode and num_args_first_command == 0:
            first_command = [ first_opcode ]
            first_word_suffix = words[0][1:]
            remaining_str = first_word_suffix
            for i in range(1, len(words)):
                remaining_str += " " + words[i]
        elif len(words) > num_args_first_command:
            first_command = [ first_opcode ]
            for i in range(num_args_first_command):
                arg = words[1 + i]
                first_command.append(arg)
            remaining_str = ""
            for i in range(num_args_first_command + 1, len(words)):
                remaining_str += " " + words[i]
            remaining_str = remaining_str.lstrip()
        else:
            return [ ], raw_buffer

        next_commands, tail = self.__parse_hamlib_cmds(remaining_str)
        all_commands = [ first_command ]
        for c in next_commands:
            all_commands.append(c)
        return all_commands, tail


    def __target(self):
        signal(SIGTERM, self.__sigterm_handler)

        simple_tcp_port = self.__parsed_args["simple_tcp_port"]
        simple_local_udp_port = self.__parsed_args["simple_local_udp_port"]
        try:
            simple_tcp_port = int(simple_tcp_port)
        except:
            print "Hamlib compat. service with cache: invalid simple tcp port, exiting."
            return
        try:
            simple_local_udp_port = int(simple_local_udp_port)
        except:
            print "Hamlib compat. service with cache: invalid simple local udp port, exiting."
            return
        try:
            simple_addr = self.__parsed_args["simple_addr"]
            from_simple_if = self.__parsed_args["from_simple_if"]
        except:
            print "Hamlib compat. service with cache: invalid simple server data, exiting."
            return

        self.__to_simple = socket(AF_INET, SOCK_STREAM)
        self.__to_simple.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self.__from_simple = socket(AF_INET, SOCK_DGRAM)
        self.__from_simple.bind((from_simple_if, simple_local_udp_port))
        counter = 0
        while True:
            try:
               counter = counter + 1
               self.__to_simple.connect((simple_addr, simple_tcp_port))
               break
            except:
               if counter < 65:
                   sleep(1)
               else:
                   print "Hamlib compat. service with cache: cannot connect to simple server, exiting."
                   exit(1)
        self.__to_simple.settimeout(0.05)

        listen_socket = socket(AF_INET, SOCK_STREAM)
        listen_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        is_done = False
        tries = 0
        while not is_done and tries < 65:
            try:
                listen_socket.bind((self.__parsed_args["listen_addr"], int(self.__parsed_args["listen_tcp_port"])))
                is_done = True
            except:
                sleep(1)
                is_done = False
                tries = tries + 1
        if not is_done:
            return
        listen_socket.listen(5)

        clients = []
        buffers_dict = {}

        last_tick = -1
        while not self.__terminating:
            # update cached radio state
            update = { }

            is_done = False
            recv = ""
            while not is_done:
                r, w, e = select([self.__from_simple], [ ], [ ], 0.05)
                if r:
                    r = r[0]
                    recv, addr = r.recvfrom(65535)
                    if len(recv) == 0:
                        is_done = True
                else:
                    is_done = True

            if len(recv) > 0:
                spl = recv.splitlines()
                start = None
                end = None
                for cnt in range(len(spl)):
                    if spl[cnt].startswith("tick: "):
                        start = cnt
                        break
                if start != None:
                    for cnt in range(start, len(spl)):
                        if spl[cnt].startswith("end-of-tick"):
                            end = cnt
                            break

                if start != None and end != None:
                    for cnt in range(start, end):
                        line = spl[cnt]
                        line_spl = line.split(": ", 1)
                        if len(line_spl) != 2:
                            continue
                        update[line_spl[0]] = line_spl[1]
                try:
                    current_tick = update["tick"]
                    current_tick = int(current_tick)
                except:
                    current_tick = -1
                if current_tick > self.__state["tick"]:
                    for feature in self.__state:
                        if feature in update:
                            self.__state[feature] = update[feature]
                    self.__state["tick"] = current_tick


            # accept any new hamlib client
            selected = [listen_socket]
            for client in clients:
                selected.append(client)

            try:
                r, w, e = select(selected, [], [], 0.01)
            except:
                r = []
                w = []
                e = []
                self.__terminating = True

            if listen_socket in r:
                [new_socket, new_addr] = listen_socket.accept()
                new_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                new_socket.settimeout(0.05)
                buffers_dict[new_socket] = ""
                clients.append(new_socket)

            # process requests from clients
            try:
                r, w, e = select(clients, [], [], 0.05)
            except:
                print "service_hamlib_compat: problem while selecting clients..."
                r = []
                w = []
                e = []
                self.__terminating = True

            for client in r:
                remove_this_client = False
                try:
                    text = client.recv(8192)
                    buffers_dict[client] += text
                    commands, remaining = self.__parse_hamlib_cmds(buffers_dict[client])
                    buffers_dict[client] = remaining
                    for command in commands:
                        if command[0].upper().startswith("Q"):
                            remove_this_client = True
                            break
                        reply = self.execute_hamlib_cmd(command)
                        client.send(reply)
                except:
                    remove_this_client = True

                if remove_this_client:
                    clients.remove(client)
                    del buffers_dict[client]
                    client.close()

        listen_socket.close()
        self.__from_simple.close()
        self.__to_simple.close()


    def start_action(self, args):
        super(Service_Hamlib_Compat, self).start_action(args)
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
        super(Service_Hamlib_Compat, self).stop_action()
        self.__process.terminate()

        return ACK


    def status(self):
        if not self.__process:
            return ACK + str(False)
        return ACK + str(self.__process.is_alive())

