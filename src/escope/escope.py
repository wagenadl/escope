#!/usr/bin/python3

# escope.py

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

VERSION = "3.3.0"

    
class MainWin(QWidget):
    def __init__(self,cfg):
        QWidget.__init__(self)
        self.cfg = cfg
        self.h_hw = None
        self.h_chn = None
        self.h_trig = None
        self.ds = None
        self.capfh = None
        self.stopRequested = False
        self.inSweep = False
        self.saveSweepRequested = False
        self.setWindowTitle('EScope')
        self.place()
        self.makeContents()
        self.stylize()

    def stylize(self):
        self.setFont(QFont(*self.cfg.font))
        p = self.palette()
        p.setColor(QPalette.Window,QColor("#000000"))
        self.setPalette(p)

    def place(self):
        scr = QApplication.desktop()
        scrw = scr.screenGeometry().width()
        scrh = scr.screenGeometry().height()
        self.resize(500,400)
        self.move(scrw//2-self.width()//2,scrh//2-self.width()//2)

    def makeContents(self):
        LSIZE = 40
        RSIZE = 110
        BSIZE = 35

        hw = QPushButton()
        hw.setText("Hardware...")
        hw.clicked.connect(self.click_hardware)

        cn = QPushButton()
        cn.setText("Channels...")
        cn.clicked.connect(self.click_channels)

        tr = QPushButton()
        tr.setText("Trigger...")
        tr.clicked.connect(self.click_trigger)


        ll = LEDLabel()
        ll.setToolTip("Indicates whether data are currently being acquired")
        self.h_led = ll
        
        rn = QPushButton()
        rn.setText("Run")
        self.h_run = rn
        rn.clicked.connect(self.click_run)

        sp = QPushButton()
        sp.setText("Stop")
        self.h_stop = sp
        sp.clicked.connect(self.click_stop)
        sp.hide()

        ca = QCheckBox()
        ca.setText("Capture")
        ca.stateChanged.connect(self.click_capture)

        dsp = QComboBox()
        dsp.addItem('Dots')
        dsp.addItem('Lines')
        dsp.addItem('True')
        #dsp.setFixedHeight(20)
        dsp.currentIndexChanged.connect(self.click_display)
        self.displaystyle = dsp

        self.hdate = QLabel()
        self.hdate.setText(esconfig.datetimestr())
        self.hsweepno = QLabel(self)
        self.hsweepno.setText("#000")
        self.sweepno = 0

        lds = QPushButton()
        lds.setText("Load Sweep...")
        lds.clicked.connect(self.click_loadsweep)

        sas = QPushButton()
        sas.setText("Save Sweep")
        sas.clicked.connect(self.click_savesweep)
        abt = QPushButton()
        abt.setText("About...")
        abt.clicked.connect(self.click_about)

        butlay = QHBoxLayout()
        butlay.addWidget(hw)
        butlay.addWidget(cn)
        butlay.addWidget(tr)
        butlay.addStretch(1)
        butlay.addWidget(lds)
        butlay.addWidget(sas)
        butlay.addWidget(abt)
        
        but2lay = QHBoxLayout()
        but2lay.addWidget(ll)
        but2lay.addWidget(rn)
        but2lay.addWidget(sp)
        but2lay.addWidget(ca)
        but2lay.addWidget(dsp)
        but2lay.addStretch(1)
        but2lay.addWidget(self.hdate)
        but2lay.addWidget(self.hsweepno)
        
        vlay = QVBoxLayout(self)
        vlay.addLayout(butlay)
        vlay.addLayout(but2lay)
        
        for h in [rn, ca]:
            p=h.palette()
            p.setColor(QPalette.WindowText,QColor("white"))
            h.setPalette(p)
        for h in [self.hdate, self.hsweepno]:
            p=h.palette()
            p.setColor(QPalette.WindowText,QColor("gray"))
            h.setPalette(p)
        for h in [hw, cn, tr, lds, sas, abt]:
            h.setFocusPolicy(Qt.NoFocus)

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
        vlay.addLayout(axlay)
        self.rpane.trigChanged.connect(self.trigShifted)
        self.rpane.sclChanged.connect(self.vertChanged)
        self.lpane.cfgChanged.connect(self.vertChanged)

        botlay = QHBoxLayout()
        dummy = QWidget(self)
        dummy.setFixedSize(LSIZE,BSIZE)
        botlay.addWidget(dummy)
        self.bpane = ESTMarks(self.cfg, self)
        self.bpane.setMinimumSize(50, BSIZE)
        self.bpane.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        botlay.addWidget(self.bpane)
        dummy = QWidget(self)
        dummy.setFixedSize(RSIZE,BSIZE)
        botlay.addWidget(dummy)
        vlay.addLayout(botlay)
        self.bpane.trigChanged.connect(self.trigShifted)
        self.bpane.trigEnabled.connect(self.trigChanged)
        self.bpane.timeChanged.connect(self.horiChanged)
        
        vlay.setSpacing(0)
        axlay.setSpacing(0)
        botlay.setSpacing(0)
        vlay.setContentsMargins(0,0,0,2)
        axlay.setContentsMargins(0,0,0,0)
        botlay.setContentsMargins(0,0,0,0)
        butlay.setContentsMargins(10,10,10,10)
        butlay.setSpacing(10)
        but2lay.setContentsMargins(10,0,10,10)
        but2lay.setSpacing(10)
        self.apane.sweepStarted.connect(self.sweepStarted)
        self.apane.sweepComplete.connect(self.sweepComplete)
        

    def click_hardware(self):
        if self.h_hw is None:
            self.h_hw = ESHardware(self.cfg)
            self.h_hw.cfgChanged.connect(self.hwChanged)
        self.h_hw.reconfig()
        self.h_hw.show()
        self.h_hw.raise_()
            
    def click_channels(self):
        if self.h_chn is None:
            self.h_chn = ESChannels(self.cfg)
            self.h_chn.cfgChanged.connect(self.chnChanged)
        self.h_chn.reconfig()
        self.h_chn.show()
        self.h_chn.raise_()

    def click_trigger(self):
        if self.h_trig is None:
            self.h_trig = ESTrigger(self.cfg)
            self.h_trig.cfgChanged.connect(self.trigChanged)
        self.h_trig.reconfig()
        self.h_trig.show()
        self.h_trig.raise_()

    def click_run(self):
        self.startRun()

    def click_stop(self):
        self.stopRunSoon()

    def click_capture(self, on):
        self.cfg.capt_enable = not not on
        if self.cfg.capt_enable:
            self.h_led.setColor([1, 0, 0], [0.2, 1, 0.3])
        else:
            self.h_led.setColor([0.2, 1, 0.3])            
        self.restart()

    def startRun(self):
        self.h_run.hide()
        self.h_stop.show()
        self.h_led.turnOn()
        self.stopRequested = False
        self.inSweep = False
        self.ds = ESTriggerBuffer(self.cfg)
        self.ds.reconfig()
        self.sweepno = 0
        self.rundate = esconfig.datetimestr()
        self.hdate.setText(self.rundate)
        self.hsweepno.setText('#000')
        p=self.hsweepno.palette()
        p.setColor(QPalette.WindowText,QColor("white"))
        self.hsweepno.setPalette(p)
        self.apane.startRun(self.ds)
        if self.cfg.capt_enable:
            self.writeInfoFile()
            self.ds.startCapture(self.rundate)
            p=self.hdate.palette()
            p.setColor(QPalette.WindowText,QColor("white"))
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
        self.inSweep = False
        self.apane.stopRun()
        self.ds.stop()
        self.ds.stopCapture()
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
        self.restart()

    def chnChanged(self):
        #print 'CHANNELS changed'
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
        # dlg = QFileDialog()
        # dlg.setFileMode(QfileDialog.ExistingFile)
        # dlg.setNameFilter()
        name, _ = QFileDialog.getOpenFileName(self,
                                           "Load Sweep",
                                           os.getcwd(),
                                           "EScope files (*.escope)")
        if name:
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
                    
            wasRunning = self.ds is not None
            if wasRunning:
                self.stopRun()
                
            with open(name, "r") as fd:
                esc = serializer.load(fd)
            if "config" in esc:
                cfg = esc["config"]
            else:
                with open(name[:-7] + ".config") as fd:
                    cfg = serializer.load(fd)
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
            self.update()
            self.rundate = rundate
            self.hdate.setText(self.rundate)
            self.sweepno = sweepno
            self.hsweepno.setText('#%03i' % self.sweepno)

    def click_savesweep(self):
        print("clicksave", self.ds)
        self.saveSweep()
        if not self.apane.sweepIsComplete() and self.ds is not None:
            self.saveSweepRequested = True

    def click_about(self):
        abt = QMessageBox()
        txt = f"""<b>EScope</b> v. {VERSION}<br>

        (C) 2010, 2023, 2024 Daniel A. Wagenaar<br><br>

        <b>EScope</b> is an electronic oscilloscope.  More
        information, including a user manual, is available at <a
        href="https://github.com/wagenadl/escope">github</a> and <a
        href="https://escope.readthedocs.org">readthedocs</a>.<br><br>

        <b>EScope</b> is free software: you can redistribute it and/or
        modify it under the terms of the GNU General Public License as
        published by the Free Software Foundation, either version 3 of
        the License, or (at your option) any later
        version.<br><br><b>EScope</b> is distributed in the hope
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

    def click_display(self, val):
        self.apane.setDisplayStyle(val)

    def closeEvent(self,evt):
        QApplication.quit()

def main():
    print(f'This is EScope {VERSION}')
    os.chdir(os.path.expanduser("~/Documents"))
    if not os.path.exists("EScopeData"):
        os.mkdir("EScopeData")
    os.chdir("EScopeData")
    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()

    mw = MainWin(cfg)

    mw.displaystyle.setCurrentIndex(2)
    mw.displaystyle.hide() # on modern computer hardware, this control is not needed
    mw.show()
    app.exec_()
    

if __name__=='__main__':
    main()
