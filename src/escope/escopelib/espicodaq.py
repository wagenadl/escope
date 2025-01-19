# espicodaq.py - This file is part of EScope/ESpark
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


"""espicodaq.py
Wrapper for picoDAQ functions
"""

import numpy as np
from numpy.typing import ArrayLike
from typing import List, Optional, Tuple, Callable
from PyQt5.QtCore import QTimer, QThread, QMutex, pyqtSignal, Qt
from multiprocessing.connection import Connection


try:
    import picodaq
    from picodaq.background import DAQProcess
    pdaq = True
    print("(got picodaq)")
except ImportError as exc:
    import sys
    pdaq = None
    print(exc)
    print("No picodaq library")


class Mutex(QMutex):
    def __enter__(self):
        self.lock()
        return self

    def __exit__(self, *args):
        self.unlock()

    
def deviceList() -> List[str]:
    if pdaq is None:
        return []   
    devs = []
    for port in picodaq.device.picodaqs():
        if port.startswith("/dev/ttyACM"):
            devs.append(port[8:])
        else:
            devs.append(port)
    return devs


def devAIChannels(dev: str) -> List[str]:
    if dev.startswith("ACM"):
        dev = "/dev/tty" + dev
    p = picodaq.device.PicoDAQ(dev)
    info = p.deviceinfo()
    nAIchannels = int(info['AI'])
    return [f"ai{k}" for k in range(nAIchannels)]


def devAOChannels(dev: str) -> List[str]:
    if dev.startswith("ACM"):
        dev = "/dev/tty" + dev
    p = picodaq.device.PicoDAQ(dev)
    info = p.deviceinfo()
    nAOchannels = int(info['AO'])
    return [f"ao{k}" for k in range(nAOchannels)]


def devDOChannels(dev: str) -> List[str]:
    if dev.startswith("ACM"):
        dev = "/dev/tty" + dev
    p = picodaq.device.PicoDAQ(dev)
    info = p.deviceinfo()
    nDOchannels = int(info['DO'])
    return [f"do{k}" for k in range(nDOchannels)]


######################################################################
class Reader(QThread):
    dataAvailable = pyqtSignal()
    
    def __init__(self, conn: Connection, callback: Optional[Callable],
                 every: int):
        super().__init__()
        self.conn = conn
        self.stopsoon = False
        self.data = []
        if callback is not None and every > 0:
            self.dataAvailable.connect(callback, Qt.QueuedConnection)
        self.mutex = Mutex()
        self.every = every
        self.accum = 0
        super().start()

    def stop(self) -> None:
        self.stopsoon = True
        if not self.wait(1000):
            raise RuntimeError("Could not stop reader thread")

    def accumulated(self):
        with self.mutex:
            acc = self.accum
        return acc

    def read(self, count=None) -> Optional[Tuple[ArrayLike, ArrayLike]]:
        """Read accumulated data

        If count is given, reads at most that many scans.
        Otherwise, reads one chunk.
        Returns an (adata, ddata) pair or None
        """
        if count:
            adat = []
            ddat = []
            got = 0
            with self.mutex:
                while self.data and got < count:
                    adat1, ddat1 = self.data[0]
                    N = len(adat1)
                    now = min(N, count - got)
                    adat.append(adat1[:now])
                    ddat.append(ddat1[:now])
                    if now < N:
                        adat1 = adat1[now:]
                        ddat1 = ddat1[now:]
                        self.data[0] = (adat1, ddat1)
                    else:
                        del self.data[0]
                    got += now
            if got > 0:
                adat = np.concatenate(adat, 0)
                ddat = np.concatenate(ddat, 0)
                return adat, ddat
            else:
                return None
        else:
            dat = None
            with self.mutex:
                if self.data:
                    dat = self.data.pop(0)
            return dat
        
    def run(self):
        # Do not call, private thread function
        print("reader running")
        while not self.stopsoon:
            if self.conn.poll(0.1):
                try:
                    dat = self.conn.recv() # adata, ddata
                except EOFError:
                    print("eoferror")
                    self.dataAvailable.emit() # lie, but we need attention
                    break
                #print(type(dat))
                with self.mutex:
                    self.data.append(dat)
                    self.accum += len(dat[0])
                    mustemit = self.accum >= self.every
                #print(len(self.data), self.accum, self.every, mustemit)
                if mustemit:
                    self.accum -= self.every
                    self.dataAvailable.emit()
        print("reader done")

