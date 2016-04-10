#!/usr/bin/env python
#
# File: dial.py
# Version: 1.0
#
# mrig: dial widget
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


import math
import Tkinter

class Dial(Tkinter.Canvas):
   def __init__(self, parent, **options):
      Tkinter.Canvas.__init__(self, parent, **options)

      self._centre_x = 0
      self._centre_y = 0
      self._radius = 0
      self._dnd_ext_radius = 0
      self._dnd_int_radius = 0
      self._dragging = False
      self._turns = 0.0
      self._angle = None
      self._turn_change_callback = None

      self._mark = None

      self.bind("<Configure>", self.__configure)
      self.bind("<Button-1>", self._start_dragging)
      self.bind("<ButtonRelease-1>", self._stop_dragging)
      self.bind("<B1-Motion>", self._drag)

   def register_change_callback(self, callback):
      self._turn_change_callback = callback

   def __configure(self, event):
      widget = event.widget
      self.__w = event.width - 2
      self.__h = event.height - 2
      widget.config(width=self.__w)
      widget.config(height=self.__h)

      self._centre_x = self.__w / 2
      self._centre_y = self.__h / 2

      if self.__w < self.__h:
         self._radius = self.__w / 2
      else:
         self._radius = self.__h / 2

      width = int(self._radius * 0.08)
      self._radius = int(self._radius * 0.90)
      self._sqr_dnd_ext_radius = int(math.pow(self._radius * 2.5, 2))
      self._sqr_dnd_int_radius = int(math.pow(self._radius * 0.5, 2))

      widget.delete(Tkinter.ALL)

      widget.create_oval(self._centre_x - self._radius, self._centre_y - self._radius, self._centre_x + self._radius, self._centre_y + self._radius, width=width)
      widget._draw_mark()

   def _draw_mark(self):
      p1_distance = int(self._radius * 0.9)
      p2_distance = int(self._radius * 0.2)
      p3_distance = p2_distance
      p1_angle = self._turns * 2 * 3.1416
      delta_angle = 0.2 * 2 * 3.1416
      p2_angle = p1_angle + delta_angle
      p3_angle = p1_angle - delta_angle

      centered_p1_x = int(math.cos(p1_angle) * p1_distance)
      centered_p1_y = int(-math.sin(p1_angle) * p1_distance)
      centered_p2_x = int(math.cos(p2_angle) * p2_distance)
      centered_p2_y = int(-math.sin(p2_angle) * p2_distance)
      centered_p3_x = int(math.cos(p3_angle) * p3_distance)
      centered_p3_y = int(-math.sin(p3_angle) * p3_distance)

      p1_x = centered_p1_x + self._centre_x
      p1_y = centered_p1_y + self._centre_y
      p2_x = centered_p2_x + self._centre_x
      p2_y = centered_p2_y + self._centre_y
      p3_x = centered_p3_x + self._centre_x
      p3_y = centered_p3_y + self._centre_y

      if self._mark:
         self.delete(self._mark)
      self._mark = self.create_polygon(p1_x, p1_y, p2_x, p2_y, p3_x, p3_y, fill="black")


   def _to_angle(self, x, y):
      # (x, y) is referred to the centre of the circle
      try:
         angle = math.atan(float(y) / float(x))
      except ZeroDivisionError:
         angle = 3.1416 / 2.0
      if x < 0 and y >= 0:
         angle = 3.1416 + angle
      elif x <= 0 and y < 0:
         angle = 3.1416 + angle
      elif x > 0 and y < 0:
         angle = 2 * 3.1416 + angle
      angle = angle * 180.0 / 3.1416

      return angle

   def _start_dragging(self, event):
      x = event.x
      y = event.y

      centered_x = x - self._centre_x
      centered_y = y - self._centre_y
      centered_y = -centered_y

      sqr_dist = centered_x * centered_x + centered_y * centered_y

      if sqr_dist >= self._sqr_dnd_int_radius and sqr_dist <= self._sqr_dnd_ext_radius:
         self._angle = self._to_angle(centered_x, centered_y)
         self._dragging = True

   def _stop_dragging(self, event):
      if self._dragging:
         self._dragging = False

   def _drag(self, event):
      if self._dragging:
         x = event.x
         y = event.y

         centered_x = x - self._centre_x
         centered_y = y - self._centre_y
         centered_y = -centered_y

         sqr_dist = centered_x * centered_x + centered_y * centered_y

         if sqr_dist > self._sqr_dnd_ext_radius or sqr_dist < self._sqr_dnd_int_radius:
            self.dragging = False
         else:
            last_angle = self._angle
            self._angle = self._to_angle(centered_x, centered_y)

            delta_angle = self._angle - last_angle
            if delta_angle > 180:
               delta_angle = -360 - last_angle + self._angle
            elif delta_angle < -180:
               delta_angle = 360 + self._angle - last_angle
            self._turns = self._turns + delta_angle / 360.0
            self._draw_mark()
            if self._turn_change_callback:
               self._turn_change_callback(self._turns)
