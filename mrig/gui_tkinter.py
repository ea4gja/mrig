#!/usr/bin/env python
#
# File: gui_tkinter.py
# Version: 1.0
#
# mrig: GUI client for simple server, implemented in Tkinter
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


import dial
import level
from Tkinter import N, W, E, S
import Tkinter
import time
import datetime
import select
import math



class FeatureWidget(object):
   def __init__(self, parent, feature):
      self.__parent = parent
      self.feature = feature
      self.value = ""
      parent.add_feature_widget_to_list(self)

   def user_action(self, event=None):
      # invoked when the user changes the widget
      new_value            = self.calculate_value()
      self.__parent.self_notify_all_widgets(self.feature, new_value)
      self.__parent.block_feature(self.feature)
      self.__parent.send_to_radio(self.feature, new_value)

   def notified(self, feature, new_value):
      # invoked when the associated feature has changed in the server
      if not self.is_blocked(self.feature) and feature == self.feature:
         self.value = new_value
         self.reconfig()

   def self_notified(self, feature, new_value):
      if feature == self.feature:
         self.value = new_value
         self.reconfig()

   def reconfig(self):
      # changes the widget config options according to the current value of the feature
      pass

   def calculate_value(self):
      # gets the current value of the feature
      return ""

   def is_blocked(self, feature):
      return self.__parent.is_blocked(feature)



class PermanentButtonFeature(FeatureWidget, Tkinter.Button):
   def __init__(self, parent, feature, color_down="black", color_up="green", **options):
      FeatureWidget.__init__(self, parent, feature)
      options["text"] = feature.upper()
      options["command"] = self.user_action
      Tkinter.Button.__init__(self, parent, **options)
      self.__color_down = color_down
      self.__color_up = color_up
      self.value = ""
      self.reconfig()

   def reconfig(self):
      if self.value != None:
         upper = self.value.upper()
         if "TRUE" in upper:
            self.config(fg=self.__color_up)
         else:
            self.config(fg=self.__color_down)

   def calculate_value(self):
      if self.value != None:
         upper = self.value.upper()
         if "TRUE" in upper:
            current_val = True
         else:
            current_val = False
         self.value = str(not current_val)
         return self.value



class MomentaryButtonFeature(FeatureWidget, Tkinter.Button):
   def __init__(self, parent, feature, color_down="black", color_up="green", **options):
      FeatureWidget.__init__(self, parent, feature)
      options["text"] = feature.upper()
      Tkinter.Button.__init__(self, parent, **options)
      self.__pushed = False
      self.bind("<Button-1>", self.__set_pushed)
      self.bind("<ButtonRelease-1>", self.__clear_pushed)
      self.__color_down = color_down
      self.__color_up = color_up
      self.value = ""
      self.reconfig()

   def __set_pushed(self, event):
      self.__pushed = True
      self.user_action()

   def __clear_pushed(self, event):
      self.__pushed = False
      self.user_action()

   def reconfig(self):
      if self.__pushed != None:
         if self.__pushed:
            self.config(fg=self.__color_up)
         else:
            self.config(fg=self.__color_down)

   def calculate_value(self):
      self.value = str(self.__pushed)
      return self.value



class ListFeature(FeatureWidget, Tkinter.Menubutton):
   def __init__(self, parent, feature, value_list, **options):
      FeatureWidget.__init__(self, parent, feature)
      self.__value = Tkinter.StringVar()
      self.__value.set(value_list[0])
      self.__displayed_text = Tkinter.StringVar()
      options["textvariable"] = self.__displayed_text
      Tkinter.Menubutton.__init__(self, parent, **options)
      self.menu = Tkinter.Menu(self, tearoff=0)
      for v in value_list:
         self.menu.add_radiobutton(label=v, value=v, variable=self.__value, command=self.user_action)
      self["menu"] = self.menu
      self.__value_list = value_list
      self.reconfig()

   def calculate_value(self):
      self.value = self.__value.get()
      return self.value

   def notified(self, feature, value):
      if not self.is_blocked(self.feature) and feature == self.feature:
         if value in self.__value_list:
            self.__value.set(value)
            self.reconfig()

   def reconfig(self):
      my_str = self.feature + ": " + self.__value.get()
      my_str = my_str.upper()
      self.__displayed_text.set(my_str)



