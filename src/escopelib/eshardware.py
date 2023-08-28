# eshardware.py

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
import esconfig
import numpy as np

class ESHardware(QWidget):
    cfgChanged = pyqtSignal()
    
    def __init__(self, cfg):
        QWidget.__init__(self, None)
        self.setWindowTitle("EScope: Hardware")
        self.cfg = cfg
        lay = QGridLayout(self)
        lbl = QLabel("Adapter:", self)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(lbl,0,0)

        lbl = QLabel("Acq. Rate:", self)
        lbl.setAlignment(Qt.AlignRight)
        lay.addWidget(lbl,1,0)

        self.h_ada = QComboBox(self)
        self.h_rate = QComboBox(self)
        self.h_ada.activated.connect(self.selectHardware)
        self.h_rate.activated.connect(self.selectRate)
        lay.addWidget(self.h_ada,0,1)
        lay.addWidget(self.h_rate,1,1)
        lay.setSpacing(10)
        f = self.font()
        f.setPixelSize(self.cfg.FONTSIZE)
        self.setFont(f)

        self.buildAdapters()
        self.reconfig()

    def reconfig(self):
        self.findAdapter()
        self.buildRates()

    def findAdapter(self):
        k=0
        for ada in self.cfg.hw.adapters:
            if self.cfg.hw.adapter==ada:
                self.h_ada.setCurrentIndex(k)
            k=k+1

    def findRate(self):
        k = np.argmin(abs(self.cfg.hw.acqrate.value -
                             self.cfg.hw.acqrate.values))
        self.h_rate.setCurrentIndex(k)

    def buildAdapters(self):
        self.h_ada.clear()
        for ada in self.cfg.hw.adapters:
            name = ada[0]
            if len(ada)>1:
                name = name + ": " + `ada[1]`
            self.h_ada.addItem(name)
        self.findAdapter()

    def buildRates(self):
        self.h_rate.clear()
        for v in self.cfg.hw.acqrate.values:
            self.h_rate.addItem("%g kHz" % (v/1000))
        self.findRate()

    def selectHardware(self, idx):
        self.cfg.hw.adapter = self.cfg.hw.adapters[idx]
        esconfig.confighardware(self.cfg)
        self.buildRates()
        self.cfgChanged.emit()

    def selectRate(self, idx):
        self.cfg.hw.acqrate.value = self.cfg.hw.acqrate.values[idx]
        self.cfgChanged.emit()

    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()
    win = ESHardware(cfg)
    win.show()
    app.exec_()
    
