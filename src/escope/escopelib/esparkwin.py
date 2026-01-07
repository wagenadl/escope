#!/usr/bin/python3

# espark.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import os
import re
import math
import pickle
import numpy as np
from . import espconfig
from .esphardware import ESPHardware
from .espchannels import ESPChannels
from .esptraingraph import ESPTrainGraph
from .esppulsegraph import ESPPulseGraph
from .espvaredit import ESPVarEdit
from .esptypebox import ESPTypeBox
from .ledlabel import LEDLabel
from . import espsinks
from . import serializer

VERSION = "4.1.0"

_PULSECOL=3
_TRAINCOL=2

class MainWin(QWidget):
    channelsChanged = pyqtSignal()
    runRequested = pyqtSignal()
    
    def __init__(self, cfg, reccfg=None):
        super().__init__()
        self.cfg = cfg
        self.reccfg = reccfg
        self.standalone = reccfg is None
        self.acqtask = None
        self.stopped = False
        self.ds = None
        self.h_hw = None
        self.h_chn = None

        self.label = [None] * self.cfg.MAXCHANNELS
        self.traingraph = [None] * self.cfg.MAXCHANNELS
        self.pulsegraph = [None] * self.cfg.MAXCHANNELS
        self.htr = [None] * self.cfg.MAXCHANNELS
        self.hpu = [None] * self.cfg.MAXCHANNELS
        self.frames = [None] * self.cfg.MAXCHANNELS
        self.olay = None
        self.scroll = None
        self.canvas = None

        if self.standalone:
            self.setWindowTitle("ESpark")
        else:
            self.setWindowTitle("Stimuli (EScope)")
        self.place()
        self.makeContents()
        self.stylize()
        self.olay.update()
        self.updaterecconfig(reccfg)
        QTimer.singleShot(1, lambda: self.resizeEvent())

    def markrecconfig(reccfg):
        self.reccfg = reccfg
        if self.h_hw:
            self.h_hw.reconfig(reccfg)


    def stylize(self):
        self.setStyleSheet("""
        QLineEdit:!enabled { background-color: #f8f8f8; }
        QFrame { background-color: #f8f8f8; }
        QWidget#canvas { background-color: #eeeeee; }
        QScrollArea { background-color: #eeeeee; }
        QScrollBar:vertical { border: 0px solid #888888;
          background: #eeeeee;
          width: 15px;
          margin: 0px 0px 0px 6px;
        }
        QScrollBar::sub-line:vertical { height: 0px; }
        QScrollBar::add-line:vertical { height: 0px; }
        QScrollBar::handle:vertical {
          border: 1px solid #888888;
          margin: 0px 0px 0px 0px;
          background: #cccccc; }
        """)
        
    def place(self):
        scr = QApplication.desktop()
        scrw = scr.screenGeometry().width()
        scrh = scr.screenGeometry().height()
        unit = QFontMetrics(self.font()).boundingRect("X").height()
        self.resize(35*unit, 25*unit)
        self.move(int(.6*scrw) - self.width()//2, int(.55*scrh) - self.height()//2)

    def makeButtons(self):
        butlay = QHBoxLayout()
        butlay.setContentsMargins(6, 6, 0, 0)
        butlay.setSpacing(10)
        
        hw = QPushButton()
        hw.setText("Hardware...")
        hw.clicked.connect(self.click_hardware)

        cn = QPushButton()
        cn.setText("Channels...")
        cn.clicked.connect(self.click_channels)
        cn.setToolTip("Configure which channels are used for output")

        ld = QPushButton()
        ld.setText("Load...")
        ld.clicked.connect(self.click_load)
        ld.setToolTip("Reload previously saved configuration")

        sv = QPushButton()
        sv.setText("Save...")
        sv.clicked.connect(self.click_save)
        sv.setToolTip("Save current configuration")

        ll = LEDLabel()
        ll.setToolTip("Bright indicates stimuli are currently being sent out")
        self.h_led = ll
        
        rn = QPushButton()
        rn.setText("Run")
        rn.clicked.connect(self.click_run)
        rn.setToolTip("Start stimulation sequence")
        self.h_run = rn

        sp = QPushButton()
        sp.setText("Stop")
        sp.clicked.connect(self.click_stop)
        sp.setToolTip("Abort stimulation sequence")
        self.h_stop = sp
        sp.hide()

        rp = QCheckBox()
        rp.setText("Repeat")
        rp.stateChanged.connect(self.click_rep)
        rp.setToolTip("If enabled, stimuli are repeated indefinitely")
        self.h_rep = rp

        if self.standalone:
            abt = QPushButton()
            abt.setText("About...")
            abt.clicked.connect(self.click_about)
        else:
            abt = None

        butlay.addWidget(ll)
        butlay.addWidget(rn)
        butlay.addWidget(sp)
        butlay.addSpacing(10)
        butlay.addWidget(rp)
        butlay.addStretch(1)
        butlay.addWidget(hw)
        butlay.addWidget(cn)
        #butlay.addStretch(1)
        fr = QFrame()
        fr.setFrameShape(QFrame.StyledPanel)
        fr.setFixedWidth(2)
        butlay.addWidget(fr)
        #butlay.addSpacing(20)
        butlay.addWidget(ld)
        butlay.addWidget(sv)
        #butlay.addSpacing(20)
        #butlay.addStretch(1)
        if self.standalone:
            fr = QFrame()
            fr.setFrameShape(QFrame.StyledPanel)
            fr.setFixedWidth(2)
            butlay.addWidget(fr)
            butlay.addWidget(abt)

        hei = 22
        for h in [hw, cn, ld, sv, rn, rp, abt]:
            if h:
                h.setFocusPolicy(Qt.NoFocus)
        return butlay

    def makeGraphs(self, k):
        grlay = QHBoxLayout()
        grlay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(chr(65+k))
        self.label[k] = lbl
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        f=lbl.font()
        f.setWeight(QFont.Bold)
        lbl.setFont(f)
        grlay.addWidget(lbl)
        self.pulsegraph[k] = ESPPulseGraph(self.cfg, k)
        grlay.addWidget(self.pulsegraph[k])
        self.traingraph[k] = ESPTrainGraph(self.cfg, k)
        grlay.addWidget(self.traingraph[k])
        return grlay

    def stylizeLabels(self, hh):
        for h in hh:
            f = h.font()
            f.setStyle(QFont.StyleItalic)
            h.setFont(f)
            h.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)

    def makeTrainLayout(self, k):
        trbutlay = QGridLayout()
        trbutlay.setContentsMargins(0, 0, 0, 0)
        trbutlay.setSpacing(6)
        def addMonoTrain(varname, lbl, y):
            hl = QLabel(lbl+':')
            trbutlay.addWidget(hl, y, 0)
            h = ESPVarEdit(self.cfg, 'train', k, varname, 'base')
            trbutlay.addWidget(h, y, 1)
            return {'label':hl, 'base':h}
        def addBiTrain(varname, lbl, y):
            hh = addMonoTrain(varname, lbl, y)
            h = ESPVarEdit(self.cfg, 'train', k, varname, 'delta')
            trbutlay.addWidget(h, y, _TRAINCOL)
            hh['delta'] = h
            return hh
        def addTriTrain(varname, lbl, y):
            hh = addBiTrain(varname, lbl, y)
            h = ESPVarEdit(self.cfg, 'train', k, varname, 'delti')
            trbutlay.addWidget(h, y, _PULSECOL)
            hh['delti']=h
            return hh

        self.htr[k] = {}
        self.htr[k]['ntrains'] = addMonoTrain('ntrains','# trains', 0)
        self.htr[k]['period_s'] = addBiTrain('period_s','Train period', 1)
        self.htr[k]['period_s']['label'].setToolTip("Period is measured start to start. This number is also used for the (end-to-start) interval between repeated runs.")
        self.htr[k]['npulses'] = addBiTrain('npulses','# pulses', 2)
        self.htr[k]['ipi_s'] = addTriTrain('ipi_s','Pulse period', 3)
        self.htr[k]['ipi_s']['label'].setToolTip("Period is measured start to start.")
        self.htr[k]['delay_s'] = addMonoTrain('delay_s','Delay', 4)
        if k==0 and False:
            self.htr[k]['delay_s']['base'].setVisible(False)
            self.htr[k]['delay_s']['label'].setText(' ')
        trnal = QLabel('Chg./train:')
        trbutlay.addWidget(trnal, 0, _TRAINCOL)
        trnil = QLabel('Chg./pulse:')
        trbutlay.addWidget(trnil, 2, _PULSECOL)
        self.stylizeLabels([trnal, trnil])
        return trbutlay

    def makePulseLayout(self, k):
        pubutlay = QGridLayout()
        pubutlay.setContentsMargins(0, 0, 0, 0)
        pubutlay.setSpacing(6)
        
        def addMonoPulse(varname, lbl, y):
            hl = QLabel(lbl+':',self)
            pubutlay.addWidget(hl,y,0)
            h = ESPVarEdit(self.cfg, 'pulse', k, varname, 'base')
            pubutlay.addWidget(h, y, 1)
            return {'label': hl, 'base': h}
        def addBiPulse(varname, lbl, y):
            hh=addMonoPulse(varname, lbl, y)
            h = ESPVarEdit(self.cfg, 'pulse', k, varname, 'delta')
            pubutlay.addWidget(h, y, _TRAINCOL)
            hh['delta'] = h
            return hh
        def addTriPulse(varname, lbl, y):
            hh = addBiPulse(varname, lbl, y)
            h = ESPVarEdit(self.cfg, 'pulse', k, varname, 'delti')
            pubutlay.addWidget(h, y, _PULSECOL)
            hh['delti'] = h
            return hh

        self.hpu[k] = {}
        putl = QLabel('Pulse type:')
        pubutlay.addWidget(putl, 0, 0)
        put = ESPTypeBox(self.cfg, k)
        pubutlay.addWidget(put,0,1)
        self.hpu[k]['type'] = {'label': putl, 'base': put}
        punal = QLabel('Chg./train:')
        pubutlay.addWidget(punal, 0, _TRAINCOL)
        punil = QLabel('Chg./pulse:')
        pubutlay.addWidget(punil, 0, _PULSECOL)
        self.hpu[k]['amp1_u'] = addTriPulse('amp1_u','Amplitude', 1)
        self.hpu[k]['dur1_s'] = addTriPulse('dur1_s','Duration', 2)
        self.hpu[k]['amp2_u'] = addTriPulse('amp2_u','2nd amp.', 3)
        self.hpu[k]['amp2_u']['label'].setToolTip("or vertical offset for sine")
        self.hpu[k]['dur2_s'] = addTriPulse('dur2_s','2nd dur.', 4)
        self.hpu[k]['dur2_s']['label'].setToolTip("or phase shift for sine")
        self.stylizeLabels([punal, punil])
        return pubutlay
    
    def makeFrame(self, k):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        vlay = QVBoxLayout(frame)
        vlay.setContentsMargins(9, 6, 9, 9)
        grlay = self.makeGraphs(k)
        vlay.addLayout(grlay)

        allbutlay = QHBoxLayout()
        allbutlay.setContentsMargins(18, 0, 18, 0)
        allbutlay.setSpacing(36)
        pubutlay = self.makePulseLayout(k)
        allbutlay.addLayout(pubutlay)
        trbutlay = self.makeTrainLayout(k)
        allbutlay.addLayout(trbutlay)
        vlay.addLayout(allbutlay)

        for ky in self.htr[k]:
            for n in ['base','delta','delti']:
                if n in self.htr[k][ky]:
                    self.htr[k][ky][n].userChanged.connect(self.newTrain)
        for ky in self.hpu[k]:
            for n in ['base','delta','delti']:
                if n in self.hpu[k][ky]:
                    self.hpu[k][ky][n].userChanged.connect(self.newPulse)
        return frame
        
    def makeContents(self):
        toplay = QHBoxLayout(self)
        toplay.setContentsMargins(0, 4, 10, 10)
        docks = QWidget()
        docklay = QVBoxLayout(docks)
        docklay.setContentsMargins(4, 20, 0, 0)
        self.makedocks(docklay)
        toplay.addWidget(docks)
        olay = QVBoxLayout()
        toplay.addLayout(olay)
        olay.setContentsMargins(0, 0, 0, 0)
        olay.setSpacing(10)
        butlay = self.makeButtons()
        olay.addLayout(butlay)
        self.olay = olay
        
        scroll = QScrollArea(self)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) # for debug
        scroll.setFrameShape(QFrame.NoFrame)
        self.scroll = scroll

        self.canvas = QWidget(objectName="canvas")
        slay = QVBoxLayout(self.canvas)
        slay.setContentsMargins(0,0,0,0) #(9, 6, 9, 6)
        slay.setSpacing(4)
        
        for k in range(self.cfg.MAXCHANNELS):
            frame = self.makeFrame(k)
            frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.frames[k] = frame
            slay.addWidget(frame)
        slay.addStretch(1)
            
        scroll.setWidget(self.canvas)
        olay.addWidget(scroll)

        for k in range(self.cfg.MAXCHANNELS):
            self.chnChanged(k)
            
    def trainButEnable(self, k):
        ntr = self.htr[k]['ntrains']['base'].value()
        npu = self.htr[k]['npulses']['base'].value()
        typ = self.hpu[k]['type']['base'].value()
        rep = self.h_rep.isChecked()
        typissine = typ.value == espconfig.Pulsetype.SINE
        
        self.htr[k]['period_s']['base'].setEnabled(ntr>1 or (rep and k==0))
        self.htr[k]['period_s']['delta'].setEnabled(ntr>2)
        self.htr[k]['npulses']['delta'].setEnabled(ntr>1)
        self.htr[k]['ipi_s']['base'].setEnabled(npu>1 and not typissine)
        self.htr[k]['ipi_s']['delta'].setEnabled(ntr>1 and npu>1 and not typissine)
        self.htr[k]['ipi_s']['delti'].setEnabled(npu>2 and not typissine)

    def pulseButEnable(self, k):
        ntr = self.htr[k]['ntrains']['base'].value()
        npu = self.htr[k]['npulses']['base'].value()
        typ = self.hpu[k]['type']['base'].value()
        may = {
            'amp1_u': typ.have1amp(),
            'dur1_s': typ.have1dur(),
            'amp2_u': typ.have2amp(),
            'dur2_s': typ.have2dur() }
        for va in may:
            self.hpu[k][va]['base'].setEnabled(may[va])
            self.hpu[k][va]['delta'].setEnabled(may[va] and ntr>1)
            self.hpu[k][va]['delti'].setEnabled(may[va] and npu>1)            

    def newTrain(self, s, k):
        s = str(s)
        (varname, subname) = s.split('.')
        h = self.htr[k][varname][subname]
        val = h.value()
        ok = True
        if np.isnan(val):
            ok = False
        else:
            if varname=='ntrains':
                val = int(val)
                if val<1:
                    ok = False
                else:
                    self.trainButEnable(k)
                    self.pulseButEnable(k)
            elif (varname=='tperiod_s' or varname=='ipi_s') \
                     and subname=='base':
                ok = val>0
            elif varname=='delay_s':
                ok = val>=0
            elif varname=='npulses':
                val = int(val)
                if subname=='base':
                    if val<1:
                        ok = False
                    else:
                        self.trainButEnable(k)                                
                        self.pulseButEnable(k)                                
        p = h.palette()
        p.setColor(QPalette.Normal, QPalette.Text,
                   QColor("black") if ok else QColor("red"))
        h.setPalette(p)
        if ok:
            if self.cfg.train[k].__dict__[varname].__dict__[subname]!=val:
                self.cfg.train[k].__dict__[varname].__dict__[subname] = val
                h.reset()
                self.rebuildGraphs(k)

    def newPulse(self, s, k, maydraw=True, forcedraw=False):
        s = str(s)
        drawn = False
        (varname, subname) = s.split('.')
        h = self.hpu[k][varname][subname]
        val = h.value()
        ok = True
        drawn = False
        if varname=='type':
            self.trainButEnable(k)
            self.pulseButEnable(k)
            curdat = h.currentData()
            if curdat is None:
                h.setCurrentIndex(0)
                curdat = h.currentData()
            if not(self.cfg.pulse[k].type.value == curdat):
                self.cfg.pulse[k].type.value = curdat
                if maydraw:
                    self.rebuildGraphs(k)
                    drawn = True
        else:
            if np.isnan(val):
                ok = False
            else:
                if varname=='dur1_s' and subname=='base':
                    ok = val>0
                elif varname=='dur2_s' and subname=='base':
                    ok = val>=0
            p = h.palette()
            p.setColor(QPalette.Normal, QPalette.Text,
                       QColor("black") if ok else QColor("red"))
            h.setPalette(p)
            if ok:
                if self.cfg.pulse[k].__dict__[varname].__dict__[subname]!=val:
                    self.cfg.pulse[k].__dict__[varname].__dict__[subname] = val
                    h.reset()
                    if maydraw:
                        self.rebuildGraphs(k)
                        drawn = True
        if forcedraw and not drawn:
            self.rebuildGraphs(k)

    def rebuildGraphs(self, k):
        self.traingraph[k].rebuild()
        self.pulsegraph[k].rebuild()

    def makedocks(self, docklay):
        self.h_hw = ESPHardware(self.cfg)
        self.h_hw.cfgChanged.connect(self.hwChanged)
        docklay.addWidget(self.h_hw)
        self.h_hw.hide()
        self.h_chn = ESPChannels(self.cfg)
        self.h_chn.cfgChanged.connect(self.chnChanged)
        docklay.addWidget(self.h_chn)
        self.h_chn.hide()
        docklay.addStretch(1)
        
        
    def click_hardware(self):
        self.h_hw.reconfig(self.reccfg)
        self.h_hw.setVisible(not self.h_hw.isVisible())
        QTimer.singleShot(1, lambda: self.resizeEvent())

    def hwChanged(self):
        # Possibly triggered externally if not standalone
        for k in range(self.cfg.MAXCHANNELS):
            self.chnChanged(k)
                        
    def click_channels(self):
        self.h_chn.reconfig()
        self.h_chn.setVisible(not self.h_chn.isVisible())
        QTimer.singleShot(1, lambda: self.resizeEvent())

    def chnChanged(self, k):
        x = self.cfg.conn.hw[k]
        got = False
        if x is None:
            self.frames[k].hide()
        else:
            self.frames[k].show()
            name = self.cfg.hw.channels[x]
            self.label[k].setText(name)
            isana = name.lower().startswith("a")
            self.hpu[k]['type']['base'].rebuild(not isana)            
            for a in ['amp1_u', 'amp2_u']:
                for b in ['base', 'delta', 'delti']:
                    s = str(self.hpu[k][a][b].text())
                    if len(s):
                        oldbase = s[-1] # without prefix
                        newscl = self.cfg.conn.scale[k]
                        newuni = self.cfg.conn.units[k]
                        newbase = newuni[-1] # without prefix
                        if newbase == 'A' and oldbase == 'V':
                            factor = 1e-6
                        elif newbase == 'V' and oldbase == 'A':
                            factor = 1e6
                        else:
                            factor = 1
                        max_unit = espconfig.niceunit(10*newscl, newuni)
                        max_base = espconfig.unniceunit(max_unit, newbase)
                        val = espconfig.unniceunit(s, oldbase)
                        val *= factor
                        val = math.copysign(min(abs(val), max_base), val)
                        s = espconfig.niceunit(val, newbase)
                        self.hpu[k][a][b].setText(s)
                        self.newPulse(a+'.'+b, k, maydraw=False)
            self.newPulse('amp1_u.base', k, forcedraw=True)
            self.trainButEnable(k)
            self.pulseButEnable(k)
            self.newPulse('type.base',k,forcedraw=True) # Force redraw
            #self.rebuildGraphs(k)
        self.canvas.resize(QSize(self.canvas.width(),
                                 self.canvas.sizeHint().height()))
        self.resizeEvent()
        if not self.standalone:
            self.channelsChanged.emit()

    def resizeEvent(self, e=None):
        w = self.scroll.viewport().width()
        self.canvas.resize(w, self.canvas.height())

    def click_run(self):
        if self.standalone:
            self.startRun()
        else:
            self.runRequested.emit()


    def click_stop(self):
        self.stopRun()

    def click_rep(self, on):
        for k in range(self.cfg.MAXCHANNELS):
            self.trainButEnable(k)

    def setAcqTask(self, acqtask):
        self.acqtask = acqtask

    def startRun(self):
        self.h_run.hide()
        self.h_stop.show()
        self.h_led.turnOn()
        if self.ds:
            return # already running
        self.ds = espsinks.makeDataSink(self.cfg, self.reccfg)
        self.ds.runComplete.connect(self.doneRun)
        self.ds.reconfig()
        self.ds.join(self.acqtask)
        self.stopped = False
        self.ds.run()
        #print '  startRun ->', self, self.ds

    def stopRun(self):
        self.stopped = True
        self.h_run.show()
        self.h_stop.hide()
        self.h_led.turnOff()
        if self.ds:
            self.ds.stop()
            self.ds = None

    def doneRun(self):
        self.h_led.turnOff()
        rep = self.h_rep.isChecked()
        self.ds = None
        if rep:
            QTimer.singleShot(int(self.cfg.train[0].period_s.base*1000), lambda: self.repeatRun())
        else:
            self.h_run.show()
            self.h_stop.hide()

    def repeatRun(self):
        print("timerevent", self.h_rep.isChecked(), self.stopped)
        if self.h_rep.isChecked() and not self.stopped:
            self.startRun()
        else:
            self.h_run.show()
            self.h_stop.hide()

    def click_about(self):
        abt = QMessageBox()
        txt = f"""<b>ESpark</b> v. {VERSION}<br>

        (C) 2010, 2023, 2024 Daniel A. Wagenaar<br><br>

        <b>ESpark</b> is an electronic function generator.  More
        information, including a user manual, is available at <a
        href="https://github.com/wagenadl/escope">github</a> and <a
        href="https://escope.readthedocs.org">readthedocs</a>.<br><br>

        <b>ESpark</b> is free software: you can redistribute it and/or
        modify it under the terms of the GNU General Public License as
        published by the Free Software Foundation, either version 3 of
        the License, or (at your option) any later
        version.<br><br>

        <b>ESpark</b> is distributed in the hope
        that it will be useful, but WITHOUT ANY WARRANTY; without even
        the implied warranty of MERCHANTABILITY or FITNESS FOR A
        PARTICULAR PURPOSE. See the GNU General Public License for
        more details.<br><br>You should have received a copy of the GNU
        General Public License along with this program. If not, see <a
        href="http://www.gnu.org/licenses/gpl-3.0.en.html">www.gnu.org/licenses/gpl-3.0.en.html</a>.
        
        """
        abt.setText(txt)
        abt.setWindowTitle("About ESpark")
        abt.exec_()

    def click_save(self):
        name = QFileDialog.getSaveFileName(self,
                                           "Save Configuration",
                                           os.getcwd(),
                                           "ESpark files (*.espark)")
        name = name[0]
        if not name:
            return
        if not name.endswith('.espark'):
            name += '.espark'
        with open(name, "wt") as fd:
            serializer.dump(self.cfg, fd) # fd.write(repr(self.cfg))

    def click_load(self):
        name = QFileDialog.getOpenFileName(self,
                                           "Load Configuration",
                                           os.getcwd(),
                                           "ESpark files (*.espark)")
        name = name[0]
        if not name:
            return

        with open(name, "rt") as fd:
            cfg = serializer.load(fd)
        if not self.setConfig(cfg):
            QMessageBox.warning(self, "EScope",
                                """Stimulus configuration is not
                                compatible with connected hardware""")
        #    return 
        #for k in range(self.cfg.MAXCHANNELS):
        #    for a in self.htr[k]:
        #        for b in self.htr[k][a]:
        #            if b!='label':
        #                self.htr[k][a][b].reset()
        #    for a in self.hpu[k]:
        #        for b in self.hpu[k][a]:
        #            if b!='label':
        #                self.hpu[k][a][b].reset()
        #    self.trainButEnable(k)
        #    self.pulseButEnable(k)
        #    self.newPulse('amp1_u.base', k, forcedraw=True)

    def closeEvent(self,evt):
        if self.standalone:
            QApplication.quit()


    def setConfig(self, cfg):
        if cfg.hw.adapter not in self.cfg.hw.adapters:
            # Cannot load config for adapter that is not available
            return False
        for k in self.cfg.__dict__:
            self.cfg.__dict__[k] = cfg.__dict__[k]
        self.updaterecconfig(self.reccfg)
        if self.h_hw:
            self.h_hw.reconfig(self.reccfg)
        self.hwChanged()
        if self.h_chn:
            self.h_chn.reconfig()
        for k in range(self.cfg.MAXCHANNELS):
            self.chnChanged(k)
            

    def updaterecconfig(self, reccfg):
        self.reccfg = reccfg
        if reccfg is None:
            return
        if reccfg.hw.adapter == self.cfg.hw.adapter \
               and reccfg.hw.adapter[0] == 'picodaq':
            self.cfg.hw.genrate = reccfg.hw.acqrate
        if self.h_hw:
            self.h_hw.reconfig(reccfg)
        self.hwChanged()