class EntryFeature(FeatureWidget, Tkinter.Entry):
   def __init__(self, parent, feature, process_value=None, **options):
      FeatureWidget.__init__(self, parent, feature)
      Tkinter.Entry.__init__(self, parent, **options)
      self.__process_value = process_value
      self.bind("<Return>", self.user_action)
      self.reconfig()

   def reconfig(self):
      pass

   def calculate_value(self):
      self.value = self.get()
      if self.__process_value != None:
         self.value = self.__process_value(self.value)
      return self.value

   def user_action(self, event=None):
      super(EntryFeature, self).user_action(event)
      self.delete(0, Tkinter.END)




class DialFeature(FeatureWidget, dial.Dial):
   def __init__(self, parent, feature, steps_per_turn, external_calculate_value, **options):
      FeatureWidget.__init__(self, parent, feature)
      dial.Dial.__init__(self, parent, **options)
      self.value = "1"
      self._steps_per_turn = steps_per_turn
      self._old_steps = 0
      self._current_steps = 0
      self._external_calculate_value = external_calculate_value
      self.register_change_callback(self.turned)
      self.reconfig()

   def turned(self, absolute_turns):
      current_steps = self._current_steps
      new_steps = absolute_turns * float(self._steps_per_turn)
      if new_steps < 0:
         new_steps = new_steps - 1
      new_steps = int(new_steps)
      if current_steps != new_steps:
         self._old_steps = self._current_steps
         self._current_steps = new_steps
         self.user_action()

   def calculate_value(self):
      delta_steps = self._current_steps - self._old_steps
      try:
         value = float(self.value)
      except:
         return ""
      value = self._external_calculate_value(value, -delta_steps)   # - is clockwise, + is counterclockwise
      return str(value)



class ListDialFeature(DialFeature):
   def __init__(self, parent, feature, steps_per_turn, value_list, **options):
      DialFeature.__init__(self, parent, feature, steps_per_turn, lambda value, delta_steps: self.calculate_value, **options)
      self.index = 0
      self.value_list = value_list
      self.value = str(value_list[self.index])

   def calculate_value(self):
      if not self.value_list:
         return ""

      delta_steps = self._current_steps - self._old_steps

      self.index = self.index - delta_steps   # + is counterclockwise, - is clockwise
      if self.index < 0:
         self.index = 0
      if self.index >= len(self.value_list):
         self.index = len(self.value_list) - 1

      value = self.value_list[self.index]
      return str(value)

   def notified(self, feature, new_value):
      if not self.is_blocked(self.feature) and feature == self.feature:
         super(ListDialFeature, self).notified(feature, new_value)
         for i in range(len(self.value_list)):
            if str(self.value_list[i]) == str(new_value):
               self.index = i
               break


class LevelFeature(FeatureWidget, level.Level):
   def __init__(self, parent, feature, validate_func, percent_func, **options):
      FeatureWidget.__init__(self, parent, feature)
      level.Level.__init__(self, parent, **options)
      self.__validate_func = validate_func
      self.__percent_func = percent_func
      self.set_percent(0.0)
      self.reconfig()

   def reconfig(self):
      if self.value == None or "?" in self.value or self.value == "":
         self.set_percent(0.0)
      else:
         if self.__validate_func(self.value):
            percent = self.__percent_func(self.value)
            if percent > 100:
               percent = 100.0
            if percent < 0:
               percent = 0.0
            self.set_percent(percent)

   def calculate_value(self):
      return ""   # this class currently supports just read-only features (s-meter, ...)




class LabelFeature(FeatureWidget, Tkinter.Label):
   def __init__(self, parent, feature, prefix, suffix, test_value, **options): #, width=2, height=1, **options):
      FeatureWidget.__init__(self, parent, feature)
      Tkinter.Label.__init__(self, parent, options)
      self.__prefix = prefix
      self.__suffix = suffix
      self.__test_value = test_value
      self.reconfig()

   def reconfig(self):
      if self.value != None:
         my_text = self.__prefix + self.value + self.__suffix
         self.config(text=my_text)

   def calculate_value(self):
      return ""   # this class supports just read-only features (s-meter, ...)




