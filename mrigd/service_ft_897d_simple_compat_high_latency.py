#!/usr/bin/env python
#
# This file is broken, please use the low latency flavor instead
#
# File: service_ft_897d_simple_compat_high_latency.py
# Version: 1.0
#
# mrigd: simple server, optimised for high latency networks
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
import select
import socket
import globals
import signal
import datetime
import os
import time
import random


class server():
    def __init__(self, rig_name):
        self.__parsed_args = { }
        self.__rig_name = rig_name
        self.__terminating = False
        self.__client_is_done = False
        self.__rigserve = None
        self.__clients = None
        self.__udp_socket = None
        self.rigserve_port = 14652
        self.__remote_udp_port = None

        self.complex_ttl = 15
        self.long_ttl    = 6
        self.mid_ttl     = 2.5
        self.short_ttl   = 0.4
        self.client_timeout = 0.005

        self.__read_radio_feature_dict = {
            "freq":                 "CONTROL.raw_freq_and_mode_hex",
            "mode":                 "CONTROL.raw_freq_and_mode_hex",
            "vfo":                  "CONTROL.vfo_select",
            "ptt":                  "CONTROL.tx_status",
            "high-swr":             "CONTROL.tx_status",
#            "operate":              "CONTROL.operate",
            "split":                "CONTROL.split",
            "vox":                  "CONTROL.vox",
            "vox-gain":             "CONTROL.vox_gain",
            "vox-delay":            "CONTROL.vox_delay",
            "bk":                   "CONTROL.bk",
            "atten":                "<vfo>.atten",
            "fm-narrow":            "<vfo>.fm_narrow",
            "cw-dig-narrow":        "<vfo>.cw_dig_narrow",
            "agc-mode":             "CONTROL.agc_mode",
            "nb":                   "CONTROL.noise_blank",
            "dnr":                  "CONTROL.noise_reduce",
            "dnf":                  "CONTROL.notch_auto",
            "dbf":                  "CONTROL.bandpass_filter",
            "dbf-high":             "CONTROL.bandpass_filter_band",
            "dbf-low":              "CONTROL.bandpass_filter_band",
            "preamp":               "<vfo>.preamp",
            "rit":                  "CONTROL.rit",
            "squelched":            "CONTROL.rx_status",
            "ctcss-dcs-matched":    "CONTROL.rx_status",
            "discrim-centered":     "CONTROL.rx_status",
            "s-meter":              "CONTROL.rx_status",
            "mic-gain":             "CONTROL.mic_gain",
            "nom-power":            "CONTROL.power",
            "sp-proc":              "CONTROL.speech_proc",
            "act-power":            "CONTROL.tx_metering",
            "swr":                  "CONTROL.tx_metering",
            "alc":                  "CONTROL.tx_metering",
            "mod":                  "CONTROL.tx_metering",
            "tone-mode":            "<vfo>.tone_dcs_mode",
            "tone-freq":            "<vfo>.tone",
            "rpt-offset":           "<vfo>.repeater_offset_frequency",
            "cw-delay":             "CONTROL.cw_delay"
        }

        self.__write_radio_feature_dict = {
            "freq":                 "CONTROL.freq",
            "mode":                 "CONTROL.mode",
            "vfo":                  "CONTROL.vfo_select",
            "ptt":                  "CONTROL.transmit",
            "split":                "CONTROL.split",
            "vox":                  "CONTROL.vox",
            "vox-gain":             "CONTROL.vox_gain",
            "vox-delay":            "CONTROL.vox_delay",
            "bk":                   "CONTROL.bk",
            "atten":                "<vfo>.atten",
            "fm-narrow":            "<vfo>.fm_narrow",
            "cw-dig-narrow":        "<vfo>.cw_dig_narrow",
            "agc-mode":             "CONTROL.agc_mode",
            "nb":                   "CONTROL.noise_blank",
            "dnr":                  "CONTROL.noise_reduce",
            "dnf":                  "CONTROL.notch_auto",
            "dbf":                  "CONTROL.bandpass_filter",
            "dbf-high":             "CONTROL.bandpass_filter_band",
            "dbf-low":              "CONTROL.bandpass_filter_band",
            "preamp":               "<vfo>.preamp",
            "rit":                  "CONTROL.rit",
            "mic-gain":             "CONTROL.mic_gain",
            "nom-power":            "CONTROL.power",
            "sp-proc":              "CONTROL.speech_proc",
            "tone-mode":            "<vfo>.tone_dcs_mode",
            "tone-freq":            "<vfo>.tone",
            "rpt-offset":           "<vfo>.repeater_offset_frequency",
            "cw-delay":             "CONTROL.cw_delay"
        }

