# espdatasink.py - abstract data sink

from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
from . import espconfig
import numpy as np
import ctypes

class ESPDataSink(QObject):
    runComplete = pyqtSignal()

    def __init__(self, cfg):
        QObject.__init__(self)
        self.cfg = cfg
        self.running = False
        self.dat = None
        self.t_end_s = None

    def reconfig(self):
        self.idx = [k for k, x in enumerate(self.cfg.conn.hw) if x is not None]
        self.nchans = len(self.idx)
        self.chans = [self.cfg.conn.hw[k] for k in self.idx]
        self.nscans = 0
        for k in range(self.nchans):
            timing = espconfig.mktiming(self.cfg,self.idx[k])
            if timing[0]>self.nscans:
                self.nscans = timing[0]
        self.dat = np.zeros((self.nscans+4, self.nchans))
        for k in range(self.nchans):
            timing = espconfig.mktiming(self.cfg,self.idx[k])
            espconfig.filltrain(self.cfg, self.idx[k], timing, self.dat[:,k])
        self.t_end_s = self.nscans/self.cfg.hw.genrate.value

    def run(self):
        self.running = True

    def stop(self):
        self.markEnded()

    def markEnded(self):
        self.running = False        

class ESPDS_Dummy(ESPDataSink):
    def __init__(self, cfg):
        ESPDataSink.__init__(self, cfg)
        self.timerid = None

    def reconfig(self):
        ESPDataSink.reconfig(self)

    def run(self):
        ESPDataSink.run(self)
        if self.timerid is not None:
            self.killTimer(self.timerid)
        self.timerid = self.startTimer(int(self.t_end_s*1000))
        
    def stop(self):
        if self.timerid is not None:
            self.killTimer(self.timerid)
        ESPDataSink.stop(self)

    def timerEvent(self, evt):
        self.killTimer(self.timerid)
        self.timerid=None
        self.markEnded()
        print('espdatasink: timerevent: emitting runcomplete')
        self.runComplete.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    cfg = espconfig.basicconfig()
    ds = ESPDS_Dummy(cfg)
    ds.reconfig()

    def rcv():
        print("Recv!")
        
    ds.runComplete.connect(rcv)

    win = QWidget()
    win.show()

    print('window open')
    ds.reconfig()
    print('configured')
    ds.run()
    print('running')
    
    app.exec_()