class ColorLabelFeature(FeatureWidget, Tkinter.Label):
   def __init__(self, parent, feature, color_down="black", color_up="green", **options): #, width=1, height=1):
      FeatureWidget.__init__(self, parent, feature)
      self.__false_color = color_down
      self.__true_color = color_up
      Tkinter.Label.__init__(self, parent, options) #, width=int(hzoom*width), height=int(vzoom*height))
      self.value = "True"
      self.reconfig()

   def reconfig(self):
      if self.value != None:
         if "TRUE" in self.value.upper():
            my_color = self.__true_color
         else:
            my_color = self.__false_color
         self.config(foreground=my_color)

   def calculate_value(self):
      return ""   # this class supports just read-only features (s-meter, ...)




class List(Tkinter.Menubutton):
   def __init__(self, parent, value_list, callback, **options):
      self.__my_value = Tkinter.StringVar()
      self.__my_displayed_text = Tkinter.StringVar()
      options["textvariable"] = self.__my_displayed_text
      Tkinter.Menubutton.__init__(self, parent, options)
      self.menu = Tkinter.Menu(self, tearoff=0)
      for v in value_list:
         self.menu.add_radiobutton(label=v + " speed", value=v, variable=self.__my_value, command=self.set_value)
      self["menu"] = self.menu
      self.__my_value.set(value_list[0])
      self.__callback = callback
      self.set_value()
      self.__callback(self.__my_value.get())

   def set_value(self):
      my_str = "SPEED: " + self.__my_value.get() + "Hz"
      self.__callback(self.__my_value.get())
      self.__my_displayed_text.set(my_str)



s_meter_levels = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "+10dB", "+20dB", "+30dB", "+40dB", "+50dB", "+60dB")
s_meter_level_percent_dict = {
   "0":     0  * 100.0 / 15.0,
   "1":     1  * 100.0 / 15.0,
   "2":     2  * 100.0 / 15.0,
   "3":     3  * 100.0 / 15.0,
   "4":     4  * 100.0 / 15.0,
   "5":     5  * 100.0 / 15.0,
   "6":     6  * 100.0 / 15.0,
   "7":     7  * 100.0 / 15.0,
   "8":     8  * 100.0 / 15.0,
   "9":     9  * 100.0 / 15.0,
   "+10dB": 10 * 100.0 / 15.0,
   "+20dB": 11 * 100.0 / 15.0,
   "+30dB": 12 * 100.0 / 15.0,
   "+40dB": 13 * 100.0 / 15.0,
   "+50dB": 14 * 100.0 / 15.0,
   "+60dB": 15 * 100.0 / 15.0,
}

for i in range(16):
   key = str(s_meter_levels[i])
   val = i * 100.0 / 15.0
   s_meter_level_percent_dict[key] = val
 
#for i in range(10):
#   val = i * 100.0 / 15.0
#   s_meter_level_percent_dict[i] = val




def process_freq(freq):
   try:
      tmp_freq = str(freq)
      if tmp_freq.endswith("k") or tmp_freq.endswith("K"):
         tmp_freq = tmp_freq[:-1]
         float_freq = float(tmp_freq) * 1000
      elif tmp_freq.endswith("m") or tmp_freq.endswith("M"):
         tmp_freq = tmp_freq[:-1]
         float_freq = float(tmp_freq) * 1000000
      else:
         float_freq = float(tmp_freq)
      return str(int(float_freq))
   except:
      return ""