#        self.__reverse_read_radio_feature_dict = { }
#        for int_f in self.__read_radio_feature_dict:
#            ext_f = self.__read_radio_feature_dict[int_f]
#            if ext_f in self.__external_to_internal_radio_feature_dict:
#                 self.__external_to_internal_radio_feature_dict[ext_f].append(int_f)
#            else:
#                 self.__external_to_internal_radio_feature_dict[ext_f] = [int_f]


        self.__metadata = {"internal": {"radio": {}, "client": {} },
                           "external": {"radio": {}, "client": {} }}

        for int_f in self.__read_radio_feature_dict:
            ext_f = self.__read_radio_feature_dict[int_f]

            int_f_rt         = ("s-meter", "act-power", "swr", "alc", "mod")
            int_f_important  = ("ptt", "high-swr", "freq", "mode", "vfo")
            int_f_be         = ("squelched", "ctcss-dcs-matched", "discrim-centered", "rit",
                                "atten", "preamp", "fm-narrow", "cw-dig-narrow", "tone-mode", "tone-freq", "rpt-offset")
            
            if int_f in int_f_rt:
                ttl = self.short_ttl
                prio = 10
            elif int_f in int_f_important:
                ttl = self.mid_ttl
                prio = 6
            elif int_f in int_f_be:
                ttl = self.complex_ttl
                prio = 1
            else:
                ttl = self.long_ttl
                prio = 3 

            if ext_f == "CONTROL.rx_status":
                valid_during_tx = False
            else:
                valid_during_tx = True

            if ext_f == "CONTROL.tx_metering":
                valid_during_rx = False
            else:
                valid_during_rx = True

            if ext_f == "CONTROL.rit":
                readable = False
            else:
                readable = True

            if ext_f == "CONTROL.operate" or ext_f == "CONTROL.rx_status" or ext_f == "CONTROL.tx_status" or ext_f == "CONTROL.tx_metering":
                writable = False
            else:
                writable = True

            self.__metadata["internal"]["radio"][int_f]  = {
                "ttl": ttl,
                "valid_during_tx": valid_during_tx,
                "valid_during_rx": valid_during_rx,
                "readable": readable,
                "writable": writable,
                "prio": prio
            }
            self.__metadata["internal"]["client"][int_f] = {
                "ttl": ttl,
                "valid_during_tx": valid_during_tx,
                "valid_during_rx": valid_during_rx,
                "readable": readable,
                "writable": writable,
                "prio": prio
            }
            # if ext_f in self.__metadata["external"]["radio"]:
            if ext_f == "CONTROL.rx_status" and ext_f in self.__metadata["external"]["radio"]:
                ext_ttl  = self.__metadata["external"]["radio"][ext_f]["ttl"]
                ext_prio = self.__metadata["external"]["radio"][ext_f]["prio"]
                if prio > ext_prio:
                    ext_prio = prio
                if ttl < ext_ttl:
                    ext_ttl = ttl
            else:
                ext_prio = prio
                ext_ttl = ttl
            self.__metadata["external"]["radio"][ext_f]  = {
                "ttl": ext_ttl,
                "valid_during_tx": valid_during_tx,
                "valid_during_rx": valid_during_rx,
                "readable": readable,
                "writable": writable,
                "prio": ext_prio
            }
            self.__metadata["external"]["client"][ext_f] = {
                "ttl": ttl,
                "valid_during_tx": valid_during_tx,
                "valid_during_rx": valid_during_rx,
                "readable": readable,
                "writable": writable,
                "prio": prio
            }

        # correct wrong info: this internal feature is not valid during RX,
        # even part of the external feature "CONTROL.tx_status" actually is
        self.__metadata["internal"]["radio"]["high-swr"]["valid_during_rx"] = False

        self.__state = {"current": {}, "old": {}}
        for key in self.__state:
            self.__state[key]["internal"] = {"radio": {}}
            self.__state[key]["external"] = {"radio": {}}

        for internal_feature in self.__read_radio_feature_dict:
            external_feature = self.__read_radio_feature_dict[internal_feature]

            now = datetime.datetime.utcnow()

            self.__state["current"]["internal"]["radio"][internal_feature] = {
                "value": None,
                "timestamp" : now
            }
            self.__state["current"]["external"]["radio"][external_feature] = {
                "value": None,
                "timestamp": now
            }
            self.__state["old"]["internal"]["radio"][internal_feature] = {
                "value": None,
                "timestamp": now
            }
            self.__state["old"]["external"]["radio"][external_feature] = {
                "value": None,
                "timestamp": now
            }

        # default value for non-readable features (will be synced to radio)
        self.__state["current"]["internal"]["radio"]["rit"]["value"]         = "0.0"
        self.__state["current"]["external"]["radio"]["CONTROL.rit"]["value"] = "0.0"

        self.__ptt = False
        self.__vfo = 'VFOA'
        self.__tick = 0
        


    def __sync_client(self, client, syncs):
        if syncs:
            sync_str = ""
            sync_str = sync_str + "tick: " + str(self.__tick) + "\n"
            for sync in syncs:
                sync_str = sync_str + sync + ": " + syncs[sync] + "\n"
            sync_str = sync_str + "end-of-tick\n\n"
            try:
                client.sendall(sync_str)
            except:
                self.__remove_client(client)


    def __sync_radio(self, syncs):
        sync_strs = [ ]
        for int_f in syncs:
            int_v = syncs[int_f]
            ext_f = self.__write_radio_feature_dict[int_f]
            if int_f == "dbf-high":
                ext_v = self.__state["current"]["internal"]["radio"]["dbf-low"]["value"] + " " + syncs[int_f]
            elif int_f == "dbf-low":
                ext_v = syncs[int_f] + " " + self.__state["current"]["internal"]["radio"]["dbf-high"]["value"]
            else:
                ext_v = int_v

            sync_str = "put " + self.__rig_name + "." + ext_f + " " + ext_v
            print "VFO: " + self.__vfo
            sync_str = sync_str.replace("<vfo>", self.__vfo)
            sync_strs.append(sync_str)

        for sync_str in sync_strs:
            self.__rigserve.sendall(sync_str)
            response = self.__rigserve.recv(8192)
            if globals.is_nak(response):
                print "simple_server: warning: sync " + sync_str + " not applied to radio, received " + response

        #for int_f in syncs:
        #    if not self.__metadata["internal"]["radio"][int_f]["readable"]:
        #        self.__state["current"]["internal"]["radio"][int_f]["value"] = syncs[int_f]
        #        ext_f = self.__write_radio_feature_dict[int_f]
        #        if int_f == "rit":
        #            self.__state["current"]["external"]["radio"][ext_f]["value"] = syncs[int_f]
            


    def __read_current_client_state(self, client):
        [r, w, e] = select.select([client], [], [], 0)
        if r:
            r = r[0]
            for f in self.__state["current"]["internal"][client]:
                self.__state["old"]["internal"][client][f]["value"] = self.__state["current"]["internal"][client][f]["value"]
                self.__state["old"]["internal"][client][f]["timestamp"] = self.__state["current"]["internal"][client][f]["timestamp"]
            for f in self.__state["current"]["external"][client]:
                self.__state["old"]["external"][client][f]["value"] = self.__state["current"]["external"][client][f]["value"]
                self.__state["old"]["external"][client][f]["timestamp"] = self.__state["current"]["external"][client][f]["timestamp"]

            line = r.recv(32768)
            if line == "":
                raise EOFError
            lines = line.splitlines()

            for line in lines:
                spl = line.split(": ", 1)
                if len(spl) > 1:
                    f  = spl[0]
                    v  = spl[1]
                    timestamp = datetime.datetime.utcnow()   # now
                    if f in self.__state["current"]["external"][client]:
                        self.__state["current"]["external"][client][f]["value"]     = v
                        self.__state["current"]["external"][client][f]["timestamp"] = timestamp

            self.__external_to_internal_current_client_state(client)

        else:
            # no changes from the client
            for f in self.__state["current"]["internal"][client]:
                self.__state["old"]["internal"][client][f]["value"] = self.__state["current"]["internal"][client][f]["value"]
                self.__state["old"]["internal"][client][f]["timestamp"] = self.__state["current"]["internal"][client][f]["timestamp"]
            for f in self.__state["current"]["external"][client]:
                self.__state["old"]["external"][client][f]["value"] = self.__state["current"]["external"][client][f]["value"]
                self.__state["old"]["external"][client][f]["timestamp"] = self.__state["current"]["external"][client][f]["timestamp"]


    def __external_to_internal_current_client_state(self, c):
        for f in self.__state["current"]["external"][c]:
            for e in self.__state["current"]["external"][c][f]:
                self.__state["current"]["internal"][c][f][e] = self.__state["current"]["external"][c][f][e]


    def __read_current_radio_state(self):
        for f in self.__state["old"]["internal"]["radio"]:
            for e in self.__state["old"]["internal"]["radio"][f]:
                self.__state["old"]["internal"]["radio"][f][e] = self.__state["current"]["internal"]["radio"][f][e]

        for f in self.__state["old"]["external"]["radio"]:
            for e in self.__state["old"]["external"]["radio"][f]:
                self.__state["old"]["external"]["radio"][f][e] = self.__state["current"]["external"]["radio"][f][e]

        now = datetime.datetime.utcnow()

        # discard non-pollable features
        pollable_features = [ ]
        for f in self.__state["current"]["external"]["radio"]:
            if self.__metadata["external"]["radio"][f]["readable"]:
                valid_during_rx = self.__metadata["external"]["radio"][f]["valid_during_rx"]
                valid_during_tx = self.__metadata["external"]["radio"][f]["valid_during_tx"]
                if self.__ptt and valid_during_tx:
                    pollable_features.append(f)
                elif (not self.__ptt) and valid_during_rx:
                    pollable_features.append(f)
                else:
                    self.__state["current"]["external"]["radio"][f]["value"] = "?"

        # discard non-expired features
        expired_features = [ ]
        for f in pollable_features:
            last_read  = self.__state["current"]["external"]["radio"][f]["timestamp"]
            ttl        = self.__metadata["external"]["radio"][f]["ttl"]
            if last_read == None:
                response = self.__get_radio(f)
                if not globals.is_nak(response):
                    self.__state["current"]["external"]["radio"][f]["value"] = response
                    self.__state["current"]["external"]["radio"][f]["timestamp"]  = now                
                expired = False
            else:
                expired = last_read + datetime.timedelta(seconds=ttl) < now
            if expired:
                expired_features.append(f)

        # choose the best one
        max_points = 0.0
        chosen_feature = None
        for ef in expired_features:
            last_read = self.__state["current"]["external"]["radio"][ef]["timestamp"]
            age = now - last_read
            ttl = self.__metadata["external"]["radio"][ef]["ttl"]
            expired_time = age - datetime.timedelta(seconds=ttl)
            expired_seconds = float(expired_time.total_seconds())
            good_luck = random.randint(0, 100) / 100.0
            prio = self.__metadata["external"]["radio"][ef]["prio"]
            points = prio * expired_seconds * (1 + good_luck)
            if points > max_points:
                max_points = points
                chosen_feature = ef

        # poll
        if chosen_feature != None:
            response = self.__get_radio(chosen_feature)
            if globals.is_nak(response):
                self.__state["current"]["external"]["radio"][chosen_feature]["value"] = "?"
            else:
                self.__state["current"]["external"]["radio"][chosen_feature]["value"] = response
            self.__state["current"]["external"]["radio"][chosen_feature]["timestamp"] = now

        self.__external_to_internal_current_radio_state()


    def __get_radio(self, ext_f):
        command = "get " + self.__rig_name + "." + ext_f
        command = command.replace("<vfo>", self.__vfo)
        self.__rigserve.sendall(command)
        response = self.__rigserve.recv(8192)
        response = response.splitlines()[0]   # remove tailing end-of-line, if any
        return response


    def __external_to_internal_current_radio_state(self):
        for int_f in self.__state["current"]["internal"]["radio"]:
            ext_f = self.__read_radio_feature_dict[int_f]
            ext_v = self.__state["current"]["external"]["radio"][ext_f]["value"]

            if ext_v != None and ext_v != "?":
                spl = None
                if int_f == "freq":
                    int_v = self.__freq_from_external_radio(ext_v)
                elif int_f == "mode":
                    int_v = self.__mode_from_external_radio(ext_v)
                elif int_f == "squelched":
                    spl = ext_v.split(" ", 7)
                    if len(spl) != 8:
                        int_v = "?"
                    else:
                        int_v = spl[1]
                elif int_f == "ctcss-dcs-matched":
                    spl = ext_v.split(" ", 7)
                    if len(spl) != 8:
                        int_v = "?"
                    else:
                        int_v = spl[3]
                elif int_f == "discrim-centered":
                    spl = ext_v.split(" ", 7)
                    if len(spl) != 8:
                        int_v = "?"
                    else:
                        int_v = spl[5]
                elif int_f == "s-meter":
                    spl = ext_v.split(" ", 7)
                    if len(spl) != 8:
                        int_v = "?"
                    else:
                        int_v = spl[7]
                elif int_f == "act-power":
                    spl = ext_v.split(" ", 7)
                    if len(spl) != 8:
                        int_v = "?"
                    else:
                        int_v = spl[1]
                elif int_f == "alc":
                    spl = ext_v.split(" ", 7)
                    if len(spl) != 8:
                        int_v = "?"
                    else:
                        int_v = spl[3]
                elif int_f == "swr":
                    spl = ext_v.split(" ", 7)
                    if len(spl) != 8:
                        int_v = "?"
                    else:
                        int_v = spl[5]
                elif int_f == "mod":
                    spl = ext_v.split(" ", 7)
                    if len(spl) != 8:
                        int_v = "?"
                    else:
                        int_v = spl[7]
                elif int_f == "dbf-low":
                    spl = ext_v.split(" ", 1)
                    if len(spl) != 2:
                        int_v = "?"
                    else:
                        int_v = spl[0]
                elif int_f == "dbf-high":
                    spl = ext_v.split(" ", 1)
                    if len(spl) != 2:
                        int_v = "?"
                    else:
                        int_v = spl[1]
                elif int_f == "ptt":
                    spl = ext_v.split(" ", 3)
                    if len(spl) != 4:
                        int_v = "?"
                    else:
                        int_v = spl[1]

                    if "TRUE" in int_v.upper():
                        self.__ptt = True
                    else:
                        self.__ptt = False
                elif int_f == "high-swr":
                    spl = ext_v.split(" ", 3)
                    if len(spl) != 4:
                        int_v = "?"
                    else:
                        int_v = spl[3]
                elif int_f == "vfo":
                    if int_v == "VFOA" or int_v == "VFOB":
                        self.__vfo = int_v
                else:
                    int_v = ext_v
            else:
                int_v = "?"
            self.__state["current"]["internal"]["radio"][int_f]["value"]            = int_v
            self.__state["current"]["internal"]["radio"][int_f]["timestamp"]        = self.__state["current"]["external"]["radio"][ext_f]["timestamp"]


    def __freq_from_external_radio(self, value):
        if value == None:
            return None
        spl = value.split(" ", 4)
        freq = 0
        for i in range(4):
            my_byte = int(spl[i], 16)
            freq = freq * 10
            freq = freq + my_byte / 16
            freq = freq * 10
            freq = freq + my_byte % 16
        freq = freq * 10
        return str(freq)


    def __mode_from_external_radio(self, value):
        if value == None:
            return None
        spl = value.split(" ", 4)
        raw_mode = int(spl[4], 16)
        raw_mode = raw_mode % 16
        modes_dict = {
            0:  "LSB",
            1:  "USB",
            2:  "CW",
            3:  "CWR",
            4:  "AM",
            6:  "WFM",
            8:  "FM",
            10: "DIG",
            12: "PKT"
        }
        if raw_mode in modes_dict:
            return modes_dict[raw_mode]
        return "?"


    def __get_client_diffs(self, c):
        diffs = { }
        for f in self.__state["current"]["internal"][c]:
            old_v      = self.__state["old"]["internal"][c][f]["value"]
            current_v  = self.__state["current"]["internal"][c][f]["value"]
            if old_v != current_v:
                diffs[f] = current_v
        return diffs


    def __get_radio_diffs(self):
        diffs = { }
        for f in self.__state["current"]["internal"]["radio"]:
            old_v = self.__state["old"]["internal"]["radio"][f]["value"]
            my_dict = self.__state["current"]["internal"]["radio"][f]
            current_v = my_dict["value"]

            if current_v == "" or current_v == None:
                current_v = "?"
            if self.__ptt and not self.__metadata["internal"]["radio"][f]["valid_during_tx"]:
                current_v = "?"
            if not self.__ptt and not self.__metadata["internal"]["radio"][f]["valid_during_rx"]:
                current_v = "?"

            if old_v != current_v:
                diffs[f] = current_v

        return diffs


    def __add_client(self, c):
        self.__state["current"]["internal"][c] = {}
        self.__state["current"]["external"][c] = {}
        self.__state["old"]["internal"][c] = {}
        self.__state["old"]["external"][c] = {}
        for f in self.__read_radio_feature_dict:
            self.__state["current"]["internal"][c][f]  =  {"value": None, "timestamp": None, "ttl": None}
            self.__state["current"]["external"][c][f]  =  {"value": None, "timestamp": None, "ttl": None}
            self.__state["old"]["internal"][c][f]      =  {"value": None, "timestamp": None, "ttl": None}
            self.__state["old"]["external"][c][f]      =  {"value": None, "timestamp": None, "ttl": None}
        self.__clients.append(c)


    def __remove_client(self, c):
        try:
            c.close()
        except:
            pass
        del self.__state["current"]["internal"][c]
        del self.__state["current"]["external"][c]
        del self.__state["old"]["internal"][c]
        del self.__state["old"]["external"][c]
        self.__clients.remove(c)


    def __sigterm_handler(self, signalnum, frame):
        self.__terminating = True


    def __connect_to_rigserve(self):
        self.__rigserve = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        counter = 0
        while True:
            try:
               counter = counter + 1
               self.__rigserve.connect(('127.0.0.1', self.rigserve_port))
               break
            except:
               if counter < 65:
                   sleep(1)
               else:
                   print "Simple compat. service: cannot connect to main rigserve server, exiting."
                   exit(1)

        self.__rigserve.recv(1024)    # Welcome message


    def __write_expired_non_readable_radio_features(self):
        writes_dict = { }

        for int_f in self.__metadata["internal"]["radio"]:
            now = datetime.datetime.utcnow()
            readable = self.__metadata["internal"]["radio"][int_f]["readable"]
            if not readable:
                timestamp = self.__state["current"]["internal"]["radio"][int_f]["timestamp"]
                ttl = self.__metadata["internal"]["radio"][int_f]["ttl"]
                expired = timestamp + datetime.timedelta(0, ttl) < now
                if expired:
                    if int_f == "rit":
                        value = str(self.__state["current"]["internal"]["radio"][int_f]["value"])
                        writes_dict[int_f] = "put " + self.__rig_name + ".CONTROL.rit " + value

        for w in writes_dict:
            self.__rigserve.sendall(writes_dict[w])
            response = self.__rigserve.recv(8192)
            if globals.is_nak(response):
                print "simple_server: warning: cannot write " + w + ": " + response
            else:
                now = datetime.datetime.utcnow()
                self.__state["current"]["internal"]["radio"][w]["timestamp"] = now
                if w == "rit":
                    self.__state["current"]["external"]["radio"]["CONTROL.rit"]["timestamp"] = now
	

    def target(self, *args):
        for a in args:
            try:
                a = str(a)
                spl = a.split("=", 2)
            except:
                continue
            if len(spl) == 1:
                self.__parsed_args[spl[0]] = ""
            elif len(spl) == 2:
                self.__parsed_args[spl[0]] = spl[1]
        try:
            self.__remote_udp_port = int(self.__parsed_args["remote_udp_port"])
        except:
            print "bad udp port"
            return

        signal.signal(signal.SIGTERM, self.__sigterm_handler)

        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        is_done = False
        tries = 0
        while not is_done and tries < 65:
            tries = tries + 1
            try:
                listen_socket.bind((self.__parsed_args["listen_addr"], int(self.__parsed_args["listen_tcp_port"])))
                is_done = True
            except:
                is_done = False
                time.sleep(1)
        if not is_done:
            return

        listen_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        listen_socket.listen(5)
        listen_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.__connect_to_rigserve()
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.__udp_socket.bind((self.__parsed_args["listen_addr"], self.__parsed_args["listen_udp_port"]))
        self.__clients = [ ]

        start = datetime.datetime.utcnow()
        while not self.__terminating:
            # discover which clients need attention
            selected = [listen_socket]
            for client in self.__clients:
                selected.append(client)

            try:
                r, w, e = select.select(selected, [], [], self.client_timeout)
            except:
                r = []
                w = []
                e = []
                print traceback.format_exc()
                self.__terminating = True

            # accept any new client
            new_clients = [ ]
            if listen_socket in r:
                [new_socket, new_addr] = listen_socket.accept()
                new_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                new_socket.setblocking(1)
                new_socket.settimeout(self.client_timeout)
                new_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.__add_client(new_socket)
                new_clients.append(new_socket)

            # read from radio
            self.__read_current_radio_state()

            # convert format
            self.__external_to_internal_current_radio_state()

            # write expired non-readable features to radio
            # (this allows keeping radio and clients synced if
            # somebody changes a non-readable feature in the radio)
            self.__write_expired_non_readable_radio_features()

            # discover what has changed in the radio (the "diffs")
            radio_diffs = self.__get_radio_diffs()

            client_diffs = { }
            for client in self.__clients:
                client_diffs[client] = { }
            for client in r:
                if not client is listen_socket:
                    # read from client
                    try:
                        self.__read_current_client_state(client)
                    except:
                        self.__remove_client(client)
                        del client_diffs[client]
                        if client in new_clients:
                            new_clients.remove(client)
                        continue

                    # convert format
                    self.__external_to_internal_current_client_state(client)

                    # discover what has changed in the client (the "diffs")
                    client_diffs[client] = self.__get_client_diffs(client)

            # calculate changes to be done (the "syncs"):
            radio_syncs  = { }    # changes to be done in the radio
            client_syncs = { }    # changes to be done in each client
            for client in self.__clients:
                client_syncs[client] = { }

            # all changes made in the radio, but in none of the clients, are synced to all clients
            for d in radio_diffs:
                synced = True
                for c in self.__clients:
                    if d in client_diffs[c]:
                        synced = False
                if synced:
                    for c in self.__clients:
                        client_syncs[c][d] = radio_diffs[d]

            # new clients get a full sync from the radio
            for nc in new_clients:
                for f in self.__state["current"]["internal"]["radio"]:
                    v = self.__state["current"]["internal"]["radio"][f]["value"]
                    if v == None:
                        v = "?"
                    client_syncs[nc][f] = v

            # all features changed in a client are synced to the radio and to all clients
            # (if more than one client changes the same feature, only one of them will
            # get the feature synced; the other ones will be lost)
            for c1 in self.__clients:
                for d in client_diffs[c1]:
                    change = client_diffs[c1][d]
                    radio_syncs[d] = change
                    for c2 in self.__clients:
                        client_syncs[c2][d] = change

            # all changes made in the client are synced to the radio, unless client and radio values are equal
            #for c in client_diffs:
            #    for d in client_diffs[c]:
            #        if client_diffs[c][d] != self.__state["current"]["internal"]["radio"][d]["value"]:
            #            radio_syncs[d] = client_diffs[c][d]

            # sync clients using TCP
            # (deprecated, use UDP for better performance)
            #for c in self.__clients:
            #    self.__sync_client(c, client_syncs[c])

            # sync radio
            # _do_ use TCP now; the radio syncs are critical and should be always applied
            if radio_syncs:
                self.__sync_radio(radio_syncs)

            # fully sync clients using UDP
            full_sync_str = "tick: " + str(self.__tick) + "\n"
            for f in self.__state["current"]["internal"]["radio"]:
                v = self.__state["current"]["internal"]["radio"][f]["value"]
                full_sync_str += f + ": " + v + "\n"
            for c in self.__clients:
                ip = c.getsockname()[0]
                port = self.__remote_udp_port
                self.__udp_socket.sendto(full_sync_str, (ip, port))

            self.__tick = self.__tick + 1

            window = 80
            if self.__tick % window == 0:
                now = datetime.datetime.utcnow()
                runtime = now - start
                runtime_s = runtime.days * 86400 + runtime.seconds + runtime.microseconds / 1000000.0
                tps = window / runtime_s
                print str(tps) + " tick/s last window"
                start = now
 

        for c in self.__clients:
            self.__remove_client(c)

        listen_socket.close()
        self.__rigserve.send("quit")
        self.__rigserve.close()
        self.__udp_socket.close()

