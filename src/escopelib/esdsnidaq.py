# esdsnidaq.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import sys
from . import esconfig
import numpy as np
import ctypes
from .esdatasource import ESDataSource
from . import esnidaq

class ESDS_Nidaq(ESDataSource):
    def __init__(self, cfg):
        ESDataSource.__init__(self, cfg)
        self.acqtask = None
        
    def reconfig(self):
        ESDataSource.reconfig(self)
        dev = self.cfg.hw.adapter[1]
        chs = []
        for hw in self.cfg.conn.hw:
            if not np.isnan(hw):
                ch = self.cfg.hw.channels[int(hw)]
                chs.append(ch)
                self.acqtask = esnidaq.ContAcqTask(dev, chs,
                                                   self.cfg.hw.acqrate.value, 
                                                   self.range)

    def run(self):
        if self.acqtask is None:
            raise RuntimeError('ESDSNidaq: Cannot run w/o prior configuration')
        self.acqtask.setCallback(self.feedData,
                                 self.period_scans)
        self.acqtask.prep() 
        self.acqtask.run() 
        if not self.acqtask.running:
            return False
        return ESDataSource.run(self)
            
       
    def stop(self):
        ESDataSource.stop(self)
        self.acqtask.stop()
        self.acqtask.unprep()

    def feedData(self, *args):
        self.dataAvailable.emit()
        return 0

    def getData(self, dst):
        #print 'esdsnidaq.getdata: dst:',dst.shape
        nsc = self.acqtask.getData(dst)
        return nsc
