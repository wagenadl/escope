# esnidaq.py - This file is part of EScope/ESpark
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


"""esnidaq.py
Wrapper for NIDAQmx functions
This started from Dr Lock's work at
http://www.drlock.com/projects/pyrwi/docs/examples/index.php?ex=ContAcq_nidaqmx
For version 2.0, this was rewritten extensively to use the newer “nidaqmx” module from NI.
"""

import numpy as np

try:
    import nidaqmx
    import nidaqmx.errors
    import nidaqmx.stream_readers
    import nidaqmx.stream_writers
    import nidaqmx.constants
    try:
        nidaqmx.system.System.local()
    except nidaqmx.errors.DaqNotSupportedError:
        raise ImportError
    nidaq = True
    print("(got nidaqmx)")
except ImportError:
    nidaq = None
    print("No nidaqmx library")

        
#%%
# Some constants
if nidaq:
    DAQmx_RSE = nidaqmx.constants.TerminalConfiguration.RSE
    DAQmx_Volts = nidaqmx.constants.VoltageUnits.VOLTS
    DAQmx_Rising = nidaqmx.constants.Edge.RISING
    
    DAQmx_FiniteSamps = nidaqmx.constants.AcquisitionType.FINITE
    DAQmx_ContSamps = nidaqmx.constants.AcquisitionType.CONTINUOUS
    DAQmx_HWTimedSinglePoint = nidaqmx.constants.AcquisitionType.HW_TIMED_SINGLE_POINT
    DAQmx_ChanPerLine = nidaqmx.constants.LineGrouping.CHAN_PER_LINE
    

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

def devDOChannels(dev):
    system = nidaqmx.system.System.local()
    chs = [c.name for c in system.devices[dev].do_lines]
    return [c.replace(dev + '/', '').replace("port", "P").replace("/line", ".") for c in chs]

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
        print(C, nscans)
        n = self.rdr.read_many_sample(dat, nscans)
        dst[:n,:] = dat.T
        return n


######################################################################

class FiniteProdTask:
    def __init__(self, dev, chans, genrate_hz, data):
        self.dev = dev
        self.chans = chans # i.e., names of the channels
        self.genrate_hz = genrate_hz
        self.th = None
        self.data = data # TxC
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
        self.ath = nidaqmx.Task()
        self.adata = []
        self.dth = nidaqmx.Task()
        self.ddata = []
        for k, ch in enumerate(self.chans):
            if ch.lower().startswith("a"):
                self.ath.ao_channels.add_ao_voltage_chan(self.dev + "/" + ch,
                                                         ch,
                                                         min_val=-10, max_val=10,
                                                         units=DAQmx_Volts)
                self.adata.append(self.data[:,k].copy())
            else:
                lines = self.dev + "/" + ch.replace("P", "port").replace(".", "/line")
                self.dth.do_channels.add_do_chan(lines, line_grouping=DAQmx_ChanPerLine)
                self.ddata.append((self.data[:,k]>0).astype(np.uint32)*0xffffffff)
        self.adata = np.array(self.adata)
        self.ddata = np.array(self.ddata)
        self.ath.timing.cfg_samp_clk_timing(rate=self.genrate_hz,
                                                active_edge=DAQmx_Rising,
                                                sample_mode=DAQmx_FiniteSamps,
                                                samps_per_chan=self.adata.shape[-1])
        if len(self.ddata):
            src = f"/{self.dev}/ao/SampleClock"
            self.dth.timing.cfg_samp_clk_timing(rate=self.genrate_hz,
                                                source=src,
                                                active_edge=DAQmx_Rising,
                                                sample_mode=DAQmx_FiniteSamps,
                                                samps_per_chan=self.ddata.shape[-1])
                    
        if self.foo is not None:
            if len(self.adata):
                self.ath.register_done_event(self.foo)
            elif len(self.ddata):
                self.dth.register_done_event(self.foo)
        self.prepped = True

    def run(self):
        if not self.prepped:
            self.prep()
        if self.running:
            return
        #nwritten = int32()
        #offset = 0
        if len(self.adata):
            awrtr = nidaqmx.stream_writers.AnalogMultiChannelWriter(self.ath.out_stream)
            nawritten = awrtr.write_many_sample(self.adata)
        if len(self.ddata):
            dwrtr = nidaqmx.stream_writers.DigitalMultiChannelWriter(self.dth.out_stream)
            ndwritten = dwrtr.write_many_sample_port_uint32(self.ddata) # this may not be correct
            self.dth.start() # this waits for the analog task if both exists
        if len(self.adata):
            self.ath.start()
        self.running = True
     
    def stop(self):
        if self.running:
            if len(self.ddata):
                self.dth.stop()
            if len(self.adata):
                self.ath.stop()
            self.running = False

    def isRunning(self):
        if not self.running:
            return False
        if len(self.adata):
            th = self.ath
        else:
            th = self.dth
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
            if nidaq is not None:
                if self.ath is not None:
                    self.ath.close()
                    self.ath = None
                if self.dth is not None:
                    self.dth.close()
                    self.dth = None

######################################################################
if nidaq:
    try:
        if not deviceList():
            nidaq = None
            print("No nidaq devices")
    except nidaqmx.errors.DaqNotFoundError as e:
        nidaq = None
        print(e)
        print("No nidaq devices")
