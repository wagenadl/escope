# esppulsegraph.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .espgraph import ESPGraph
from .import espconfig
import numpy as np

class ESPPulseGraph(ESPGraph):
    def __init__(self, cfg, k, parent=None):
        ESPGraph.__init__(self, parent)
        self.cfg = cfg
        self.k = k
        
    def rebuild(self):
        self.cla()
        mul=1.
        scl = self.cfg.conn.scale[self.k]
        (xx, yy) = espconfig.mktrain(self.cfg, self.k)
        rng = np.max(np.abs(yy))*scl
        if rng==0:
            rng = 1.
        while rng>1000:
            rng /= 1000.
            mul *= 1000.
            scl /= 1000.
        while rng<1:
            rng *= 1000.
            mul /= 1000.
            scl *= 1000.
        
        if self.cfg.pulse[self.k].type.value:
            for itr in range(1,int(self.cfg.train[self.k].ntrains.base)):
                for ipu in range(1,int(self.cfg.train[self.k].npulses.base +
                                       itr*
                                       self.cfg.train[self.k].npulses.delta)):
                    (xx, yy) = espconfig.mkpulse(self.cfg, self.k, itr, ipu)
                    self.plot(xx*1e3, yy*scl, [.7, .7, .7])
            for itr in range(1,int(self.cfg.train[self.k].ntrains.base)):
                (xx, yy) = espconfig.mkpulse(self.cfg, self.k, itr, 0)
                self.plot(xx*1e3, yy*scl, [.4, .4, .4])
            for ipu in range(1,int(self.cfg.train[self.k].npulses.base)):
                (xx, yy) = espconfig.mkpulse(self.cfg, self.k, 0, ipu)
                self.plot(xx*1e3, yy*scl, [.3, .5, 1])
            
            (xx, yy) = espconfig.mkpulse(self.cfg, self.k, 0, 0)
            self.plot(xx*1e3, yy*scl)
        else:
            self.plot([-.3, 10.3], [0, 0])
        self.setXLabel('(ms)')
        scl = espconfig.scaleunit(self.cfg.conn.units[self.k], mul)
        self.setYLabel(f'({scl})')
        self.autolim()
