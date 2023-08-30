# eschannels.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import numpy as np
from . import esconfig


class ESChannels(QWidget):
    cfgChanged = pyqtSignal(int)
    
    def __init__(self, cfg):
        QWidget.__init__(self, None)
        self.setWindowTitle("EScope: Channels")
        self.cfg = cfg
        lay = QGridLayout(self)
        lbl = QLabel("Trace", self)
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl,0,0)
        lbl = QLabel("Channel", self)
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl,0,1)
        lbl = QLabel("1 V means", self)
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl,0,2,1,2)

        f = self.font()
        f.setPixelSize(self.cfg.FONTSIZE)
        self.setFont(f)

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
            p.setColor(QPalette.Window, self.cfg.colors[k])
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
            items = 'uV mV V pA nA uA mA'.split(' ')
            for c in items:
                self.h_uni[k].addItem(c)
            scl = esconfig.niceunit(self.cfg.conn.scale[k],
                                    self.cfg.conn.units[k]).split(' ')
            if scl[1] in items:
                self.h_uni[k].setCurrentIndex(items.index(scl[1]))
            else:
                self.h_uni[k].setCurrentIndex(0)
                print('Cannot find units item for', scl[1])

    def selectChannel(self, k, idx):
        was = self.cfg.conn.hw[k]
        if idx==len(self.cfg.hw.channels):
            self.cfg.conn.hw[k] = np.nan
        else:
            if idx in self.cfg.conn.hw:
                ak=np.nonzero(self.cfg.conn.hw==idx)[0][0]
                if ak!=k:
                    self.cfg.conn.hw[ak] = np.nan
                    self.h_chn[ak].setCurrentIndex(len(self.cfg.hw.channels))
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
    
