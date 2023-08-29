"""esnidaq.py
Wrapper for NIDAQmx functions
This started from Dr Lock's work at
http://www.drlock.com/projects/pyrwi/docs/examples/index.php?ex=ContAcq_nidaqmx
For version 2.0, this was rewritten extensively to use the newer “nidaqmx” module from NI.
"""

import numpy as np

try:
    import nidaqmx
    import nidaqmx.stream_readers
    import nidaqmx.stream_writers    
    nidaq = True
except ImportError:
    nidaq = None
    print("no nidaqmx")
    

# Some constants
DAQmx_RSE = nidaqmx.constants.TerminalConfiguration.RSE
DAQmx_Volts = nidaqmx.constants.VoltageUnits.VOLTS
DAQmx_Rising = nidaqmx.constants.Edge.RISING

DAQmx_FiniteSamps = nidaqmx.constants.AcquisitionType.FINITE
DAQmx_ContSamps = nidaqmx.constants.AcquisitionType.CONTINUOUS
DAQmx_HWTimedSinglePoint = nidaqmx.constants.AcquisitionType.HW_TIMED_SINGLE_POINT


def deviceList():
    if nidaq is None:
        return []
    system = nidaqmx.system.System.local()
    devs = [dev.name for dev in system.devices]
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


class ContAcqTask:
    def __init__(self, dev, chans, acqrate_hz, rnge):
        self.dev = dev
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
        if self.prepped:
            return
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
                                                        min_val=-rng, max_val=rng,
                                                        units=DAQmx_Volts)
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
        else:
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
        if self.running:
            raise AttributeError('Cannot unprepare while running')
        if self.prepped:
            self.prepped = False
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

class FiniteProdTask:
    def __init__(self, dev, chans, genrate_hz, data):
        self.dev = dev
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
        if self.prepped:
            return
        if nidaq is None:
            raise AttributeError('No NIDAQ library found')
        self.th = nidaqmx.Task()
        self.nchans = 0
        for ch in self.chans:
            self.th.ao_channels.add_ao_voltage_chan(self.dev + "/" + ch,
                                                    ch,
                                                    min_val=-10, max_val=10,
                                                    units=DAQmx_Volts)
            self.nchans += 1
        print('genrate is ', self.genrate_hz)
        print('shape is ', self.data.shape[0])
        self.th.timing.cfg_samp_clk_timing(self.genrate_hz,
                                           active_edge=DAQmx_Rising,
                                           sample_mode=DAQmx_FiniteSamps,
                                           samps_per_chan=self.data.shape[0])
        # CHK(nidaq.DAQmxCfgOutputBuffer(self.th,uInt32(self.data.shape[0])))
        # ?-> th.out_stream.output_buf_size = self.data.shape[0]
        if self.foo is not None:
            self.th.register_done_event(self.foo)
        self.prepped = True

    def run(self):
        if not self.prepped:
            self.prep()
        if self.running:
            return
        #nwritten = int32()
        #offset = 0
        self.th.out_stream.auto_start = True
        wrtr = nidaqmx.stream_writers.AnalogMultiChannelWriter(self.th.out_stream)
        nwritten = writr.write_many_samples(self.data.T)
        print(self.data.shape, nwritten)
        self.running = True
     
    def stop(self):
        if self.running:
            self.th.stop()
            self.running = False

    def isRunning(self):
        if not self.running:
            return False
        if th.wait_until_done(0.0001):
            # ^ The NIDAQ docs say that I can use float64(0.0) for immediate
            # answer, but that did not work for me. So I wait 0.1 ms instead.
            return True
        self.running = False
        return False
    
    def unprep(self):
        #print 'FiniteProdTask: unprep, nidaq=',nidaq, ' prepped=',self.prepped, ' th=',self.th
        if self.isRunning():
            raise AttributeError('Cannot unprepare while running')
        if self.prepped:
            self.prepped = False
            if nidaq is not None and self.th is not None:
                self.th.close()
            self.th = None
