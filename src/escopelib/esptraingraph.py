# esptraingraph.py

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from espgraph import ESPGraph, ESPQ
import espconfig
import numpy as np

class ESPTrainGraph(ESPGraph):
    def __init__(self, cfg, k, parent=None):
        ESPGraph.__init__(self, parent)
        self.cfg = cfg
        self.k = k
        
    def rebuild(self):
        self.cla()
        mul=1.
        fs_hz = self.cfg.hw.genrate.value
        if self.cfg.pulse[self.k].type.value:
            scl = self.cfg.conn.scale[self.k]
            (xx, yy) = espconfig.mktrain(self.cfg, self.k)
            rng = np.max(np.abs(yy))*scl
            if rng==0:
                rng=1.
            while rng>1000:
                rng/=1000.
                mul*=1000.
                scl/=1000.
            while rng<1:
                rng*=1000.
                mul/=1000.
                scl*=1000.
            self.plot(xx, yy*scl,[.7,.7,.7])
            timing = espconfig.mktiming(self.cfg, self.k)
            for itr in range(1,int(self.cfg.train[self.k].ntrains.base)):
                if ESPQ:
                    self.colorify(timing[1][itr,0]/fs_hz,
                                  (timing[2][itr,0]+4)/fs_hz, [.4,.4,.4])
                else:
                    (xx, yy) = espconfig.mkpulse(self.cfg, self.k, itr, 0)
                    self.plot(xx+timing[1][itr,0]/fs_hz, yy*scl, [.4,.4,.4])
            for ipu in range(1,int(self.cfg.train[self.k].npulses.base)):
                if ESPQ:
                    self.colorify(timing[1][0,ipu]/fs_hz,
                                  (timing[2][0,ipu]+4)/fs_hz, [0,1,1])
                else:
                    (xx, yy) = espconfig.mkpulse(self.cfg, self.k, 0, ipu)
                    self.plot(xx+timing[1][0,ipu]/fs_hz, yy*scl, [0,1,1])
            if ESPQ:
                self.colorify(timing[1][0,0]/fs_hz,
                              (timing[2][0,0]+4)/fs_hz, [0,0,1])
            else:
                (xx, yy) = espconfig.mkpulse(self.cfg, self.k, 0, 0)
                self.plot(xx+timing[1][0,0]/fs_hz, yy*scl, [0,0,1])
                
        self.setXLabel('(s)')
        self.setYLabel('(%s)' %
                       espconfig.scaleunit(self.cfg.conn.units[self.k],
                                           mul))
                       
        self.autolim()
            
