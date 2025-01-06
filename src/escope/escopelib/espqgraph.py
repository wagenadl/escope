# espqgraph.py - This file is part of EScope/ESpark
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
import pyqtgraph as pg
from PyQt5.QtGui import QPen, QColor, QPalette
from PyQt5.QtCore import Qt


pg.setConfigOption('background', '#f8f8f8')
pg.setConfigOption('foreground', 'k')
pg.setConfigOptions(antialias=True)

class ESPGraph(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMaximumSize(3000, 250)
        self.setMinimumSize(100, 100)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def setXLabel(self, s):
        self.plotItem.setLabel("bottom", s)

    def setYLabel(self, s):
        self.plotItem.setLabel("left", s)
        
    def cla(self):
        self.plotItem.clear()

    def plot(self, x, y, col=[0.,0.,1.]):
        pen = pg.mkPen(color=[int(255*c) for c in col], width=3)
        h = self.plotItem.plot(x, y, pen=pen)
        return h

    def autolim(self):
        pass

    def noticks(self):
        pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = QWidget()
    lay = QHBoxLayout(win)
    fig = ESPGraph(win)
    lay.addWidget(fig)
    win.show()
    app.exec_()
