# esdatasource.py - This file is part of EScope/ESpark
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


# esdatasource.py - abstract data source

from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
from . import esconfig
import numpy as np
import ctypes

class ESDataSource(QObject):
    dataAvailable = pyqtSignal()
    
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.running = False

    def reconfig(self):
        per_s = self.cfg.hori.s_div * (self.cfg.hori.xlim[1] -
                                       self.cfg.hori.xlim[0])
        if per_s >= 10:
            per_s /= 100
        elif per_s >= 0.1:
            per_s = 0.1
        self.period_scans = int(per_s * self.cfg.hw.acqrate.value)
        self.period_s = self.period_scans/self.cfg.hw.acqrate.value
        useme = ~np.isnan(self.cfg.conn.hw)
        self.nchan=sum(useme)
        self.chans=self.cfg.conn.hw[useme]
        self.range=20*self.cfg.vert.unit_div[useme]

    def run(self):
        print('ESDS: running')
        self.running = True
        return True

    def stop(self):
        self.running = False

    def getData(self, dst):
        """Retrieves data as a numpy array

        An array must be passed in, so no memory allocation is performed.
        The array may not be filled to capacity.
        getData returns the number of rows filled."""
        return 0
    

class ESDS_Dummy(ESDataSource):
    def __init__(self, cfg):
        ESDataSource.__init__(self, cfg)
        self.timerid = None
        self.acqtask = None

    def reconfig(self):
        ESDataSource.reconfig(self)
        self.t = 0
        self.ddt = np.arange(0,self.period_scans)/self.cfg.hw.acqrate.value

    def run(self):
        ESDataSource.run(self)
        if self.timerid is not None:
            self.killTimer(self.timerid)
        self.timerid = self.startTimer(int(self.period_s*1000))
        
    def stop(self):
        if self.timerid is not None:
            self.killTimer(self.timerid)
        ESDataSource.stop(self)

    def timerEvent(self, evt):
        self.dataAvailable.emit()

    def getData(self, dst):
        now = min(self.period_scans, dst.shape[0])
        dst[:now,:] = .1*np.random.standard_normal((now, self.nchan))
        ff=[3,10,30,100,300,1,0.3,0.1]
        for k in range(self.nchan):
            f = ff[int(self.chans[k])]
            dst[:now,k] += np.sin(2*np.pi*f*(self.t+self.ddt[:now]))
        self.t += now/self.cfg.hw.acqrate.value
        return now

if __name__ == "__main__":
    app = QApplication(sys.argv)

    cfg = esconfig.basicconfig()
    ds = ESDS_Dummy(cfg)
    ds.reconfig()
    dst = np.zeros((ds.period_scans,ds.nchan))

    def rcv():
        global dst
        n = ds.getData(dst)
        print("Recv!", dst.ctypes.data)
        print(np.mean(dst,0))
        print(np.std(dst,0))
        
    ds.dataAvailable.connect(rcv)

    win = QWidget()
    win.show()

    ds.reconfig()
    ds.run()
    
    app.exec_()
