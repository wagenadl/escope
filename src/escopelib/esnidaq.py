"""esnidaq.py
Wrapper for NIDAQmx functions
This started from Dr Lock's work at
http://www.drlock.com/projects/pyrwi/docs/examples/index.php?ex=ContAcq_nidaqmx
"""

import numpy as np

try:
    import nidaqmx
    import nidaqmx.stream_readers
    nidaq = True
except ImportError:
    nidaq = None
    print("no nidaqmx")
    

# The constants
DAQmx_RSE = nidaqmx.constants.TerminalConfiguration.RSE
DAQmx_Volts = nidaqmx.constants.VoltageUnits.VOLTS
DAQmx_Rising = nidaqmx.constants.Edge.RISING

DAQmx_FiniteSamps = nidaqmx.constants.AcquisitionType.FINITE
DAQmx_ContSamps = nidaqmx.constants.AcquisitionType.CONTINUOUS
DAQmx_HWTimedSinglePoint= nidaqmx.constants.AcquisitionType.HW_TIMED_SINGLE_POINT
 
# Values for the everyNsamplesEventType parameter of
# DAQmxRegisterEveryNSamplesEvent
DAQmx_Val_Acquired_Into_Buffer = 1 # Acquired Into Buffer
DAQmx_Val_Transferred_From_Buffer = 2 # Transferred From Buffer


def deviceList():
    if nidaq is None:
        return []
    system = nidaqmx.system.System.local()
    devs = [dev.name for dev in system.devices]
    print("device list", devs)
    return devs

def devAIChannels(dev):
    system = nidaqmx.system.System.local()
    chs = [c.name for c in system.devices[dev].ai_physical_chans]
    return [c.replace(dev + '/', '') for c in chs]

def devAOChannels(dev):
    system = nidaqmx.system.System.local()
    chs = [c.name for c in system.devices[dev].ao_physical_chans]
    return [c.replace(dev + '/', '') for c in chs]

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
            print('DAQ', a, 'prepped')
            thisbad = True
        if dq.th:
            print('DAQ', a, 'has nonzero taskhandle')
            thisbad = True
        if thisbad:
            dq.stop()
            dq.unprep()
            good = False
    if not good and newid is not None:
        print('(while working on DAQ', newid, ')')
        


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
        self.rdr = None

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
        if nidaq is None:
            raise AttributeError('No NIDAQ library found')
        self.th = nidaqmx.Task()
        try:
            self.nchans = 0
            for k in range(len(self.chans)):
                ch = self.chans[k]
                rng = self.range[k]
                if rng>10.:
                    rng = 10.
                self.th.ai_channels.add_ai_voltage_chan(self.dev + "/" + ch,
                                                        ch,
                                                        terminal_config=DAQmx_RSE,
                                                        min_val=-rng, max_val=rng)
                self.nchans += 1
            
            self.th.timing.cfg_samp_clk_timing(self.acqrate_hz,
                                               active_edge=DAQmx_Rising,
                                               sample_mode=DAQmx_ContSamps,
                                               samps_per_chan=self.nscans)
            if self.foo is not None:
                self.th.register_every_n_samples_acquired_into_buffer_event(self.nscans, self.foo)

        except RuntimeError as e:
            print('Preparation failed:', e)
            self.th.close()
            self.th = None
            self.collectionid = None
        else:
            contacq_collection[self.collectionid] = self
            contacq_taskfinder[self.th.name] = self.collectionid
            self.prepped = True
            
    def run(self):
        if not self.prepped:
            self.prep()
        if not self.prepped:
            print('Failed to prepare, cannot run')
            return
        if self.running:
            return
        self.rdr = nidaqmx.stream_readers.AnalogMultiChannelReader(self.th.in_stream)
        self.th.start()
        self.running = True
     
    def stop(self):
        if self.running:
            self.th.stop()
            self.running = False
            self.rdr = None

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
                del contacq_taskfinder[self.th.name]
            self.collectionid = None
            if nidaq:
                self.th.close()
            self.th = None
    
    def getData(self, dst):
        if not self.running:
            return 0
        T, C = dst.shape
        nscans = min(T, self.nscans)
        dat = np.empty((C, nscans))
        n = self.rdr.read_many_sample(dat, nscans)
        dst[:n,:] = dat.T
        return n


######################################################################
finiteprod_nextid = 1
finiteprod_collection = {}

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
        if nidaq is None:
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
        print('genrate is ', self.genrate_hz)
        print('shape is ', self.data.shape[0])
        CHK(nidaq.DAQmxCfgSampClkTiming(self.th,"",
                                        float64(self.genrate_hz),
                                        DAQmx_Val_Rising,
                                        DAQmx_Val_FiniteSamps,
                                        uInt64(self.data.shape[0])))
        CHK(nidaq.DAQmxCfgOutputBuffer(self.th,uInt32(self.data.shape[0])))
        if self.foo is not None:
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
            if nidaq is not None and self.th is not None:
                CHK(nidaq.DAQmxClearTask(self.th))
            self.th = None
