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
        
