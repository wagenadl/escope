# espmgraph.py - This file is part of EScope/ESpark
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


import numpy as np
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class ESPGraph(FigureCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        fig = Figure()
        self.axes = fig.add_axes([0.20, 0.20, 0.75, 0.78])
        # self.axes = fig.add_subplot(111)
        # self.axes.hold(True)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        self.setMaximumSize(2000, 250)
        self.setSizePolicy(QSizePolicy.Expanding,
                           QSizePolicy.Fixed)
        self.setMinimumSize(100, 100)
        fig.set_facecolor('#f8f8f8') # The Qt palette doesn't affect the fig.

    def setXLabel(self, s):
        self.axes.set_xlabel(s)

    def setYLabel(self, s):
        self.axes.set_ylabel(s)
        
    def cla(self):
        self.axes.cla()
        self.axes.set_facecolor('#ffffff')
        for s in self.axes.spines.values():
            s.set_color('#000000')

    def plot(self,x,y, col=[0.,0.,1.]):
        return self.axes.plot(x,y, color=col)

    def autolim(self):
        self.axes.axis('tight')
        xx = self.axes.get_xlim()
        yy = self.axes.get_ylim()
        dx = (xx[1]-xx[0])/20
        dy = (yy[1]-yy[0])/20
        self.axes.set_xlim((xx[0]-dx,xx[1]+dx))
        self.axes.set_ylim((yy[0]-dy,yy[1]+dy))
        self.draw()

    def noticks(self):
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        self.axes.set_facecolor('#f8f8f8')
        for s in self.axes.spines.values():
            s.set_color('#aaaaaa')
        self.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = QWidget()
    lay = QHBoxLayout(win)
    fig = ESPGraph(win)
    lay.addWidget(fig)
    win.show()
    app.exec_()