class gui_Tkinter(Tkinter.Frame):
   def __init__(self, root, **options):
      self.__root = root
      self.__tcp = options["tcp"]
      self.__udp = options["udp"]
      self.blocked_features = { }

      Tkinter.Frame.__init__(self, root)

      self.__tuning_speed = 0

      # build widgets
      self.__feature_widgets = [ ]
      tcp = self.__tcp
      udp = self.__udp

      self.__split_pbutton          =  PermanentButtonFeature(self, "split")
      self.__vox_pbutton            =  PermanentButtonFeature(self, "vox", width=2, height=1)
      self.__bk_pbutton             =  PermanentButtonFeature(self, "bk", width=2, height=1)
      self.__atten_pbutton          =  PermanentButtonFeature(self, "atten", width=2, height=1)
      self.__fm_narrow_pbutton      =  PermanentButtonFeature(self, "fm-narrow", width=2, height=1)
      self.__cw_dig_narrow_pbutton  =  PermanentButtonFeature(self, "cw-dig-narrow", width=2, height=1)
      self.__nb_pbutton             =  PermanentButtonFeature(self, "nb", width=2, height=1)
      self.__dnr_pbutton            =  PermanentButtonFeature(self, "dnr", width=2, height=1)
      self.__dnf_pbutton            =  PermanentButtonFeature(self, "dnf", width=2, height=1)
      self.__dbf_pbutton            =  PermanentButtonFeature(self, "dbf", width=2, height=1)
      self.__preamp_pbutton         =  PermanentButtonFeature(self, "preamp", width=2, height=1)
      self.__sp_proc_pbutton        =  PermanentButtonFeature(self, "sp-proc", width=2, height=1)

      self.__ptt_mbutton            =  MomentaryButtonFeature(self, "ptt", width=4, height=1)

      self.__mode_dlist             =  ListFeature(self, "mode", ("LSB", "USB", "CW", "CWR", "AM", "FM", "WFM", "DIG", "PKT"), width=3, height=1)
      self.__vfo_dlist              =  ListFeature(self, "vfo",  ("VFOA", "VFOB"), width=3, height=1)
      self.__agc_mode_dlist         =  ListFeature(self, "agc-mode", ("AUTO", "FAST", "SLOW"), width=3, height=1)
      self.__tone_dcs_mode_dlist    =  ListFeature(self, "tone-mode", ("None", "Tone", "ToneSquelch", "DCS", "DCSSquelch"), width=3, height=1)
      tone = (
         "67.0",
         "69.3",
         "71.9",
         "74.4",
         "77.0",
         "79.7",
         "82.5",
         "85.4",
         "88.5",
         "91.5",
         "94.8",
         "97.4",
         "100.0",
         "103.5",
         "107.2",
         "110.9",
         "114.8",
         "118.8",
         "123.0",
         "127.3",
         "131.8",
         "136.5",
         "141.3",
         "146.2",
         "151.4",
         "156.7",
         "159.8",
         "162.2",
         "165.5",
         "167.9",
         "171.3",
         "173.8",
         "177.3",
         "179.9",
         "183.5",
         "186.2",
         "189.9",
         "192.8",
         "196.6",
         "199.5",
         "203.5",
         "206.5",
         "210.7",
         "218.1",
         "225.7",
         "229.1",
         "233.6",
         "241.8",
         "250.3",
         "254.1"
      )
      self.__tone_dlist             =  ListFeature(self, "tone-freq", tone, width=3, height=1)

      self.__freq_entry             =  EntryFeature(self, "freq", process_freq, width=9)
      self.__rpt_offset_entry       =  EntryFeature(self, "rpt-offset", process_freq, width=9)

      self.__freq_dial              =  DialFeature(self, "freq", 15, lambda value, delta_steps: int(value + delta_steps * self.__tuning_speed), width="4c", height="4c")
      self.__rit_dial               =  DialFeature(self, "rit", 15, lambda value, delta_steps: value + delta_steps * 0.01, width="2c", height="2c")
      self.__vox_gain_dial          =  DialFeature(self, "vox-gain", 15, lambda value, delta_steps: int(value + delta_steps), width="2c", height="2c")
      self.__vox_delay_dial         =  DialFeature(self, "vox-delay", 15, lambda value, delta_steps: int(value + delta_steps * 100), width="2c", height="2c")
      self.__mic_gain_dial          =  DialFeature(self, "mic-gain", 20, lambda value, delta_steps: int(value + delta_steps), width="2c", height="2c")
      self.__nominal_power_dial     =  DialFeature(self, "nom-power", 20, lambda value, delta_steps: int(value + delta_steps), width="2c", height="2c")
      self.__cw_delay_dial          =  DialFeature(self, "cw-delay", 15, lambda value, delta_steps: int(value + delta_steps * 100), width="2c", height="2c")

      low_cutoff = (
         100,
         160,
         220,
         280,
         340,
         400,
         460,
         520,
         580,
         640,
         700,
         760,
         820,
         880,
         940,
         1000
      )
      high_cutoff = (
         1000,
         1160,
         1320,
         1480,
         1650,
         1800,
         1970,
         2130,
         2290,
         2450,
         2610,
         2770,
         2940,
         3100,
         3260,
         3420,
         3580,
         3740,
         3900,
         4060,
         4230,
         4390,
         4550,
         4710,
         4870,
         5030,
         5190,
         5390,
         5520,
         5680,
         5840,
         6000
      )
      self.__dbf_low_listdial       =  ListDialFeature(self, "dbf-low", 15, low_cutoff, width="2c", height="2c")
      self.__dbf_high_listdial      =  ListDialFeature(self, "dbf-high", 15, high_cutoff, width="2c", height="2c")

      self.__power_level            =  LevelFeature(self, "act-power", lambda v: float(v) >= 0 and float(v) <= 100, lambda v: float(v), width=4, height=0.5)
      self.__alc_level              =  LevelFeature(self, "alc", lambda v: float(v) >= 0 and float(v) <= 100, lambda v: float(v), width=4, height=0.5)
      self.__mod_level              =  LevelFeature(self, "mod", lambda v: float(v) >= 0 and float(v) <= 100, lambda v: float(v), width=4, height=0.5)
      self.__swr_level              =  LevelFeature(self, "swr", lambda v: float(v) >= 1, lambda v: (float(v)-1) * 100.0 / 5.0, width=4, height=0.5)
      self.__s_meter_level          =  LevelFeature(self, "s-meter", lambda v: v in s_meter_levels, lambda v: s_meter_level_percent_dict[v], width=9, height=0.5)

      self.__vox_gain_dlabel        =  LabelFeature(self, "vox-gain", "VOX gain\n", "", "100")
      self.__vox_delay_dlabel       =  LabelFeature(self, "vox-delay" , "VOX delay\n", " ms", "1000")
      self.__dbf_low_dlabel         =  LabelFeature(self, "dbf-low", "dbf low cutoff\n", " Hz", "123")
      self.__dbf_high_dlabel        =  LabelFeature(self, "dbf-high", "dbf high cutoff\n", " Hz", "1234")
      self.__mic_gain_dlabel        =  LabelFeature(self, "mic-gain", "MIC gain\n", " %", "100")
      self.__nominal_power_dlabel   =  LabelFeature(self, "nom-power", "", " W", "100")
      self.__nominal_power_2_dlabel =  LabelFeature(self, "nom-power", "Nom.\n", " W", "100")
      self.__cw_delay_dlabel        =  LabelFeature(self, "cw-delay", "CW delay\n", " ms", "1000")
      self.__power_dlabel           =  LabelFeature(self, "act-power", "Power ", " W", "100")
      self.__alc_dlabel             =  LabelFeature(self, "alc", "ALC ", " %", "100")
      self.__mod_dlabel             =  LabelFeature(self, "mod", "Mod ", "", "100")
      self.__swr_dlabel             =  LabelFeature(self, "swr", "SWR ", ":1", "1.2")
      self.__freq_dlabel            =  LabelFeature(self, "freq", "", " Hz", "432000000", font=("LKLUG", 40))
      self.__mode_dlabel            =  LabelFeature(self, "mode", "", "", "LSB")
      self.__vfo_dlabel             =  LabelFeature(self, "vfo", "", "", "VFOA")
      self.__rit_dlabel             =  LabelFeature(self, "rit", "RIT ", " kHz", "+2.54")
      self.__rit_2_dlabel           =  LabelFeature(self, "rit", "RIT ", " kHz", "+1.23")
      self.__rpt_offset_dlabel      =  LabelFeature(self, "rpt-offset", "Rpt. input ", " Hz", "7600000")
      self.__s_meter_dlabel         =  LabelFeature(self, "s-meter", "S", "", "9+60")
      self.__tone_dlabel            =  LabelFeature(self, "tone-freq", "Tone ", " Hz", "1.0")
      # self.__tone_dcs_mode_dlabel   =  LabelFeature(self, "tone-mode", "T. mode ", "", "?")

      self.__ptt_colorlabel         =  ColorLabelFeature(self, "ptt", text="PTT", color_down=self.cget("background"), color_up="black")
      self.__high_swr_colorlabel    =  ColorLabelFeature(self, "high-swr", text="HIGH SWR!", color_down=self.cget("background"), color_up="red")
      self.__split_colorlabel       =  ColorLabelFeature(self, "split", color_down=self.cget("background"), text="Split", color_up="black")


      self.__mode_1_label           =  Tkinter.Label(self, text="Mode")
      self.__vfo_1_label            =  Tkinter.Label(self, text="VFO")
      self.__agc_mode_1_label       =  Tkinter.Label(self, text="AGC mode")
      self.__freq_1_label           =  Tkinter.Label(self, text="Freq")
      self.__rpt_offset_1_label     =  Tkinter.Label(self, text="Rpt. offset")
      self.__tuning_speed_list      =  List(self, ("10", "100", "500", "1k", "2.5k", "5k", "9k", "10k", "12.5k", "25k", "100k", "1M"), self.set_tuning_speed, text="Tune speed")
      
      self.__dummy_widgets = [ ]
      

      # where to draw each widget
      self.__freq_dlabel.grid(row=0, column=0, rowspan=1, columnspan=10, sticky=N+S+E+W)

      self.__rpt_offset_dlabel.grid(row=1, column=0, rowspan=1, columnspan=4, sticky=N+S+E+W)
      self.__tone_dcs_mode_dlist.grid(row=1, column=4, rowspan=1, columnspan=3, sticky=N+S+E+W)
      self.__tone_dlist.grid(row=1, column=7, rowspan=1, columnspan=3, sticky=N+S+E+W)

      self.__rit_dlabel.grid(row=2, column=0, rowspan=1, columnspan=3, sticky=N+S+E+W)
      self.__mode_dlabel.grid(row=2, column=3, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__vfo_dlabel.grid(row=2, column=4, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__split_colorlabel.grid(row=2, column=5, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__nominal_power_dlabel.grid(row=2, column=6, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__ptt_colorlabel.grid(row=2, column=7, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__high_swr_colorlabel.grid(row=2, column=8, rowspan=1, columnspan=2, sticky=N+S+E+W)

      self.__s_meter_dlabel.grid(row=3, column=0, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__s_meter_level.grid(row=3, column=1, rowspan=1, columnspan=9, sticky=N+S+E+W)
      self.__s_meter_level.set_percent(50)

      self.__alc_dlabel.grid(row=4, column=0, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__alc_level.grid(row=4, column=1, rowspan=1, columnspan=4, sticky=N+S+E+W)
      self.__alc_level.set_percent(100)
      self.__power_dlabel.grid(row=4, column=5, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__power_level.grid(row=4, column=6, rowspan=1, columnspan=4, sticky=N+S+E+W)
      self.__power_level.set_percent(100)

      self.__mod_dlabel.grid(row=5, column=0, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__mod_level.grid(row=5, column=1, rowspan=1, columnspan=4, sticky=N+S+E+W)
      self.__swr_dlabel.grid(row=5, column=5, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__swr_level.grid(row=5, column=6, rowspan=1, columnspan=4, sticky=N+S+E+W)

      self.__freq_1_label.grid(row=6, column=0, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__freq_entry.grid(row=6, column=1, rowspan=1, columnspan=4, sticky=N+S+E+W)
      self.__rpt_offset_1_label.grid(row=6, column=5, rowspan=1, columnspan=1, sticky=N+S+E+W)
      self.__rpt_offset_entry.grid(row=6, column=6, rowspan=1, columnspan=4, sticky=N+S+E+W)

      self.__mode_dlist.grid(row=7, column=0, rowspan=1, columnspan=3, sticky=N+S+E+W)
      self.__vfo_dlist.grid(row=7, column=3, rowspan=1, columnspan=3, sticky=N+S+E+W)
      self.__agc_mode_dlist.grid(row=7, column=6, rowspan=1, columnspan=3, sticky=N+S+E+W)

      self.__nominal_power_2_dlabel.grid(row=8, column=0, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__mic_gain_dlabel.grid(row=8, column=2, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__rit_2_dlabel.grid(row=8, column=4, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__tuning_speed_list.grid(row=8, column=8, rowspan=1, columnspan=2, sticky=N+S+E+W)

      self.__nominal_power_dial.grid(row=9, column=0, rowspan=2, columnspan=2, sticky=N+S+E+W)
      self.__mic_gain_dial.grid(row=9, column=2, rowspan=2, columnspan=2, sticky=N+S+W+E)
      self.__rit_dial.grid(row=9, column=4, rowspan=2, columnspan=2, sticky=N+S+E+W)
      self.__freq_dial.grid(row=9, column=6, rowspan=4, columnspan=4, sticky=N+S+E+W)

      self.__vox_gain_dlabel.grid(row=11, column=0, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__vox_delay_dlabel.grid(row=11, column=2, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__cw_delay_dlabel.grid(row=11, column=4, rowspan=1, columnspan=2, sticky=N+S+E+W)

      self.__vox_gain_dial.grid(row=12, column=0, rowspan=2, columnspan=2, sticky=N+S+E+W)
      self.__vox_delay_dial.grid(row=12, column=2, rowspan=2, columnspan=2, sticky=N+S+E+W)
      self.__cw_delay_dial.grid(row=12, column=4, rowspan=2, columnspan=2, sticky=N+S+E+W)

      self.__ptt_mbutton.grid(row=13, column=6, rowspan=1, columnspan=4, sticky=N+S+E+W)

      self.__dbf_low_dlabel.grid(row=14, column=0, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__dbf_high_dlabel.grid(row=14, column=2, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__dbf_pbutton.grid(row=14, column=4, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__nb_pbutton.grid(row=14, column=6, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__fm_narrow_pbutton.grid(row=14, column=8, rowspan=1, columnspan=2, sticky=N+S+E+W)

      self.__dbf_low_listdial.grid(row=15, column=0, rowspan=2, columnspan=2, sticky=N+S+E+W)
      self.__dbf_high_listdial.grid(row=15, column=2, rowspan=2, columnspan=2, sticky=N+S+E+W)
      self.__dnf_pbutton.grid(row=15, column=4, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__atten_pbutton.grid(row=15, column=6, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__cw_dig_narrow_pbutton.grid(row=15, column=8, rowspan=1, columnspan=2, sticky=N+S+E+W)

      self.__dnr_pbutton.grid(row=16, column=4, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__preamp_pbutton.grid(row=16, column=6, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__split_pbutton.grid(row=16, column=8, rowspan=1, columnspan=2, sticky=N+S+E+W)

      self.__sp_proc_pbutton.grid(row=17, column=4, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__vox_pbutton.grid(row=17, column=6, rowspan=1, columnspan=2, sticky=N+S+E+W)
      self.__bk_pbutton.grid(row=17, column=8, rowspan=1, columnspan=2, sticky=N+S+E+W)

      self.grid(sticky=Tkinter.N + Tkinter.S + Tkinter.E + Tkinter.W)

      self.__tick = -1

      self.__root.after(1, self.__main_loop)


   def add_feature_widget_to_list(self, widget):
      self.__feature_widgets.append(widget)

   def self_notify_all_widgets(self, feature, value):
      for w in self.__feature_widgets:
         w.self_notified(feature, value)

   def notify_all_widgets(self, feature, value):
      for w in self.__feature_widgets:
         w.notified(feature, value)

   def send_to_radio(self, feature, value):
      my_str = feature + ": " + value + "\n"
      self.__tcp.sendall(my_str)

   def set_tuning_speed(self, value):
      tuning_speed = process_freq(value)
      try:
         tuning_speed = math.trunc(float(tuning_speed))
      except:
         tuning_speed = 20
      self.__tuning_speed = tuning_speed

   def block_feature(self, feature):
      self.blocked_features[feature] = datetime.datetime.now()

   def is_blocked(self, feature):
      if not feature in self.blocked_features:
         return False
      return self.blocked_features[feature] + datetime.timedelta(seconds=5) > datetime.datetime.now()

   def __main_loop(self):
      is_done = False
      recv = ""
      while not is_done:
         r, w, e = select.select([self.__udp], [ ], [ ], 0)
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
            values_dict = { }
            for cnt in range(start, end):
               line = spl[cnt]
               line_spl = line.split(": ", 1)
               if len(line_spl) != 2:
                  continue
               values_dict[line_spl[0]] = line_spl[1]

            try:
               current_tick = int(values_dict["tick"])
            except:
               current_tick = -1

            if current_tick > self.__tick:
               self.__tick = current_tick
               for cnt in range(start + 1, end):
                  line = spl[cnt]
                  line_spl = line.split(": ", 1)
                  if len(line_spl) != 2:
                     continue
                  feature = line_spl[0]
                  value = line_spl[1]
                  self.notify_all_widgets(feature, value)

        
      self.__root.after(1, self.__main_loop)
