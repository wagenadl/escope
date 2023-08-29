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

PRIMELIM = 10 # Number of samples of continuously-below-trigger required

class ESTriggerBuffer(ESDataSource):
    trigAvailable = pyqtSignal()
    
    def __init__(self, cfg):
        ESDataSource.__init__(self, cfg)
        self.source = None
        self.read_idx = 0
        self.write_idx = 0
        self.capfh = None
        #self.mutex = QMutex()

    def rethresh(self):
        if self.cfg.trig.enable:
            if self.cfg.trig.auto:
                self.nextautotrig_idx = self.write_idx + self.per_scans + self.cfg.hw.acqrate.value
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
        

    def reconfig(self):
        ESDataSource.reconfig(self)
        typ = self.cfg.hw.adapter[0]
        if typ=='dummy':
            self.source = ESDS_Dummy(self.cfg)
        elif typ=='nidaq':
            self.source = ESDS_Nidaq(self.cfg)
        else:
            raise AttributeError('Unknown data source type')
        self.source.dataAvailable.connect(self.importData)
        self.source.reconfig()
        per_s = self.cfg.hori.s_div * (self.cfg.hori.xlim[1] -
                                       self.cfg.hori.xlim[0])
        self.per_scans = int(per_s*self.cfg.hw.acqrate.value)
        self.buffer = np.zeros((3*self.per_scans, self.nchan))
        # print self.buffer.shape, per_s, self.cfg.hw.acqrate.value, self.nchan
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

    def importData(self):
        #lock = QMutexLocker(self.mutex)
        origidx = self.write_idx
        relidx = self.write_idx % self.buffer.shape[0]
        offset = self.write_idx//self.buffer.shape[0]
        offset *= self.buffer.shape[0]
        nrows = self.source.getData(self.buffer[relidx:,:])
        self.write_idx += nrows
        if self.cfg.trig.enable:
            if self.trig_idx is not None:
                #lock = None
                self.dataAvailable.emit()
                #lock = QMutexLocker(self.mutex)
                if self.write_idx-self.trig_idx >= self.posttrig_scans:
                    self.trig_idx=None
            elif origidx>=self.nexttrigok_idx:
                src = self.buffer[relidx:relidx+nrows, self.trig_column]
                if self.cfg.trig.direction>0:
                    k = 0
                    if self.trig_primed<PRIMELIM:
                        while k<src.size:
                            if src[k]<self.trig_revert:
                                self.trig_primed += 1
                                if self.trig_primed>=PRIMELIM:
                                    break
                            else:
                                self.trig_primed = 0
                            k += 1
                    if self.trig_primed>=PRIMELIM:
                        while k<src.size:
                            if src[k]>self.trig_volt and origidx+k>=self.pretrig_scans:
                                self.trig_idx = origidx + k
                                self.nexttrigok_idx = self.trig_idx + self.per_scans
                                break
                            k += 1
                else:
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
                if self.trig_idx is None:
                    if origidx>=self.nextautotrig_idx:
                        dx = self.nextautotrig_idx-self.read_idx
                        if dx<self.pretrig_scans:
                            self.trig_idx = self.read_idx + self.pretrig_scans
                        else:
                            self.trig_idx = self.nextautotrig_idx
                            self.read_idx = self.trig_idx - self.pretrig_scans
                        self.nexttrigok_idx = self.trig_idx + self.per_scans
                        self.nextautotrig_idx = self.trig_idx + 2*self.per_scans + self.cfg.hw.acqrate.value
                        #lock = None
                        self.trigAvailable.emit()
                    pass
                else:
                    self.trig_primed = 0
                    self.read_idx = self.trig_idx - self.pretrig_scans
                    if self.cfg.trig.auto:
                        self.nextautotrig_idx = self.trig_idx + 2*self.per_scans + self.cfg.hw.acqrate.value
                    #lock = None
                    self.trigAvailable.emit()
        else:
            #lock = None
            self.dataAvailable.emit()

    def getData(self, dst):
        #lock = QMutexLocker(self.mutex)
        if self.cfg.trig.enable:
            if self.trig_idx is None:
                now = 0
            else:
                now = min(self.write_idx-self.read_idx,
                          dst.shape[0],
                          self.trig_idx+self.posttrig_scans-self.read_idx)
        else:
            now = min(self.write_idx - self.read_idx, dst.shape[0])
        if now==0:
            return 0
        
        i0 = self.read_idx % self.buffer.shape[0]
        i1 = (self.read_idx+now) % self.buffer.shape[0]
        if i1==0:
            i1 = self.buffer.shape[0]
        #print 'i0=',i0, 'i1=',i1, 'now=',now
        #print 'dst:',dst.shape, 'buf:',self.buffer.shape
        #print 'readidx=',self.read_idx,'writeidx=',self.write_idx, 'trigidx=',self.trig_idx
        if i1<=i0:
            # Must do it in two bits
            n0 = self.buffer.shape[0] - i0
            dst[:n0,:] = self.buffer[i0:,:]
            dst[n0:now,:] = self.buffer[:i1,:]
        else:
            dst[:now,:] = self.buffer[i0:i1,:]

        self.read_idx += now
        if self.capfh:
            self.writeData(dst,now)
        return now

    def writeData(self, src, nscan):
        self.capfh.write(src[:nscan,:])
    
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
    
