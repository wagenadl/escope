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
from PyQt5.QtCore import QTimer, pyqtSignal, Qt, QProcess
import time

try:
    import picodaq
    pdaq = True
    print("(got picodaq)")
    pdserver = "pdserver"
except ImportError as exc:
    import sys
    pdaq = None
    print(exc)
    print("No picodaq library")

    
def deviceList() -> List[str]:
    if pdaq is None:
        return []   
    devs = []
    for port in picodaq.device.devices():
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


######################################################################
class ContAcqTask:
    def __init__(self, dev: str, chans: List[str],
                 acqrate_hz: float, rnge):
        self.dev = dev # e.g., "ACM0"
        self.chans = chans # "aix"
        self.acqrate_hz = acqrate_hz
        self.foo = None
        self.pd = None # a pdserver QProcess
        self.buffer = [] # incoming
        self.bufcount = 0
        self.every = 1000
        self.prepped = False
        self.running = False
        self.stimcfg = None
        self.ochans: List[str] = [] # "aox" and "dox"
        self.timer = None

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

    def setCallback(self, foo: Callable, every: int):
        self.unprep()
        self.foo = foo
        self.every = every

    def prep(self):
        if self.prepped:
            return
        if not pdaq:
            raise RuntimeError('No picoDAQ library found')


        for c in self.chans:
            if not c.startswith("ai"):
                raise ValueError("Bad channel name")
        for chn in self.ochans:
            if not chn.startswith("ao") and not chn.startswith("do"):
                raise ValueError("Bad channel name")
        
        self.pd = QProcess()
        self.pd.setProgram(pdserver)
        self.pd.setArguments([self.dev, f"{int(self.acqrate_hz)}"]
                             + self.chans + self.ochans)
        self.pd.readyReadStandardOutput.connect(lambda: self.readproc())
        self.pd.setProcessChannelMode(QProcess.ForwardedErrorChannel)
        self.prepped = True

    def feedstimdata(self, data: ArrayLike) -> None:
        """Add data to output queue
        Shape of data must match config
        """
        print("espicodaq feedstimdata", data.shape, np.std(data, 0))
        if not self.pd:
            raise RuntimeError("Not prepared")
        bts = data.astype(np.float32).tobytes()
        if self.pd.write(bts) != len(bts):
            raise RuntimeError("Failed to write to picoDAQ process")
            
    def run(self) -> None:
        print("espicodaq run")
        if not self.prepped:
            self.prep()
        if not self.prepped:
            raise RuntimeError('Failed to prepare, cannot run')
        if self.running:
            return
        self.pd.start()
        if not self.pd.waitForStarted(1000):
            print(self.pd.errorString())
            print(self.pd.readAllStandardError())
            raise Exception("picoDAQ process not started")
        self.running = True
        print("espicodaq running")
     
    def stop(self) -> None:
        print("espicodaq stop")
        if self.running:
            self.running = False
            self.pd.close()
            if self.pd.atEnd():
                print("stopped")
                return
            if not self.pd.waitForFinished(1000):
                print("picoDAQ process not finished")
                self.pd.terminate()
                if not self.pd.waitForFinished(1000):
                    raise RuntimeError("picoDAQ process not finished")

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
        if not len(self.buffer):
            return 0      
        dat = np.concatenate(self.buffer, 0)
        
        nscans = min(T, self.every, len(dat))
        if nscans < len(dat):
            self.buffer = [dat[nscans:]]
            self.bufcount = len(self.buffer[0])
        else:
            self.buffer = []
            self.bufcount = 0
        dst[:nscans] = dat[:nscans]
        return nscans

    def readproc(self):
        dat = self.pd.read(1200) # arbitrary, to be fixed
        ar = np.frombuffer(dat, np.float32).reshape(-1, len(self.chans))
        self.bufcount += len(ar)
        self.buffer.append(ar)
        if self.bufcount >= self.every:
            self.bufcount -= self.every
            if self.foo:
                self.foo()
 

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
        raise RuntimeError("Not yet implemented")

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
                    
