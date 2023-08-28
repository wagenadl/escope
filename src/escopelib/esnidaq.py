"""esnidaq.py
Wrapper for NIDAQmx functions
This started from Dr Lock's work at
http://www.drlock.com/projects/pyrwi/docs/examples/index.php?ex=ContAcq_nidaqmx
"""

import ctypes
import numpy as np
import pylab as pl
import time
import sys

try:
    nidaq = ctypes.windll.nicaiu # load the DLL
except AttributeError:
    nidaq = None
    

##############################
# Setup some typedefs and constants to correspond with values in
# C:\Program Files\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include\NIDAQmx.h

# The typedefs
int32 = ctypes.c_int32
uInt32 = ctypes.c_uint32
uInt64 = ctypes.c_uint64
float64 = ctypes.c_double
TaskHandle = uInt32

# The constants
DAQmx_Val_Cfg_Default = int32(-1)
DAQmx_Val_RSE = 10083
DAQmx_Val_Volts = 10348
DAQmx_Val_Rising = 10280
 
DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123
DAQmx_Val_HWTimedSinglePoint= 12522
 
# Values for the everyNsamplesEventType parameter of
# DAQmxRegisterEveryNSamplesEvent
DAQmx_Val_Acquired_Into_Buffer = 1 # Acquired Into Buffer
DAQmx_Val_Transferred_From_Buffer = 2 # Transferred From Buffer
 
# Values for the Fill Mode parameter of DAQmxReadXXX and for the
# Data Layout parameter of DAQmxWriteXXX
DAQmx_Val_GroupByChannel = 0 # Group by Channel
DAQmx_Val_GroupByScanNumber = 1 # Group by Scan Number

DAQmx_Val_Task_Abort = 6

# ----------------------------------------------------------------------
def mkBuf(nBytes):
    return ctypes.create_string_buffer(nBytes)

def CHK(err, th=None):
    """a simple error checking routine"""
    if err < 0:
        buf = mkBuf(500)
        nidaq.DAQmxGetErrorString(err, ctypes.byref(buf), 500)
        exc = RuntimeError('NIDAQ call failed with error %d: %s' %
                           (err, repr(buf.value)))
        if th!=None:
            nidaq.DAQmxTaskControl(th,DAQmx_Val_Task_Abort)
        raise exc

# ----------------------------------------------------------------------
def taskNames():
    if nidaq==None:
        return []
    buf = mkBuf(2000)
    err = nidaq.DAQmxGetSysTasks(ctypes.byref(buf), 2000)
    if err:
        return []
    devs = buf.value
    return devs.split(', ')
    
def deviceList():
    if nidaq==None:
        return []
    buf = mkBuf(2000)
    err = nidaq.DAQmxGetSysDevNames(ctypes.byref(buf), 2000)
    if err:
        return []
    devs = buf.value
    return devs.split(', ')

def devTypeName(dev):
    typ = mkBuf(256)
    CHK(nidaq.DAQmxGetDevProductType(dev, typ, 256))
    return typ.value

def devTypeCode(dev):
    prodnum = ctypes.c_uint32()
    CHK(nidaq.DAQmxGetDevProductNum(dev, ctypes.byref(prodnum)))
    return prodnum.value

def devSerialNo(dev):
    sernum = ctypes.c_uInt32()
    CHK(nidaq.DAQmxGetDevSerialNum(dev, ctypes.byref(sernum)))
    return sernum.value

def devAIChannels(dev):
    buf = mkBuf(2000)
    CHK(nidaq.DAQmxGetDevAIPhysicalChans(dev, ctypes.byref(buf), 2000))
    chs = buf.value
    chs = chs.replace(dev + '/', '')
    return chs.split(', ')

def devAOChannels(dev):
    buf = mkBuf(2000)
    CHK(nidaq.DAQmxGetDevAOPhysicalChans(dev, ctypes.byref(buf), 2000))
    chs = buf.value
    chs = chs.replace(dev + '/', '')
    return chs.split(', ')

######################################################################
contacq_nextid = 1
contacq_collection = {}
contacq_taskfinder = {}

