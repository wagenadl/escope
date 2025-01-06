# esptraingraph.py - This file is part of EScope/ESpark
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
        train = self.cfg.train[self.k]
        pulse = self.cfg.pulse[self.k]

        mul = 1.
        fs_hz = self.cfg.hw.genrate.value
        if True: #pulse.type.value and (train.ntrains.base > 1
            #                     or train.npulses.base > 1):
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
            for itr in range(1, int(train.ntrains.base)):
                (xx, yy) = espconfig.mkpulse(self.cfg, self.k, itr, 0,
                                             margin=False)
                self.plot(xx + timing[1][itr,0] / fs_hz,
                          yy * scl, txp1color)
            for ipu in range(1, int(train.npulses.base)):
                (xx, yy) = espconfig.mkpulse(self.cfg, self.k, 0, ipu,
                                             margin=False)
                self.plot(xx+timing[1][0,ipu]/fs_hz, yy*scl, t1pxcolor)
            (xx, yy) = espconfig.mkpulse(self.cfg, self.k, 0, 0,
                                         margin=False)
            self.plot(xx+timing[1][0,0]/fs_hz, yy*scl, t1p1color)
                
            self.setXLabel('(s)')
            scl = espconfig.scaleunit(self.cfg.conn.units[self.k], mul)
            self.setYLabel(f'({scl})')
            self.autolim()
        else:
            self.setXLabel('')
            self.setYLabel('')
            self.noticks()
            
