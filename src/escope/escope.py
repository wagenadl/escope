#!/usr/bin/python3

# escope.py

VERSION = "4.1.0"

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import os
import re
import pickle
import numpy as np

from .escopelib import esconfig
from .escopelib.eshardware import ESHardware
from .escopelib.eschannels import ESChannels
from .escopelib.estrigger import ESTrigger
from .escopelib.esvzeromarks import ESVZeroMarks
from .escopelib.esvscalemarks import ESVScaleMarks
from .escopelib.estmarks import ESTMarks
from .escopelib.esscopewin import ESScopeWin
from .escopelib.estriggerbuffer import ESTriggerBuffer
from .escopelib import serializer
from .escopelib.ledlabel import LEDLabel
from .escopelib import esparkwin

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

def _parsefilename(name):
    m = re.search(r"(\d{8}-\d{6})-(\d{3})\.escope$", name)
    if m:
        rundate = m.group(1)
        sweepno = int(m.group(2))
    else:
        sweepno = None
        m = re.search(r"(\d{8}-\d{6})\.escope$", name)
        if m:
            rundate = m.group(1)
        else:
            rundate = "???-???"
    return rundate, sweepno


def _loadconfig(name):
    with open(name, "r") as fd:
        esc = serializer.load(fd)
    if "config" in esc:
        cfg = esc["config"]
    else:
        with open(name[:-7] + ".config") as fd:
            cfg = serializer.load(fd)
    return esc, cfg

