# espchannels.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import numpy as np
from . import espconfig


class ESPChannels(QWidget):
    cfgChanged = pyqtSignal(int)
    
    def __init__(self, cfg):
        QWidget.__init__(self, None)
        self.setWindowTitle("ESpark: Channels")
        self.cfg = cfg
        lay = QGridLayout(self)
        #lbl = QLabel("Stim", self)
        #lbl.setAlignment(Qt.AlignCenter)
        #lay.addWidget(lbl,0,0)
        lbl = QLabel("Channel", self)
        lbl.setToolTip('''Note that some channels are analog outputs, while others are digital.
On digital channels, only TTL pulses can be generated and the scale is fixed.
On analog channels, many different waveform shapes can be generated.''')        
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl,0,1)
        lbl = QLabel("1 V makes", self)
        lbl.setToolTip('''Here you explain to ESpark what happens in the real world when
it instructs the DAC to output 1 V.
This enables the use of correct units in the “Amplitude” boxes
and graphs.''')
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl,0,2,1,2)

        self.setFont(QFont(*self.cfg.font))

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
            lbl = QLabel(self)
            lbl.setText(chr(65+k))
            lbl.setAlignment(Qt.AlignCenter)
            f = lbl.font()
            f.setWeight(QFont.Bold)
            lbl.setFont(f)
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
            if self.cfg.conn.hw[k] is None:
                self.h_chn[k].setCurrentIndex(self.h_chn[k].count()-1)
            else:
                self.h_chn[k].setCurrentIndex(self.cfg.conn.hw[k])

    def buildScales(self):
        for k in range(self.cfg.MAXCHANNELS):
            self.h_scl[k].clear()
            items='1 2 5 10 20 50 100 200 500'.split(' ')
            for c in items:
                self.h_scl[k].addItem(c)
            scl = espconfig.niceunit(self.cfg.conn.scale[k],
                                     self.cfg.conn.units[k]).split(' ')
            if scl[0] in items:
                self.h_scl[k].setCurrentIndex(items.index(scl[0]))
            else:
                self.h_scl[k].setCurrentIndex(0)
                print('Cannot find scale item for', scl[0])
            self.h_scl[k].setEnabled(self.h_chn[k].currentText().lower().startswith("a"))

    def buildUnits(self):
        for k in range(self.cfg.MAXCHANNELS):
            self.h_uni[k].clear()
            items = 'uV mV V pA nA uA mA'.split(' ')
            for c in items:
                self.h_uni[k].addItem(c)
            scl = espconfig.niceunit(self.cfg.conn.scale[k],
                                    self.cfg.conn.units[k]).split(' ')
            if scl[1] in items:
                self.h_uni[k].setCurrentIndex(items.index(scl[1]))
            else:
                self.h_uni[k].setCurrentIndex(0)
                print('Cannot find units item for', scl[1])
            self.h_uni[k].setEnabled(self.h_chn[k].currentText().lower().startswith("a"))

    def selectChannel(self, k, idx):
        was = self.cfg.conn.hw[k]
        ena = False
        if idx==len(self.cfg.hw.channels):
            self.cfg.conn.hw[k] = None
        else:
            if idx in self.cfg.conn.hw:
                ak = self.cfg.conn.hw.index(idx)
                if ak!=k:
                    self.cfg.conn.hw[ak] = None
                    self.h_chn[ak].setCurrentIndex(len(self.cfg.hw.channels))
                    self.h_scl[ak].setEnabled(False)
                    self.h_uni[ak].setEnabled(False)
                    self.cfgChanged.emit(ak)
            self.cfg.conn.hw[k] = idx
            ena = self.h_chn[k].currentText().lower().startswith("a")
        self.h_scl[k].setEnabled(ena)
        self.h_uni[k].setEnabled(ena)
            
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
    cfg = espconfig.basicconfig()
    win = ESPChannels(cfg)
    win.show()
    app.exec_()
    