def assert_none_prepped(newid=None):
    good = True
    for a in contacq_collection.keys():
        dq = contacq_collection[a]
        thisbad = False
        if dq.prepped:
            print 'DAQ', a, 'prepped'
            thisbad = True
        if dq.th:
            print 'DAQ', a, 'has nonzero taskhandle'
            thisbad = True
        if thisbad:
            dq.stop()
            dq.unprep()
            good = False
    if not good and newid!=None:
        print '(while working on DAQ', newid, ')'
        

EVERYNFUNC = ctypes.CFUNCTYPE(int32, TaskHandle, int32, uInt32,
                              ctypes.c_void_p)
def everyN(th, everyNsamplesEventType, nSamples, callbackData):
    global contacq_collection
    #print 'everyN', th, everyNsamplesEventType, nSamples, callbackData
    if th in contacq_taskfinder:
        callbackData = contacq_taskfinder[th]
    if callbackData in contacq_collection:
        #print '  calling foo with', nSamples
        contacq_collection[callbackData].foo(nSamples)
    else:
        raise AttributeError('everyN called with unknown task')
    return 0
EveryNCallback_func = EVERYNFUNC(everyN)

class ContAcqTask:
    def __init__(self, dev, chans, acqrate_hz, rnge):
        self.dev = dev
        self.collectionid = None
        self.chans = chans
        self.range = rnge
        self.acqrate_hz = acqrate_hz
        self.foo = None
        self.th = None
        self.nscans = 1000
        self.prepped = False
        self.running = False

    def __del__(self):
        self.stop()
        self.unprep()

    def setCallback(self, foo, nscans):
        self.unprep()
        self.foo = foo
        self.nscans = nscans

    def prep(self):
        global contacq_nextid
        global contacq_collection
        if self.prepped:
            return
        assert_none_prepped(contacq_nextid)
        self.collectionid = contacq_nextid
        contacq_nextid += 1
        if nidaq==None:
            raise AttributeError('No NIDAQ library found')
        self.th = TaskHandle(0)
        CHK(nidaq.DAQmxCreateTask("foo",ctypes.byref(self.th)))
        taskNames()
        
        try:
            self.nchans = 0
            for k in range(len(self.chans)):
                ch = self.chans[k]
                rng = self.range[k]
                if rng>10.:
                    rng = 10.
                CHK(nidaq.DAQmxCreateAIVoltageChan(self.th,
                                                   self.dev+"/"+ch,"",
                                                   DAQmx_Val_RSE,
                                                   float64(-rng),float64(rng),
                                                   DAQmx_Val_Volts, None))
                self.nchans += 1
            
            CHK(nidaq.DAQmxCfgSampClkTiming(self.th,"",
                                            float64(self.acqrate_hz),
                                            DAQmx_Val_Rising,
                                            DAQmx_Val_ContSamps,
                                            uInt64(self.nscans)))
            if self.foo!=None:
                CHK(nidaq.DAQmxRegisterEveryNSamplesEvent(self.th,
                                                          DAQmx_Val_Acquired_Into_Buffer,
                                                          self.nscans,
                                                          0,
                                                          EveryNCallback_func,
                                                          25))
        except RuntimeError as e:
            print 'Preparation failed:', e
            try:
                if nidaq:
                    CHK(nidaq.DAQmxClearTask(self.th))
            except RunTimeError as e:
                print 'Double failure:', e
            self.th = None
            self.collectionid = None
        else:
            contacq_collection[self.collectionid] = self
            contacq_taskfinder[self.th.value] = self.collectionid
            self.prepped = True
            
    def run(self):
        if not self.prepped:
            self.prep()
        if not self.prepped:
            print 'Failed to prepare, cannot run'
            return
        if self.running:
            return
        CHK(nidaq.DAQmxStartTask(self.th))
        self.running = True
     
    def stop(self):
        if self.running:
            CHK(nidaq.DAQmxTaskControl(self.th,DAQmx_Val_Task_Abort))
            self.running = False

    def unprep(self):
        global contacq_collection
        if self.running:
            raise AttributeError('Cannot unprepare while running')
        if self.prepped:
            self.prepped = False
            if contacq_collection:
                # ^ This checks that the collection hasn't been deleted yet
                # if this unprep is due to program exit
                del contacq_collection[self.collectionid]
            if contacq_taskfinder:
                del contacq_taskfinder[self.th.value]
            self.collectionid = None
            if nidaq:
                CHK(nidaq.DAQmxClearTask(self.th))
            self.th = None
    
    def getData(self, dst):
        nscans = min(dst.shape[0],self.nscans)
        nread = int32()
        if self.running:
            CHK(nidaq.DAQmxReadAnalogF64(self.th, nscans, float64(10.0),
                                         DAQmx_Val_GroupByScanNumber,
                                         dst.ctypes.data,nscans*self.nchans,
                                         ctypes.byref(nread),None), self.th)
        return nread.value

