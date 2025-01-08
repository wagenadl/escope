# esphardware.py - This file is part of EScope/ESpark
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


# esphardware.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
from . import espconfig
import numpy as np

class ESPHardware(QGroupBox):
    cfgChanged = pyqtSignal()
    
    def __init__(self, cfg):
        super().__init__(title="Hardware")
        self.setWindowTitle("ESpark: Hardware")
        self.cfg = cfg
        wdg = QWidget()
        wdg.setObjectName("hwdock")
        tlay = QGridLayout(self)
        tlay.setContentsMargins(0,0,0,0)
        tlay.addWidget(wdg)
        wdg.setStyleSheet("""
        QWidget#hwdock {background-color: #f8f8f8;}
        """)
        lay = QGridLayout(wdg)
        lbl = QLabel("Adapter:", self)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(lbl,0,0)

        lbl = QLabel("Gen. Rate:", self)
        lbl.setAlignment(Qt.AlignRight)
        lay.addWidget(lbl,1,0)

        self.h_ada = QComboBox(self)
        self.h_rate = QComboBox(self)
        self.h_ada.activated.connect(self.selectHardware)
        self.h_rate.activated.connect(self.selectRate)
        lay.addWidget(self.h_ada,0,1)
        lay.addWidget(self.h_rate,1,1)
        lay.setSpacing(10)

        self.reccfg = None
        self.buildAdapters()
        self.reconfig()

    def reconfig(self, reccfg=None):
        self.reccfg = reccfg
        self.findAdapter()
        self.buildRates()

    def findAdapter(self):
        k=0
        for ada in self.cfg.hw.adapters:
            if self.cfg.hw.adapter==ada:
                self.h_ada.setCurrentIndex(k)
            k=k+1

    def findRate(self):
        k = np.argmin(abs(self.cfg.hw.genrate.value -
                             self.cfg.hw.genrate.values))
        self.h_rate.setCurrentIndex(k)

    def buildAdapters(self):
        self.h_ada.clear()
        for ada in self.cfg.hw.adapters:
            name = ada[0]
            if len(ada)>1:
                name = f"{name}: {ada[1]}"
            self.h_ada.addItem(name)
        self.findAdapter()

    def buildRates(self):
        self.h_rate.clear()
        if self.reccfg and self.reccfg.hw.adapter == self.cfg.hw.adapter \
               and self.cfg.hw.adapter[0] == 'picodaq':
            self.h_rate.addItem("%g kHz" % (self.reccfg.hw.acqrate.value/1000))
            self.h_rate.setEnabled(False)
        else:
            for v in self.cfg.hw.genrate.values:
                self.h_rate.addItem("%g kHz" % (v/1000))
            self.h_rate.setEnabled(True)
        self.findRate()

    def selectHardware(self, idx):
        self.cfg.hw.adapter = self.cfg.hw.adapters[idx]
        espconfig.confighardware(self.cfg)
        self.buildRates()
        self.cfgChanged.emit()

    def selectRate(self, idx):
        self.cfg.hw.genrate.value = self.cfg.hw.genrate.values[idx]
        self.cfgChanged.emit()

    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    cfg = espconfig.basicconfig()
    win = ESPHardware(cfg)
    win.show()
    app.exec_()
    
