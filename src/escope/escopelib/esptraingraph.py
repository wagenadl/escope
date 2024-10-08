# esptraingraph.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from .espgraph import ESPGraph
from . import espconfig
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
                rng = 1.
            while rng>1000:
                rng /= 1000.
                mul *= 1000.
                scl /= 1000.
            while rng<1:
                rng *= 1000.
                mul /= 1000.
                scl *= 1000.
            t1p1color = [0, 0, 1]
            if espconfig.haspulsechange(self.cfg, self.k):
                t1pxcolor = [.4, .6, 1]
            else:
                t1pxcolor = t1p1color
                
            if espconfig.hastrainchange(self.cfg, self.k):
                txp1color = [.4, .4, .4]
                if espconfig.haspulsechange(self.cfg, self.k):
                    txpxcolor = [.7, .7, .7]
                else:
                    txpxcolor = txp1color
            else:
                txp1color = t1p1color
                txpxcolor = t1pxcolor
            self.plot(xx, yy*scl, txpxcolor)
            timing = espconfig.mktiming(self.cfg, self.k)
            for itr in range(1,int(self.cfg.train[self.k].ntrains.base)):
                (xx, yy) = espconfig.mkpulse(self.cfg, self.k, itr, 0)
                self.plot(xx+timing[1][itr,0]/fs_hz, yy*scl, txp1color)
            for ipu in range(1,int(self.cfg.train[self.k].npulses.base)):
                (xx, yy) = espconfig.mkpulse(self.cfg, self.k, 0, ipu)
                self.plot(xx+timing[1][0,ipu]/fs_hz, yy*scl, t1pxcolor)
            (xx, yy) = espconfig.mkpulse(self.cfg, self.k, 0, 0)
            self.plot(xx+timing[1][0,0]/fs_hz, yy*scl, t1p1color)
                
        self.setXLabel('(s)')
        scl = espconfig.scaleunit(self.cfg.conn.units[self.k], mul)
        self.setYLabel(f'({scl})')
        self.autolim()
            
