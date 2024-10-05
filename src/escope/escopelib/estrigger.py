# estrigger.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
from . import esconfig
import numpy as np

class MyRadio(QRadioButton):
    def hitButton(self, pos):
        return True

class ESTrigger(QWidget):
    cfgChanged = pyqtSignal()
    
    def __init__(self, cfg):
        QWidget.__init__(self, None)
        self.setWindowTitle("EScope: Trigger")
        self.cfg = cfg
        lay = QVBoxLayout(self)
        self.h_enable = QCheckBox(self)
        self.h_enable.setText("Trigger")
        lay.addWidget(self.h_enable)
        self.h_auto = QCheckBox(self)
        self.h_auto.setText("Auto")
        lay.addWidget(self.h_auto)
        def eslot():
            self.cfg.trig.enable = self.h_enable.isChecked()
            #print 'Enabled: ', self.cfg.trig.enable
            self.cfgChanged.emit()
        self.h_enable.toggled.connect(eslot)
        def aslot():
            self.cfg.trig.auto = self.h_auto.isChecked()
            #print 'Auto: ', self.cfg.trig.auto
            self.cfgChanged.emit()
        self.h_auto.toggled.connect(aslot)
        self.hh=[]
        for ch in range(self.cfg.MAXCHANNELS):
            h = MyRadio(self)
            h.setText('')
            #h.setFixedHeight(20)
            h.setAutoFillBackground(True)
            p = h.palette()
            p.setColor(QPalette.Button, esconfig.color(self.cfg, ch))
            h.setPalette(p)
            self.hh.append(h)
            lay.addWidget(h)
            def mkSlot(ch):
                def rslot():
                    self.cfg.trig.source=ch
                    #print 'Selected: ', ch
                    self.cfgChanged.emit()
                return rslot
            h.clicked.connect(mkSlot(ch))
        self.setFont(QFont(*self.cfg.font))
        lay.setSpacing(5)
        self.reconfig()

    def reconfig(self):
        self.h_enable.setChecked(self.cfg.trig.enable)
        self.h_auto.setChecked(self.cfg.trig.auto)
        for ch in range(self.cfg.MAXCHANNELS):
            self.hh[ch].setChecked(self.cfg.trig.source==ch)
        
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
                name = f"{name}: {ada[1]}"
            self.h_ada.addItem(name)
        self.findAdapter()

    def buildRates(self):
        self.h_rate.clear()
        for v in self.cfg.hw.acqrate.values:
            self.h_rate.addItem("%g kHz" % (v/1000))
        self.findRate()

    def selectTrigger(self, idx):
        self.cfg.hw.adapter = self.cfg.hw.adapters[idx]
        esconfig.es_configtrigger(self.cfg)
        self.buildRates()
        self.cfgChanged.emit()

    def selectRate(self, idx):
        self.cfg.hw.acqrate.value = self.cfg.hw.acqrate.values[idx]
        self.cfgChanged.emit()

    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()
    win = ESTrigger(cfg)
    win.show()
    app.exec_()
    
