# ledlabel.py
# inspired by https://forum.qt.io/topic/101648/how-to-create-simply-virtual-led-indicator/2

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class LEDLabel(QLabel):
    SIZE = 24
    def __init__(self, color=[.2,1,.3], lit=False):
        super().__init__()
        self.color = color
        self.lit = lit
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMinimumSize(self.SIZE, self.SIZE)
        self.setMaximumSize(self.SIZE, self.SIZE)
        self.rebuild()

    def setColor(self, color):
        self.color = color
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
            clr = [x/3.0 for x in self.color]
        rgba = f"rgba({int(255*clr[0])}, {int(255*clr[1])}, {int(255*clr[2])}, 255)"
        clrb = [x/2 for x in clr]
        rgbb = f"rgba({int(255*clrb[0])}, {int(255*clrb[1])}, {int(255*clrb[2])}, 255)"
        ss = f"color: white;border-radius: {self.SIZE/2};background-color: qlineargradient(spread:pad, x1:0.145, y1:0.16, x2:0.92, y2:0.988636, stop:0 {rgba}, stop:0.869347 {rgbb});"
        self.setStyleSheet(ss)
        
