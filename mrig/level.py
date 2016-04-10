#!/usr/bin/env python
#
# File: level.py
# Version: 1.0
#
# mrig: level widget
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


import Tkinter

class Level(Tkinter.Canvas):
   def __init__(self, parent, **options):
      self.__color = "blue"
      if "color" in options:
         self.__color = options["color"]
         del options["color"]

      Tkinter.Canvas.__init__(self, parent, options)
      self.bind("<Configure>", self.__configure)

      self.__percent = 0

   def __configure(self, event):
      widget = event.widget
      self.__w = event.width - 2
      self.__h = event.height - 2
      widget.config(width=self.__w)
      widget.config(height=self.__h)
      self._draw_rectangle()


   def _draw_rectangle(self):
      w = int(self.cget("width"))
      h = int(self.cget("height"))
      self.delete(Tkinter.ALL)
      self.create_rectangle(0, 0, int((w - 1) * self.__percent / 100.0), (h - 1), fill=self.__color)

   def set_percent(self, percent):
      int_percent = int(percent)
      if int_percent >= 0 and int_percent <= 100:
         self.__percent = int_percent
      self._draw_rectangle()

   def get_percent(self):
      return self.__percent
