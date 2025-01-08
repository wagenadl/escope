# eschannels.py - This file is part of EScope/ESpark
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


# eschannels.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import numpy as np
from . import esconfig


class ESChannels(QGroupBox):
    cfgChanged = pyqtSignal(int)
    
    def __init__(self, cfg):
        super().__init__(title="Channels")
        self.setWindowTitle("EScope: Channels")
        self.cfg = cfg
        lay = QGridLayout(self)
        lbl = QLabel("     ", self)
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl,0,0)
        lbl = QLabel("Channel", self)
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl,0,1)
        lbl = QLabel("1 V means", self)
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl,0,2,1,2)

        self.h_chn = [None] * self.cfg.MAXCHANNELS
        self.h_scl = [None] * self.cfg.MAXCHANNELS
        self.h_uni = [None] * self.cfg.MAXCHANNELS

        def mkSelChn(k):
            def selChn(idx):
                self.selectChannel(k,idx)
            return selChn
        def mkSelScl(k):
            def selScl(idx):
                self.selectScale(k,idx)
            return selScl
        def mkSelUni(k):
            def selUni(idx):
                self.selectUnits(k,idx)
            return selUni
        
        for k in range(self.cfg.MAXCHANNELS):
            lbl = QFrame(self)
            lbl.setAutoFillBackground(True)
            p = lbl.palette()
            p.setColor(QPalette.Window, esconfig.color(self.cfg, k))
            lbl.setPalette(p)
            lay.addWidget(lbl,1+k,0)

            cb = QComboBox(self)
            self.h_chn[k] = cb
            lay.addWidget(cb,1+k,1)
            cb.activated.connect(mkSelChn(k))

            cb = QComboBox(self)
            self.h_scl[k] = cb
            lay.addWidget(cb,1+k,2)
            cb.activated.connect(mkSelScl(k))

            cb = QComboBox(self)
            self.h_uni[k] = cb
            lay.addWidget(cb,1+k,3)
            cb.activated.connect(mkSelUni(k))

        lay.setSpacing(10)
        self.reconfig()

    def reconfig(self):
        self.buildChannels()
        self.buildScales()
        self.buildUnits()

    def buildChannels(self):
        for k in range(self.cfg.MAXCHANNELS):
            self.h_chn[k].clear()
            for c in self.cfg.hw.channels:
                self.h_chn[k].addItem(c)
            self.h_chn[k].addItem('--')
            if np.isnan(self.cfg.conn.hw[k]):
                self.h_chn[k].setCurrentIndex(self.h_chn[k].count()-1)
            else:
                self.h_chn[k].setCurrentIndex(int(self.cfg.conn.hw[k]))

    def buildScales(self):
        for k in range(self.cfg.MAXCHANNELS):
            self.h_scl[k].clear()
            items='1 2 5 10 20 50 100 200 500'.split(' ')
            for c in items:
                self.h_scl[k].addItem(c)
            scl = esconfig.niceunit(self.cfg.conn.scale[k],
                                    self.cfg.conn.units[k]).split(' ')
            if scl[0] in items:
                self.h_scl[k].setCurrentIndex(items.index(scl[0]))
            else:
                self.h_scl[k].setCurrentIndex(0)
                print('Cannot find scale item for', scl[0])

    def buildUnits(self):
        for k in range(self.cfg.MAXCHANNELS):
            self.h_uni[k].clear()
            items = 'µV mV V pA nA µA mA'.split(' ')
            for c in items:
                self.h_uni[k].addItem(c)
            scl = esconfig.niceunit(self.cfg.conn.scale[k],
                                    self.cfg.conn.units[k]).split(' ')
            if scl[1] in items:
                self.h_uni[k].setCurrentIndex(items.index(scl[1]))
            else:
                self.h_uni[k].setCurrentIndex(0)
                print('Cannot find units item for', scl[1], len(scl[1]),
                      self.cfg.conn.scale[k],
                      self.cfg.conn.units[k])

    def selectChannel(self, k, idx):
        was = self.cfg.conn.hw[k]
        if idx == len(self.cfg.hw.channels):
            self.cfg.conn.hw[k] = np.nan
        else:
            if idx in self.cfg.conn.hw:
                ak = np.nonzero(self.cfg.conn.hw==idx)[0][0]
                if ak != k:
                    self.cfg.conn.hw[ak] = np.nan
                    N = len(self.cfg.hw.channels)
                    self.h_chn[ak].setCurrentIndex(N)
                    self.cfgChanged.emit(ak)
            self.cfg.conn.hw[k] = idx
        if self.cfg.conn.hw[k]!=was:
            self.cfgChanged.emit(k)

    def selectScale(self, k, idx):
        txt = self.h_scl[k].itemText(idx)
        self.cfg.conn.scale[k] = int(txt)
        self.cfgChanged.emit(k)
        
    def selectUnits(self, k, idx):
        txt = self.h_uni[k].itemText(idx)
        self.cfg.conn.units[k] = str(txt)
        self.cfgChanged.emit(k)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()
    win = ESChannels(cfg)
    win.show()
    app.exec_()
    
