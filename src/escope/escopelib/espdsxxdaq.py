# espdsnidaq.py - This file is part of EScope/ESpark
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


# espdsnidaq - data sink for nidaq

from .espdatasink import ESPDataSink
import sys
from . import espconfig
import numpy as np
import ctypes
from . import esnidaq

class ESPDS_Nidaq(ESPDataSink):
    def __init__(self, cfg):
        ESPDataSink.__init__(self, cfg)
        self.gentask = None

    def reconfig(self):
        ESPDataSink.reconfig(self)
        dev = self.cfg.hw.adapter[1]
        chs = []
        for hw in self.chans:
            chs.append(self.cfg.hw.channels[int(hw)])
        self.gentask = esnidaq.FiniteProdTask(dev, chs,
                                              self.cfg.hw.genrate.value,
                                              self.dat)

    def run(self):
        #print 'espds: run'
        if self.gentask is None:
            raise RuntimeError('ESPDS_Nidaq: Cannot run w/o prior configuration')
        self.gentask.setCallback(self.genDone)
        self.gentask.prep()
        self.gentask.run()
        ESPDataSink.run(self)

    def stop(self):
        #print 'espds: stop'
        ESPDataSink.stop(self)
        self.gentask.stop()
        self.gentask.unprep()

    def genDone(self, *args):
        #print 'espds: genDone'
        self.markEnded()
        self.gentask.unprep()
        self.runComplete.emit()
        return 0
