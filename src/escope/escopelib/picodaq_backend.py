from multiprocessing import Process, Pipe, Event
from multiprocessing.connection import Connection
from picodaq.units import Frequency, kHz, ms
from picodaq.adc import AnalogIn, DigitalIn
from picodaq.dac import AnalogOut, DigitalOut
from threading import Lock
from typing import List, Callable
from numpy.typing import ArrayLike
from PyQt5.QtCore import pyqtSignal, QThread, Qt
import time
import numpy as np

t0 = time.time()
def rtime():
    return f"* {time.time() - t0:.3f} * "

def _backend(conn: Connection, evt: Event,
             port: str, rate: Frequency,
             aichannels: List[int],
             dilines: List[int],
             aochannels: List[int],
             dolines: List[int]):
    print(rtime(), " - starting")
    astimdata = {c: [] for c in aochannels}
    dstimdata = {c: [] for c in dolines}
    def agen(c):
        while True:
            if astimdata[c]:
                #print("- agen", c, len(astimdata[c]), astimdata[c][0].shape)
                yield astimdata[c].pop(0)
            else:
                #print("- agen", c, "none")
                yield np.zeros(100, np.float32)              
    def dgen(c):
        while True:
            if dstimdata[c]:
                yield dstimdata[c].pop(0)
            else:
                yield np.zeros(100, np.uint8)

    print(rtime(), " - creating and opening streams")
    if aichannels:
        ai = AnalogIn(port=port, rate=rate, channels=aichannels)
        ai.open()
    else:
        ai = None
    if dilines:
        di = DigitalIn(port=port, rate=rate, lines=dilines)
        di.open()
    else:
        di = None
    if aochannels:
        ao = AnalogOut(port=port, rate=rate, maxahead=200*ms)
        ao.open()
        def agengen(c):
            return lambda: agen(c)
        for c in aochannels:
            ao[c].sampled(agengen(c))
    else:
        ao = None    
    if dolines:
        do = DigitalOut(port=port, rate=rate, maxahead=200*ms)
        do.open()
        def dgengen(c):
            return lambda: dgen(c)
        for c in dochannels:
            do[c].sampled(dgengen(c))        
    else:
        do = None

    while not evt.is_set():
        #print(rtime(), " - polling for stim")
        if conn.poll():
            print(rtime(), " - stim from frontend")
            adata, ddata = conn.recv()
            for k, c in enumerate(aochannels):
                astimdata[c].append(adata[:,k])
            for k, c in enumerate(dolines):
                dstimdata[c].append(ddata[:,k])
        #print(rtime(), " - sampling rec")
        if ai:
            adata = ai.read()
        else:
            adata = None
        if di:
            ddata = di.read()
        else:
            ddata = None
        #print(rtime(), " - rec to frontend")
        conn.send((adata, ddata))
        #print(rtime(), " - updating stim")
        if ao:
            ao.poll()
        elif do:
            do.poll()
    print(rtime(), " - out of loop")


class Backend:
    def __init__(self, port: str = "",
                 rate: Frequency = 10*kHz,
                 aichannels: List[int] = [],
                 dilines: List[int] = [],
                 aochannels: List[int] = [],
                 dolines: List[int] = []):
        parent_conn, child_conn = Pipe()
        evt = Event()
        self.evt = evt
        self.conn = parent_conn
        self.proc = Process(target=_backend,
                            args=(child_conn, evt,
                                  port, rate,
                                  aichannels, dilines,
                                  aochannels, dolines))
        self.proc.start()

    def close(self):
        if self.proc:
            print(rtime(), "closing conn")
            self.conn.close()
            print(rtime(), "setting event")
            self.evt.set()
            print(rtime(), "joining proc")
            self.proc.join(1)
            if self.proc.is_alive():
                print(rtime(), "still running")
                self.proc.terminate()
                time.sleep(0.2)
                if self.proc.is_alive():
                    print(rtime(), "still not terminated")
                    self.proc.kill()
                    time.sleep(0.2)
                    if self.proc.is_alive():
                        raise RuntimeError("Not killed")
            print(rtime(), "done")
            self.conn = None
            self.proc = None
        
    def read(self):
        # Returns an (adata, ddata) pair or None        
        if self.conn.poll():
            return self.conn.recv()
        else:
            return None

    def write(self, adata: ArrayLike, ddata: ArrayLike):
        self.conn.send((adata, ddata))
        

class Reader(QThread):
    dataAvailable = pyqtSignal()
    
    def __init__(self, conn: Connection, callback: Callable):
        super().__init__()
        self.conn = conn
        self.stopsoon = False
        self.data = []
        self.dataAvailable.connect(callback, Qt.QueuedConnection)
        self.mutex = Lock()
        super().start()

    def stop(self):
        self.stopsoon = True
        if not self.wait(1000):
            raise RuntimeError("Could not stop reader thread")
        print(rtime(), "reader stopped")

    def read(self):
        # Returns an (adata, ddata) pair or None
        # protect with a mutex?
        dat = None
        with self.mutex:
            if self.data:
                dat = self.data.pop(0)
        return dat

        
    def run(self):
        # Do not call, private thread function
        while not self.stopsoon:
            if self.conn.poll(0.1):
                dat = self.conn.recv()
                with self.mutex:
                    self.data.append(dat)
                self.dataAvailable.emit()
        print(rtime(), "reader terminating")
        
def test_short():
    sdat = np.sin(2*np.pi*np.arange(0, 0.02, 1e-4) / 0.02).reshape(-1, 1)
    pd = Backend(rate=10*kHz, aichannels=[0], aochannels=[0])
    pd.write(sdat, None)
    
    def report(rd):
        dat = rd.read()
        if dat is None:
            print("None")
        else:
            print(dat.shape, np.mean(dat), np.std(dat))
    rd = Reader(pd.conn, lambda: report(rd))
    for k in range(3):
        time.sleep(1)
        print(rtime(), "write", k)
        pd.write(sdat, None)
    print(rtime(), "stopping reader")
    rd.stop()
    print(rtime(), "closing backend")
    rd = None
    pd.close()
    print(rtime(), "backend closed")

if __name__ == "__main__":
    test_short()
    
