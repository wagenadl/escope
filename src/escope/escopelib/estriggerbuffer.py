# estriggerbuffer.py - This file is part of EScope/ESpark
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


# estriggerbuffer.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
from . import esconfig
import numpy as np
import ctypes
from .esdatasource import ESDataSource
from .esdatasource import ESDS_Dummy
from .esdsnidaq import ESDS_Nidaq
from .esdspicodaq import ESDS_Picodaq


PRIMELIM = 10 # Number of samples of continuously-below-trigger required

class ESTriggerBuffer(ESDataSource):
    trigAvailable = pyqtSignal()
    deviceError = pyqtSignal(str)
    
    def __init__(self, cfg):
        super().__init__(cfg)
        self.source = None
        self.read_idx = 0
        self.write_idx = 0
        self.capfh = None
        #self.mutex = QMutex()

    def rethresh(self):
        if self.cfg.trig.enable:
            if self.cfg.trig.auto:
                self.nextautotrig_idx = int(self.write_idx + self.per_scans + self.cfg.hw.acqrate.value)
            else:
                self.nextautotrig_idx = 1000*1000*1000
            self.pretrig_scans = int(self.cfg.trig.delay_div *
                                     self.cfg.hori.s_div *
                                     self.cfg.hw.acqrate.value)
            self.posttrig_scans = self.per_scans - self.pretrig_scans
            tc = 0
            s = self.cfg.trig.source
            for a in range(s):
                if not np.isnan(self.cfg.conn.hw[a]):
                    tc += 1
            self.trig_column = tc
            
            self.trig_volt = ((self.cfg.trig.level_div -
                               self.cfg.vert.offset_div[s]) *
                              self.cfg.vert.unit_div[s])
            self.trig_revert = (self.trig_volt -
                                self.cfg.trig.direction *
                                0.2*self.cfg.vert.unit_div[s])
            self.primelim = max(10,
                                self.cfg.hori.s_div*
                                self.cfg.hw.acqrate.value*0.2)
        

    def reconfig(self, stimcfg=None):
        super().reconfig()
        typ = self.cfg.hw.adapter[0]
        if typ=='dummy':
            self.source = ESDS_Dummy(self.cfg)
        elif typ=='nidaq':
            self.source = ESDS_Nidaq(self.cfg)
        elif typ=='picodaq':
            self.source = ESDS_Picodaq(self.cfg, stimcfg)
        else:
            raise AttributeError('Unknown data source type')
        self.source.dataAvailable.connect(self.importData)
        self.source.reconfig()
        per_s = self.cfg.hori.s_div * (self.cfg.hori.xlim[1] -
                                       self.cfg.hori.xlim[0])
        self.per_scans = int(per_s*self.cfg.hw.acqrate.value)
        self.buffer = np.zeros((3*self.per_scans, self.nchan))
        self.write_idx = 0
        self.read_idx = 0
        self.trig_idx = None
        if self.cfg.trig.enable:
            self.nexttrigok_idx = 0
            self.trig_primed = 0
        self.rethresh()

    def startCapture(self, fn):
        self.capfh = open(fn + ".dat","wb")

    def stopCapture(self):
        if self.capfh:
            self.capfh.close()
        self.capfh = None

    def run(self):
        self.source.run()
        return ESDataSource.run(self)

    def stop(self):
        self.source.stop()
        ESDataSource.stop(self)


    def _import_hunttrig_up(self, src, origidx):
        k = 0
        if self.trig_primed < PRIMELIM:
            while k < src.size:
                if src[k] < self.trig_revert:
                    self.trig_primed += 1
                    if self.trig_primed >= PRIMELIM:
                        break
                else:
                    self.trig_primed = 0
                k += 1
        if self.trig_primed >= PRIMELIM:
            while k < src.size:
                if src[k] > self.trig_volt and origidx + k >= self.pretrig_scans:
                    self.trig_idx = origidx + k
                    self.nexttrigok_idx = self.trig_idx + self.per_scans
                    break
                k += 1

    def _import_huntttrig_down(self, src, origidx):
        k = 0
        if self.trig_primed<PRIMELIM:
            while k<src.size:
                if src[k]>self.trig_revert:
                    self.trig_primed += 1
                    if self.trig_primed>=PRIMELIM:
                        break
                else:
                    self.trig_primed = 0
                k += 1
        if self.trig_primed>=PRIMELIM:
            while k<src.size:
                if src[k]<self.trig_volt and origidx+k>=self.pretrig_scans:
                    self.trig_idx = origidx + k
                    self.nexttrigok_idx = self.trig_idx + self.per_scans
                    break
                k += 1

    def _import_autotrig(self):
        dx = self.nextautotrig_idx - self.read_idx
        if dx<self.pretrig_scans:
            self.trig_idx = self.read_idx + self.pretrig_scans
        else:
            self.trig_idx = self.nextautotrig_idx
            self.read_idx = self.trig_idx - self.pretrig_scans
        self.nexttrigok_idx = self.trig_idx + self.per_scans
        self.nextautotrig_idx = int(self.trig_idx + 2*self.per_scans + self.cfg.hw.acqrate.value)
        self.trigAvailable.emit()        

    def _import_triggered(self):
        self.trig_primed = 0
        self.read_idx = self.trig_idx - self.pretrig_scans
        if self.cfg.trig.auto:
            self.nextautotrig_idx = self.trig_idx + 2*self.per_scans + self.cfg.hw.acqrate.value
        #lock = None
        self.trigAvailable.emit()

        
    def importData(self):
        #lock = QMutexLocker(self.mutex)
        origidx = self.write_idx
        relidx = self.write_idx % self.buffer.shape[0]
        offset = self.write_idx // self.buffer.shape[0]
        offset *= self.buffer.shape[0]
        try:
            nrows = self.source.getData(self.buffer[relidx:,:])
        except RuntimeError as exc:
            print("estriggerbuffer exception: ", exc)
            self.deviceError.emit(str(exc))
            return # we are called from a signal, so what can we do?
        if nrows == 0:
            return
        
        self.write_idx += nrows
        
        if self.cfg.trig.enable:
            if self.trig_idx is not None:
                self.dataAvailable.emit()
                if self.write_idx - self.trig_idx >= self.posttrig_scans:
                    self.trig_idx = None

            elif origidx >= self.nexttrigok_idx:
                
                src = self.buffer[relidx:relidx+nrows, self.trig_column]
                if self.cfg.trig.direction > 0:
                    self._import_hunttrig_up(src, origidx)
                else:
                    self._import_hunttrig_down(src, origidx)

                if self.trig_idx is None:
                    if origidx >= self.nextautotrig_idx:
                        self._import_autotrig()
                else:
                    self._import_triggered()
        else:
            #lock = None
            self.dataAvailable.emit()

    def getData(self, dst):
        #lock = QMutexLocker(self.mutex)
        if self.cfg.trig.enable:
            if self.trig_idx is None:
                now = 0
            else:
                now = min(self.write_idx - self.read_idx,
                          dst.shape[0],
                          self.trig_idx + self.posttrig_scans - self.read_idx)
        else:
            now = min(self.write_idx - self.read_idx, dst.shape[0])
        if now==0:
            return 0
        
        i0 = self.read_idx % self.buffer.shape[0]
        i1 = (self.read_idx + now) % self.buffer.shape[0]
        if i1 == 0:
            i1 = self.buffer.shape[0]
        if i1 <= i0:
            # Must do it in two bits
            n0 = self.buffer.shape[0] - i0
            dst[:n0,:] = self.buffer[i0:,:]
            dst[n0:now,:] = self.buffer[:i1,:]
        else:
            dst[:now,:] = self.buffer[i0:i1,:]

        self.read_idx += now
        if self.capfh:
            self.writeData(dst, now)
        return now

    def writeData(self, src, nscan):
        self.capfh.write(src[:nscan,:].astype(np.float32))
    
if __name__ == "__main__":
    app = QApplication(sys.argv)

    cfg = esconfig.basicconfig()
    cfg.trig.enable = True
    cfg.trig.level_div = 2
    ds = ESTriggerBuffer(cfg)
    ds.reconfig()
    dst = np.zeros((ds.period_scans,ds.nchan))

    def rcv():
        global dst
        n = ds.getData(dst)
        print("Recv!", dst.ctypes.data)
        print(np.mean(dst,0))
        print(np.std(dst,0))
        
    ds.trigAvailable.connect(rcv)
    ds.dataAvailable.connect(rcv)

    win = QWidget()
    win.show()

    ds.reconfig()
    ds.run()
    
    app.exec_()
    
