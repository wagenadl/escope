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


try:
    import picodaq
    import picodaq.qadc
    import picodaq.qdac
    pdaq = True
    print("(got picodaq)")
except ImportError:
    import sys
    pdaq = None
    print("No picodaq library")


def deviceList():
    if pdaq is None:
        return []   
    devs = []
    for port in picodaq.device.picodaqs():
        if port.startswith("/dev/ttyACM"):
            devs.append(port[8:])
        else:
            devs.append(port)
    return devs

def devAIChannels(dev):
    if dev.startswith("ACM"):
        dev = "/dev/tty" + dev
    p = picodaq.device.PicoDAQ(dev)
    info = p.deviceinfo()
    nAIchannels = int(info['AI'])
    return [f"ai{k}" for k in range(nAIchannels)]

def devAOChannels(dev):
    if dev.startswith("ACM"):
        dev = "/dev/tty" + dev
    p = picodaq.device.PicoDAQ(dev)
    info = p.deviceinfo()
    nAOchannels = int(info['AO'])
    return [f"ao{k}" for k in range(nAOchannels)]

def devDOChannels(dev):
    if dev.startswith("ACM"):
        dev = "/dev/tty" + dev
    p = picodaq.device.PicoDAQ(dev)
    info = p.deviceinfo()
    nDOchannels = int(info['DO'])
    return [f"do{k}" for k in range(nDOchannels)]

######################################################################
class ContAcqTask:
    def __init__(self, dev, chans, acqrate_hz, rnge):
        self.dev = dev # e.g., "ACM0"
        self.chans = chans
        self.range = rnge
        self.acqrate_hz = acqrate_hz
        self.foo = None
        self.th = None # a picodaq.qadc.ADC instance
        self.nscans = 1000
        self.prepped = False
        self.running = False
        self.rdr = None

    def __del__(self):
        self.stop()
        self.unprep()

    def setCallback(self, foo, nscans):
        self.unprep()
        self.foo = foo
        self.nscans = nscans

    def prep(self):
        if self.prepped:
            return
        if picodaq is None:
            raise AttributeError('No picoDAQ library found')
        chans = []
        for c in self.chans:
            if c.startswith("ai"):
                chans.append(int(c[2:]))
        self.nchans = len(chans)
        self.th = picodaq.qadc.ADC(self.dev) # must pick correct dev
        self.th.setAnalogChannels(chans)
        self.th.setRate(self.acqrate_hz*picodaq.units.Hz)
        if self.foo is not None:
            self.th.setEvery(self.nscans, self.foo)
        self.prepped = True
            
    def run(self):
        if not self.prepped:
            self.prep()
        if not self.prepped:
            print('Failed to prepare, cannot run')
            return
        if self.running:
            return
        self.th.start()
        self.running = True
     
    def stop(self):
        if self.running:
            self.th.stop()
            self.running = False

    def unprep(self):
        if self.running:
            raise AttributeError('Cannot unprepare while running')
        if self.prepped:
            self.prepped = False
            self.th = None
    
    def getData(self, dst):
        if not self.running:
            return 0
        T, C = dst.shape
        nscans = min(T, self.nscans)
        adat, ddat = self.th.read(nscans)
        n = len(adat)
        dst[:n, :] = adat
        return n

######################################################################


class FiniteProdTask:
    def __init__(self, dev, chans, genrate_hz, data):
        self.dev = dev
        self.chans = chans # i.e., names of the channels
        self.genrate_hz = genrate_hz
        self.th = None
        self.foo = None
        self.prepped = False
        self.running = False

    def __del__(self):
        self.stop()
        self.unprep()

    def setData(self, data):
        self.unprep()
        self.data = data

    def setCallback(self, foo):
        self.unprep()
        self.foo = foo

    def prep(self):
        if self.prepped:
            return
        if picodaq is None:
            raise AttributeError('No PicoDAQ library found')
        print("dev = ", self.dev)
        self.th = picodaq.qdac.DAC(self.dev)
        for k, ch in enumerate(self.chans):
            if ch.lower().startswith("ao"):
                self.th.addAnalogSource(int(ch[2:], self.data[:,k]))
            elif ch.lower().startswith("do"):
                self.th.addDigitalSource(int(ch[2:], self.data[:,k]))
        self.th.setRate(self.genrate_hz * picodaq.units.Hz)
        self.prepped = True

    def run(self):
        if not self.prepped:
            self.prep()
        if self.running:
            return
        self.th.start(self.foo)
        self.running = True
     
    def stop(self):
        if self.running:
            self.th.stop()
            self.running = False

    def isRunning(self):
        if not self.running:
            return False
        if self.th.isfinished():
            self.running = False
            self.th.stop()
            return False
        return True       
    
    def unprep(self):
        #print 'FiniteProdTask: unprep, nidaq=',nidaq, ' prepped=',self.prepped, ' th=',self.th
        if self.isRunning():
            raise AttributeError('Cannot unprepare while running')
        if self.prepped:
            self.prepped = False
            self.th = None
######################################################################
if picodaq:
    if not deviceList():
        pdaq = None
        print("No picoDAQ devices")
                    
