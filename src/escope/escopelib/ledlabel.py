# ledlabel.py - This file is part of EScope/ESpark
# (C) 2024  Daniel A. Wagenaar
#
# EScope and ESpark are free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# EScope and ESpark are distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software. If not, see <http://www.gnu.org/licenses/>.


# ledlabel.py
# inspired by https://forum.qt.io/topic/101648/how-to-create-simply-virtual-led-indicator/2

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class LEDLabel(QLabel):
    def __init__(self, color=[.2, 1, .3], lit=False):
        super().__init__()
        self.color = color
        self.colorb = color
        self.lit = lit
        unit = QFontMetrics(self.font()).boundingRect("X").height()
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.siz = int(unit * 0.9)
        self.setFixedSize(self.siz, self.siz)
        self.rebuild()

    def setColor(self, color, colorb=None):
        self.color = color
        if colorb is None:
            self.colorb = self.color
        else:
            self.colorb = colorb
        self.rebuild()

    def turnOn(self, on=True):
        self.lit = on
        self.rebuild()

    def turnOff(self):
        self.lit = False
        self.rebuild()

    def rebuild(self):
        if self.lit:
            clr = self.color
        else:
            clr = [x/3.0 for x in self.colorb]
        rgba = f"rgba({int(255*clr[0])}, {int(255*clr[1])}, {int(255*clr[2])}, 255)"
        clrb = [x/2 for x in clr]
        rgbb = f"rgba({int(255*clrb[0])}, {int(255*clrb[1])}, {int(255*clrb[2])}, 255)"
        ss = f"color: white;border-radius: {self.siz/2};background-color: qlineargradient(spread:pad, x1:0.145, y1:0.16, x2:0.92, y2:0.988636, stop:0 {rgba}, stop:0.869347 {rgbb});"
        self.setStyleSheet(ss)
        