######################################################################
finiteprod_nextid = 1
finiteprod_collection = {}
DONEFUNC = ctypes.CFUNCTYPE(int32, TaskHandle, int32, ctypes.c_void_p)
def DoneCallback(taskHandle, status, callbackData):
    global finiteprod_collection
    if callbackData in finiteprod_collection:
        finiteprod_collection[callbackData].foo()
    return 0;
DoneCallback_func = DONEFUNC(DoneCallback)
 
class FiniteProdTask:
    def __init__(self, dev, chans, genrate_hz, data):
        self.dev = dev
        self.collectionid = None
        self.chans = chans
        self.genrate_hz = genrate_hz
        self.th = None
        self.nscans = 0
        self.data = data
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
        global finiteprod_nextid
        global finiteprod_collection
        if self.prepped:
            return
        self.collectionid = finiteprod_nextid
        finiteprod_nextid += 1
        if nidaq==None:
            raise AttributeError('No NIDAQ library found')
        self.th = TaskHandle(0)
        CHK(nidaq.DAQmxCreateTask("",ctypes.byref(self.th)))
        self.nchans = 0
        for ch in self.chans:
            CHK(nidaq.DAQmxCreateAOVoltageChan(self.th,
                                               self.dev+"/"+ch, "",
                                               float64(-10.0),float64(10.0),
                                               DAQmx_Val_Volts, None))
            self.nchans += 1
        print 'genrate is ', self.genrate_hz
        print 'shape is ', self.data.shape[0]
        CHK(nidaq.DAQmxCfgSampClkTiming(self.th,"",
                                        float64(self.genrate_hz),
                                        DAQmx_Val_Rising,
                                        DAQmx_Val_FiniteSamps,
                                        uInt64(self.data.shape[0])))
        CHK(nidaq.DAQmxCfgOutputBuffer(self.th,uInt32(self.data.shape[0])))
        if self.foo!=None:
            CHK(nidaq.DAQmxRegisterDoneEvent(self.th, 0,
                                             DoneCallback_func,
                                             self.collectionid))
        finiteprod_collection[self.collectionid] = self
        self.prepped = True

    def run(self):
        if not self.prepped:
            self.prep()
        if self.running:
            return
        nwritten = int32()
        offset = 0
        while offset<self.data.shape[0]:
            now = self.data.shape[0] - offset
            CHK(nidaq.DAQmxWriteAnalogF64(self.th, int32(now),
                                      int32(0), float64(0.0),
                                      DAQmx_Val_GroupByScanNumber,
                                      self.data[offset:,:].ctypes.data,
                                      ctypes.byref(nwritten), None))
            if nwritten<=0:
                raise ValueError('Could not write all data')
            offset += nwritten.value
        CHK(nidaq.DAQmxStartTask(self.th))
        self.running = True
     
    def stop(self):
        if self.running:
            CHK(nidaq.DAQmxTaskControl(self.th,DAQmx_Val_Task_Abort))
            self.running = False

    def isRunning(self):
        if not self.running:
            return False
        if nidaq.DAQmxWaitUntilTaskDone(self.th, float64(0.0001)):
            # ^ The NIDAQ docs say that I can use float64(0.0) for immediate
            # answer, but that did not work for me. So I wait 0.1 ms instead.
            return True
        self.running = False
        return False
    
    def unprep(self):
        #print 'FiniteProdTask: unprep, nidaq=',nidaq, ' prepped=',self.prepped, ' th=',self.th
        global finiteprod_collection
        if self.isRunning():
            raise AttributeError('Cannot unprepare while running')
        if self.prepped:
            self.prepped = False
            if finiteprod_collection:
                # ^ This checks that the collection hasn't been deleted yet
                # if this unprep is due to program exit
                del finiteprod_collection[self.collectionid]
            self.collectionid = None
            if nidaq!=None and self.th!=None:
                CHK(nidaq.DAQmxClearTask(self.th))
            self.th = None
