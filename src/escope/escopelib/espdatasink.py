# espdatasink.py - This file is part of EScope/ESpark
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
        self.idx = [k for k, x in enumerate(self.cfg.conn.hw)
                    if x is not None]
        self.nchans = len(self.idx)
        self.chans = [self.cfg.conn.hw[k] for k in self.idx]
        self.nscans = 0
        for k in range(self.nchans):
            timing = espconfig.mktiming(self.cfg, self.idx[k])
            if timing[0]>self.nscans:
                self.nscans = timing[0]
        self.dat = np.zeros((self.nscans+4, self.nchans))
        for k in range(self.nchans):
            timing = espconfig.mktiming(self.cfg, self.idx[k])
            espconfig.filltrain(self.cfg, self.idx[k], timing,
                                self.dat[:,k])
        self.t_end_s = self.nscans/self.cfg.hw.genrate.value

    def join(self, acqtask):
        pass

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
        super().reconfig()

    def run(self):
        super().run()
        if self.timerid is not None:
            self.killTimer(self.timerid)
        self.timerid = self.startTimer(int(self.t_end_s*1000))
        
    def stop(self):
        if self.timerid is not None:
            self.killTimer(self.timerid)
        super().stop()

    def timerEvent(self, evt):
        self.killTimer(self.timerid)
        self.timerid=None
        self.markEnded()
        self.runComplete.emit()