def _loaddata(name, esc, cfg, sweepno):
    nch = len(esc["channels"])
    with open(name[:-7] + ".dat", "rb") as f:
        nscans = int(cfg.hw.acqrate.value *
                     cfg.hori.s_div * 
                     (cfg.hori.xlim[1] - cfg.hori.xlim[0]))
        nfloats = nscans * nch
        if esc["version"] >= "escope-3.2":
            typ = np.float32
            siz = 4
        else:
            typ = np.float64
            siz = 8
            f.seek(-nfloats*siz, os.SEEK_END)
        dat = np.fromfile(f, dtype=typ, count=nfloats)
        nend = f.tell()
        if sweepno is None:
            sweepno = nend // nfloats // siz
    dat = dat.reshape(len(dat) // nch, nch)
    return dat, sweepno

class MainWin(QMainWindow):
    def __init__(self, cfg, sparkcfg):
        QWidget.__init__(self)
        self.cfg = cfg
        self.sparkcfg = sparkcfg
        self.h_hw = None
        self.h_chn = None
        self.h_trig = None
        self.h_spark = None
        self.ds = None
        self.capfh = None
        self.stopRequested = False
        self.inSweep = False
        self.saveSweepRequested = False
        self.setWindowTitle('EScope')
        self.stylize()
        self.makeContents()
        self.place()

    def stylize(self):
        #self.setFont(QFont(*self.cfg.font))
        self.setStyleSheet("""
        QWidget#scope { background: black; }
        """)

    def place(self):
        scr = QApplication.desktop()
        scrw = scr.screenGeometry().width()
        scrh = scr.screenGeometry().height()
        unit = QFontMetrics(self.font()).boundingRect("X").height()
        self.resize(35*unit, 25*unit)
        self.move(int(.4*scrw) - self.width()//2, int(.45*scrh) - self.width()//2)

    def resizeEvent(self, evt):
        fm = QFontMetricsF(self.font())
        self.rpane.setFixedWidth(int(fm.boundingRect("|  500 mV").width()))
        self.bpane.setFixedHeight(int(fm.boundingRect("1 ms").height()*1.5))

    def makeContents(self):
        LSIZE = 40
        BSIZE = 35

        wid = QFontMetrics(self.font()).boundingRect("500 mV").width()
        RSIZE = max(wid + 16, 80)

        # First row of buttons
        hw = QPushButton()
        hw.setText("Hardware...")
        hw.setToolTip("Configure properties of your DAQ")
        hw.clicked.connect(self.click_hardware)

        cn = QPushButton()
        cn.setText("Channels...")
        cn.setToolTip("Configure which input channels are displayed")
        cn.clicked.connect(self.click_channels)

        tr = QPushButton()
        tr.setText("Trigger...")
        tr.setToolTip("Configure whether sweeps are started continuously or upon threshold crossing")
        tr.clicked.connect(self.click_trigger)

        stm = QPushButton()
        stm.setText("Stimuli...")
        stm.setToolTip("Configure stimulation")
        stm.clicked.connect(self.click_stim)

        # Second row of buttons
        ll = LEDLabel()
        ll.setToolTip("Bright green indicates live display, bright red indicates data are being captured to disk")
        self.h_led = ll
        
        rn = QPushButton()
        rn.setText("Run")
        rn.setToolTip("Start live update and capture (if enabled)")
        self.h_run = rn
        rn.clicked.connect(self.click_run)

        sp = QPushButton()
        sp.setText("Stop")
        sp.setToolTip("Halt live update and stop capture (if enabled)")
        self.h_stop = sp
        sp.clicked.connect(self.click_stop)
        sp.hide()

        ca = QCheckBox()
        ca.setText("Capture")
        ca.setToolTip(f"If enabled, acquired sweeps are automatically saved to “{os.getcwd()}”")
        ca.stateChanged.connect(self.click_capture)

        dsp = QComboBox()
        dsp.addItem('Dots')
        dsp.addItem('Lines')
        dsp.addItem('True')
        dsp.setToolTip("Drawing style for data")
        #dsp.setFixedHeight(20)
        dsp.currentIndexChanged.connect(self.click_display)
        self.displaystyle = dsp

        self.hdate = QLabel()
        self.hdate.setText(esconfig.datetimestr())
        self.hdate.setToolTip("This is the name of your current experiment")
        self.hsweepno = QLabel(self)
        self.hsweepno.setText("#000")
        self.hsweepno.setToolTip("This is the number of your current sweep")
        self.sweepno = 0

        # Right part of first row
        lds = QPushButton()
        lds.setText("Load Sweep...")
        lds.setToolTip("Reload previously saved data")
        lds.clicked.connect(self.click_loadsweep)

        sas = QPushButton()
        sas.setText("Save Sweep")
        sas.setToolTip("Save currently visible data to disk")
        sas.clicked.connect(self.click_savesweep)

        abt = QPushButton()
        abt.setText("About...")
        abt.clicked.connect(self.click_about)

        # Lay out the first row
        butlay = QHBoxLayout()
        butlay.addWidget(hw)
        butlay.addWidget(cn)
        butlay.addWidget(tr)
        butlay.addWidget(stm)
        butlay.addStretch(1)
        butlay.addSpacing(20)
        butlay.addWidget(lds)
        butlay.addWidget(sas)
        fr = QFrame()
        fr.setFrameShape(QFrame.StyledPanel)
        fr.setFixedWidth(2)
        butlay.addWidget(fr)
        butlay.addWidget(abt)

        # Lay out the second row
        but2lay = QHBoxLayout()
        but2lay.addWidget(ll)
        but2lay.addWidget(rn)
        but2lay.addWidget(sp)
        but2lay.addWidget(ca)
        but2lay.addWidget(dsp)
        but2lay.addStretch(1)
        but2lay.addWidget(self.hdate)
        but2lay.addWidget(self.hsweepno)

        # Set up overall layout
        """Although we are a QMainWindow, we don't use Qt's toolbar
        and dockingarea system. Our overall organization is:
        
        self
          - central: mainlay
              - docks: docklay
                  - hardware
                  - channels
                  - trigger
               - main: vlay
                   - butlay (top row of buttons)
                   - but2lay (second row of buttons)
                   - scope: vlay2
                       - axlay
                           - lpane (ESVZeroMarks)
                           - apane (ESScopeWin)
                           - rpane (ESVScaleMarks)
                       - botlay
                           - bpane (ESTMarks)
        """
        central = QWidget()
        self.setCentralWidget(central)
        mainlay = QHBoxLayout(central)
        docks = QWidget()
        docklay = QVBoxLayout(docks)
        self.docklay = docklay
        main = QWidget()
        mainlay.addWidget(docks)
        mainlay.addWidget(main)
        vlay = QVBoxLayout(main)
        vlay.addLayout(butlay)
        vlay.addLayout(but2lay)
        
        for h in [self.hdate, self.hsweepno]:
            p=h.palette()
            p.setColor(QPalette.WindowText,QColor("gray"))
            h.setPalette(p)
        for h in [hw, cn, tr, lds, sas, abt]:
            h.setFocusPolicy(Qt.NoFocus)

        scope = QWidget()
        scope.setObjectName("scope")
        self.scope = scope
        scope.setAutoFillBackground(True)
        vlay2 = QVBoxLayout(scope)
        axlay = QHBoxLayout()
        
        self.lpane = ESVZeroMarks(self.cfg, self)
        self.lpane.setFixedWidth(LSIZE)
        self.rpane = ESVScaleMarks(self.cfg, self)
        self.rpane.setFixedWidth(RSIZE)
        self.apane = ESScopeWin(self.cfg, self)
        self.click_display(0)
        self.apane.setMinimumSize(QSize(50,50))
        self.apane.setSizePolicy(QSizePolicy.MinimumExpanding,
                                 QSizePolicy.MinimumExpanding)
        axlay.addWidget(self.lpane)
        axlay.addWidget(self.apane)
        axlay.addWidget(self.rpane)
        vlay2.addLayout(axlay)
        self.rpane.trigChanged.connect(self.trigShifted)
        self.rpane.sclChanged.connect(self.vertChanged)
        self.lpane.cfgChanged.connect(self.vertChanged)

        botlay = QHBoxLayout()
        dummy = QWidget(self)
        dummy.setFixedSize(LSIZE, 2)
        botlay.addWidget(dummy)
        self.bpane = ESTMarks(self.cfg, self)
        self.bpane.setMinimumSize(50, BSIZE)
        self.bpane.setSizePolicy(QSizePolicy.MinimumExpanding,
                                 QSizePolicy.Fixed)
        botlay.addWidget(self.bpane)
        dummy = QWidget(self)
        dummy.setFixedSize(RSIZE, BSIZE)
        botlay.addWidget(dummy)
        vlay2.addLayout(botlay)
        vlay.addWidget(scope)
        self.bpane.trigChanged.connect(self.trigShifted)
        self.bpane.trigEnabled.connect(self.trigChanged)
        self.bpane.timeChanged.connect(self.horiChanged)

        docklay.setSpacing(4)
        docklay.setContentsMargins(4,20,4,6)
        mainlay.setSpacing(0)
        mainlay.setContentsMargins(0,0,0,0)
        vlay.setSpacing(0)
        vlay2.setSpacing(0)
        axlay.setSpacing(0)
        botlay.setSpacing(0)
        vlay.setContentsMargins(0,0,8,8)
        vlay2.setContentsMargins(0,8,2,3)
        axlay.setContentsMargins(0,0,0,0)
        botlay.setContentsMargins(0,0,0,0)
        butlay.setContentsMargins(8,8,0,8)
        butlay.setSpacing(10)
        but2lay.setContentsMargins(8,0,0,8)
        but2lay.setSpacing(10)
        self.apane.sweepStarted.connect(self.sweepStarted)
        self.apane.sweepComplete.connect(self.sweepComplete)
        self.apane.cursorsMoved.connect(self.updateCursors)
        self.apane.sweepComplete.connect(self.updateDataAt)
        self.makedocks()

    def updateCursors(self):
        self.bpane.setCursors(*self.apane.cursors())
        self.updateDataAt()
        
    def updateDataAt(self):
        xdiv, xdiv0, xtrig = self.apane.cursors()
        if xdiv is None:
            self.bpane.setData(None)
        else:
            data = self.apane.dataAt(xdiv)
            if xdiv0 is None:
                data0 = None
            else:
                data0 = self.apane.dataAt(xdiv0)
            self.bpane.setData(data, data0)

    def makedocks(self):
        self.h_hw = ESHardware(self.cfg)
        self.h_hw.cfgChanged.connect(self.hwChanged)
        self.docklay.addWidget(self.h_hw)
        self.h_hw.hide()
        self.h_chn = ESChannels(self.cfg)
        self.h_chn.cfgChanged.connect(self.chnChanged)
        self.docklay.addWidget(self.h_chn)
        self.h_chn.hide()
        self.h_trig = ESTrigger(self.cfg)
        self.h_trig.cfgChanged.connect(self.trigChanged)
        self.docklay.addWidget(self.h_trig)
        self.h_trig.hide()
        self.docklay.addStretch(1)
        
    def click_hardware(self):
        self.h_hw.reconfig()
        self.h_hw.setVisible(not self.h_hw.isVisible())
            
    def click_channels(self):
        self.h_chn.reconfig()
        self.h_chn.setVisible(not self.h_chn.isVisible())

    def click_trigger(self):
        self.h_trig.reconfig()
        self.h_trig.setVisible(not self.h_trig.isVisible())


    def click_run(self):
        self.startRun()

    def click_stop(self):
        self.stopRunSoon()
        if self.h_spark:
            self.h_spark.click_stop()

    def click_capture(self, on):
        self.cfg.capt_enable = not not on
        if self.cfg.capt_enable:
            self.h_led.setColor([1, 0, 0], [0.2, 1, 0.3])
        else:
            self.h_led.setColor([0.2, 1, 0.3])            
        self.restart()

    def deviceerror(self, msg):
        self.click_stop()
        QMessageBox.warning(self, "EScope",
                            "Device error: {msg}. Acquisition stopped.")

    def spark_runrequest(self):
        if not self.ds:
            self.startRun()
        self.h_spark.setAcqTask(self.ds.source.acqtask)
        self.h_spark.startRun()

    def startRun(self):
        self.h_run.hide()
        self.h_stop.show()
        self.h_led.turnOn()
        self.stopRequested = False
        self.inSweep = False
        self.ds = ESTriggerBuffer(self.cfg)
        self.ds.deviceError.connect(self.deviceerror)
        if self.h_spark:
            self.ds.reconfig(self.h_spark.cfg)
        else:
            self.ds.reconfig()
        self.sweepno = 0
        self.rundate = esconfig.datetimestr()
        self.hdate.setText(self.rundate)
        self.hsweepno.setText('#000')
        p=self.hsweepno.palette()
        p.setColor(QPalette.WindowText, QColor("black"))
        self.hsweepno.setPalette(p)
        self.apane.startRun(self.ds)
        if self.cfg.capt_enable:
            self.writeInfoFile()
            self.ds.startCapture(self.rundate)
            p=self.hdate.palette()
            p.setColor(QPalette.WindowText, QColor("black"))
            self.hdate.setPalette(p)
        if self.ds.run():
            print('Running')
        else:
            raise AttributeError('Failed to run')
        self.update()

    def stopRunSoon(self):
        if self.cfg.hori.s_div>=1 or not self.inSweep:
            self.stopRun()
        else:
            self.stopRequested = True
            print('Stopping soon')

    def stopRun(self):
        if not self.ds:
            return
        self.inSweep = False
        self.apane.stopRun()
        self.ds.stop()
        self.ds.stopCapture()
        if self.h_spark:
            self.h_spark.setAcqTask(None)
        self.ds = None
        p=self.hsweepno.palette()
        p.setColor(QPalette.WindowText,QColor("gray"))
        self.hsweepno.setPalette(p)
        p=self.hdate.palette()
        p.setColor(QPalette.WindowText,QColor("gray"))
        self.hdate.setPalette(p)
        print('Stopped')
        self.h_run.show()
        self.h_stop.hide()
        self.h_led.turnOff()

    def sweepComplete(self):
        self.inSweep = False
        if self.saveSweepRequested:
            self.saveSweep()
            self.saveSweepRequested = False
        if self.stopRequested:
            self.stopRun()
            self.stopRequested = False

    def sweepStarted(self):
        self.sweepno += 1
        self.hsweepno.setText('#%03i' % self.sweepno)
        self.inSweep = True

    def restart(self):
        wasRunning = self.ds is not None
        if wasRunning:
            self.stopRun()
            self.startRun()
        self.update()

    def hwChanged(self):
        #print 'HARDWARE changed'
        if self.h_chn is not None and self.h_chn.isVisible():
            self.h_chn.reconfig()
        if self.h_spark:
            self.h_spark.updaterecconfig(self.cfg)
        self.restart()

    def chnChanged(self):
        #print 'CHANNELS changed'
        if self.h_trig is not None and self.h_trig.isVisible():
            self.h_trig.reconfig()
        self.restart()

    def trigChanged(self):
        #print 'TRIGGER changed'
        if self.h_trig is not None and self.h_trig.isVisible():
            if self.h_trig.h_enable.isChecked() != self.cfg.trig.enable:
                self.h_trig.h_enable.setChecked(self.cfg.trig.enable)
        self.restart()

    def trigShifted(self):
        if self.ds is not None:
            self.ds.rethresh()
        if self.h_trig is not None and self.h_trig.isVisible():
            if self.h_trig.h_auto.isChecked() != self.cfg.trig.auto:
                self.h_trig.h_auto.setChecked(self.cfg.trig.auto)
        self.update()

    def vertChanged(self,k):
        #print 'VERTICAL changed', k
        self.apane.rebuild()
        if self.ds is not None:
            self.ds.rethresh()
        self.update()

    def horiChanged(self):
        #print 'HORIZONTAL changed'
        self.restart()

    def writeInfoFile(self, name=None):
        if name is None:
            name = self.rundate
        with open(name + ".escope", "w") as fd:
            js = { "version": self.cfg.VERSION,
                   "rundate": self.rundate,
                   "rate_Hz": self.cfg.hw.acqrate.value}
            chs = []
            for ch in self.cfg.conn.hw:
                if not np.isnan(ch):
                    chs.append(self.cfg.hw.channels[int(ch)])
            js["channels"] = chs
            scl = []
            for ch in range(len(self.cfg.conn.hw)):
                if not np.isnan(self.cfg.conn.hw[ch]):
                    scl.append(f"{self.cfg.conn.scale[ch]:.5g} {self.cfg.conn.units[ch]}")
            js["scale"] = scl
            js["sweep_s"] = self.cfg.hori.s_div*(self.cfg.hori.xlim[1] - self.cfg.hori.xlim[0])
            js["sweep_scans"] = int(js["sweep_s"] * self.cfg.hw.acqrate.value)
            js["config"] = self.cfg
            serializer.dump(js, fd)
                                           
        #with open(name + ".config", "w") as fd:
        #    serializer.dump(self.cfg, fd)

    def saveSweep(self):
        if self.apane.dat is None:
            return # Nothing to save
        dat = self.apane.dat[:self.apane.write_idx,:]
        name = f"{self.rundate}-{self.sweepno:03d}"
        f = open(name + ".dat", "wb")
        f.write(dat.astype(np.float32))
        f.close()
        self.writeInfoFile(name)

    def click_loadsweep(self):
        wasRunning = self.ds is not None
        if wasRunning:
            self.stopRun()

        name, _ = QFileDialog.getOpenFileName(self,
                                              "Load Sweep",
                                              os.getcwd(),
                                              "EScope files (*.escope)")
        if not name:
            return

        rundate, sweepno = _parsefilename(name)
        esc, cfg = _loadconfig(name)
        dat, sweepno = _loaddata(name, esc, cfg, sweepno)

        self._updatetoloadedsweep(cfg, rundate, sweepno)

    def _updatetoloadedsweep(self, cgf, rundate, sweepno):
        self.cfg.hw = cfg.hw
        self.cfg.conn = cfg.conn
        self.cfg.trig = cfg.trig
        self.cfg.vert = cfg.vert
        self.cfg.hori = cfg.hori
        if self.h_hw is not None and self.h_hw.isVisible():
            self.h_hw.reconfig()
        if self.h_chn is not None and self.h_chn.isVisible():
            self.h_chn.reconfig()
        if self.h_trig is not None and self.h_trig.isVisible():
            self.h_trig.reconfig()
        self.apane.forceFeed(dat)
        self.rundate = rundate
        self.hdate.setText(self.rundate)
        self.sweepno = sweepno
        self.hsweepno.setText('#%03i' % self.sweepno)
        self.update()

    def click_savesweep(self):
        print("clicksave", self.ds)
        self.saveSweep()
        if not self.apane.sweepIsComplete() and self.ds is not None:
            self.saveSweepRequested = True

    def click_about(self):
        abt = QMessageBox()
        txt = f"""<b>EScope</b> v. {VERSION}<br>

        (C) 2010, 2023–2025 Daniel A. Wagenaar<br><br>

        <b>EScope</b> is an electronic oscilloscope.  More
        information, including a user manual, is available at <a
        href="https://github.com/wagenadl/escope">github</a> and <a
        href="https://escope.readthedocs.org">readthedocs</a>.<br><br>

        <b>EScope</b> is free software: you can redistribute it and/or
        modify it under the terms of the GNU General Public License as
        published by the Free Software Foundation, either version 3 of
        the License, or (at your option) any later
        version.<br><br>

        <b>EScope</b> is distributed in the hope
        that it will be useful, but WITHOUT ANY WARRANTY; without even
        the implied warranty of MERCHANTABILITY or FITNESS FOR A
        PARTICULAR PURPOSE. See the GNU General Public License for
        more details.<br><br>You should have received a copy of the GNU
        General Public License along with this program. If not, see <a
        href="http://www.gnu.org/licenses/gpl-3.0.en.html">www.gnu.org/licenses/gpl-3.0.en.html</a>.
        
        """
        abt.setText(txt)
        abt.setWindowTitle("About EScope")
        abt.exec_()

    def click_stim(self):
        if self.h_spark is None:
            self.h_spark = esparkwin.MainWin(self.sparkcfg, self.cfg)
            self.h_spark.channelsChanged.connect(self.spark_channel_change)
            self.h_spark.runRequested.connect(self.spark_runrequest)
        if self.h_spark.isVisible():
            self.h_spark.close()
        else:
            self.h_spark.show()
            
    def spark_channel_change(self):
        if self.cfg.hw.adapter == self.h_spark.cfg.hw.adapter:
            self.restart()

    def click_display(self, val):
        self.apane.setDisplayStyle(val)

    def closeEvent(self,evt):
        self.click_stop()
        QApplication.quit()

def main():
    print(f'This is EScope {VERSION}')
    print("(C) 2010, 2023–2025 Daniel A. Wagenaar")
    print("EScope is free software. Click “About” to learn more.")
    
    os.chdir(os.path.expanduser("~/Documents"))
    if not os.path.exists("EScopeData"):
        os.mkdir("EScopeData")
    os.chdir("EScopeData")
    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()
    sparkcfg = esparkwin.espconfig.basicconfig()

    mw = MainWin(cfg, sparkcfg)

    mw.displaystyle.setCurrentIndex(2)
    mw.displaystyle.hide() # on modern computer hardware, this control is not needed, and it confuses students
    mw.show()
    app.exec_()
    

if __name__=='__main__':
    main()
