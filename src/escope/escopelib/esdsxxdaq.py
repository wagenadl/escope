# esdsxxdaq.py - This file is part of EScope/ESpark
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


# esdsxxdaq.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import sys
from . import esconfig
import numpy as np
import ctypes
from .esdatasource import ESDataSource


class ESDS_xxdaq(ESDataSource):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.AcqTask = None
        self.acqtask = None
        
    def reconfig(self):
        super().reconfig()
        dev = self.cfg.hw.adapter[1]
        chs = []
        for hw in self.cfg.conn.hw:
            if not np.isnan(hw):
                ch = self.cfg.hw.channels[int(hw)]
                chs.append(ch)
        self.acqtask = self.AcqTask(dev, chs,
                                    self.cfg.hw.acqrate.value, 
                                    self.range)

    def run(self):
        if self.acqtask is None:
            raise RuntimeError('Cannot run w/o prior configuration')
        self.acqtask.setCallback(self.feedData,
                                 self.period_scans)
        self.acqtask.prep() 
        self.acqtask.run() 
        if not self.acqtask.running:
            return False
        return super().run()
            
       
    def stop(self):
        super().stop()
        self.acqtask.stop()
        self.acqtask.unprep()

    def feedData(self, *args):
        self.dataAvailable.emit()
        return 0

    def getData(self, dst):
        nsc = self.acqtask.getData(dst)
        return nsc