######################################################################
class ContAcqTask:
    def __init__(self, dev: str, chans: List[int],
                 acqrate_hz: float, rnge):
        self.dev = dev # e.g., "ACM0"
        self.chans = chans
        self.acqrate_hz = acqrate_hz
        self.foo = None
        self.pd = None # a picodaq.background.DAQProcess instance
        self.rd = None # a Reader instance
        self.nscans = 1000
        self.prepped = False
        self.running = False
        self.rdr = None
        self.stimcfg = None
        self.ochans: List[str] = []

    def __del__(self):
        self.stop()
        self.unprep()

    def setstimconfig(self, stimcfg):
        self.stimcfg = stimcfg
        self.ochans = []
        if stimcfg:
            for c in stimcfg.conn.hw:
                if c is not None:
                    self.ochans.append(self.stimcfg.hw.channels[c])
            

    def setCallback(self, foo: Callable, nscans: int):
        self.unprep()
        self.foo = foo
        self.nscans = nscans

    def prep(self):
        if self.prepped:
            return
        if not pdaq:
            raise RuntimeError('No picoDAQ library found')
        ichans = []
        for c in self.chans:
            if c.startswith("ai"):
                ichans.append(int(c[2:]))
        self.nchans = len(ichans)
        ochans = []
        olines = []
        for chn in self.ochans:
            if chn.startswith("ao"):
                ochans.append(int(chn[2:]))
            elif chn.startswith("do"):
                olines.append(int(chn[2:]))
            else:
                raise ValueError("Bad channel name")
        self.pd = DAQProcess(port=self.dev,
                             rate=self.acqrate_hz*picodaq.units.Hz,
                             aichannels=ichans,
                             aochannels=ochans,
                             dolines=olines)
        self.prepped = True

    def feedstimdata(self, data: ArrayLike) -> None:
        """Add data to output queue
        Shape of data must match config
        """
        if not self.pd:
            raise RuntimeError("Not prepared")
        aidx = []
        didx = []
        for k, chn in enumerate(self.ochans):
            if chn.startswith("ao"):
                aidx.append(k)
            elif chn.startswith("do"):
                didx.append(k)
            else:
                raise ValueError("Bad channel name")
        self.pd.write(data[:,aidx], data[:,didx])
            
    def run(self) -> None:
        if not self.prepped:
            self.prep()
        if not self.prepped:
            raise RuntimeError('Failed to prepare, cannot run')
        if self.running:
            return
        print("espicodaq run")
        self.pd.start()
        self.rd = Reader(self.pd.conn, self.foo, self.nscans)
        self.running = True
     
    def stop(self) -> None:
        if self.running:
            self.rd.stop()
            self.rd = None
            self.running = False
            self.pd.stop()

    def unprep(self) -> None:
        if self.running:
            raise RuntimeError('Cannot unprepare while running')
        if self.prepped:
            self.prepped = False
            self.pd = None
    
    def getData(self, dst: np.ndarray) -> int:
        if not self.running:
            return 0
        T, C = dst.shape
        nscans = min(T, self.nscans)
        adat, ddat = self.rd.read(nscans)
        n = len(adat)
        dst[:n, :] = adat
        return n

######################################################################


class FiniteProdTask:
    def __init__(self, dev: str, chans: List[str],
                 genrate_hz: float, data: ArrayLike):
        self.dev = dev
        self.chans = chans # i.e., names of the channels
        self.genrate_hz = genrate_hz
        self.pd = None
        self.rd = None
        self.foo = None
        self.prepped = False
        self.running = False
        self.data = data

    def __del__(self):
        self.stop()
        self.unprep()

    def setData(self, data: ArrayLike) -> None:
        self.unprep()
        self.data = data

    def setCallback(self, foo: Callable) -> None:
        self.unprep()
        self.foo = foo

    def prep(self) -> None:
        if self.prepped:
            return
        if not pdaq:
            raise RuntimeError('No PicoDAQ library found')
        print("dev = ", self.dev)
        ochans = []
        olines = []
        aidx = []
        didx = []
        for k, chn in enumerate(self.chans):
            if chn.startswith("ao"):
                ochans.append(int(chn[2:]))
                aidx.append(k)
            elif chn.startswith("do"):
                olines.append(int(chn[2:]))
                didx.append(k)
            else:
                raise ValueError("Bad channel name")
        self.pd = DAQProcess(port=self.dev,
                             rate=self.genrate_hz*picodaq.units.Hz,
                             aochannels=ochans,
                             dolines=olines)
        self.pd.write(self.data[:,aidx], self.data[:,didx])
        self.prepped = True

    def run(self):
        if not self.prepped:
            self.prep()
        if self.running:
            return
        self.rd = Reader(self.pd.conn, self.foo, len(self.data))
        self.pd.start()
        self.running = True
     
    def stop(self):
        if not self.running:
            return
        self.rd.stop()
        self.rd = None
        self.pd.stop()
        self.running = False

    def isRunning(self):
        if not self.running:
            return False
        if self.rd.accumulated() >= len(self.data):
            stop()
            return False
        return True       
    
    def unprep(self):
        #print 'FiniteProdTask: unprep, nidaq=',nidaq, ' prepped=',self.prepped, ' th=',self.th
        if self.isRunning():
            raise RuntimeError('Cannot unprepare while running')
        if self.prepped:
            self.prepped = False
            self.pd = None
            
######################################################################
if pdaq:
    if not deviceList():
        pdaq = None
        print("No picoDAQ devices")
                    
