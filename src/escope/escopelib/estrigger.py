# estrigger.py - This file is part of EScope/ESpark
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


# estrigger.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
from . import esconfig
import numpy as np

class MyRadio(QRadioButton):
    def hitButton(self, pos):
        return True

class ESTrigger(QGroupBox):
    cfgChanged = pyqtSignal()
    
    def __init__(self, cfg):
        super().__init__(title="Trigger")
        self.setWindowTitle("EScope: Trigger")
        self.cfg = cfg
        lay = QVBoxLayout(self)
        self.h_enable = QCheckBox(self)
        self.h_enable.setText("Trigger")
        lay.addWidget(self.h_enable)
        self.h_auto = QCheckBox(self)
        self.h_auto.setText("Auto")
        lay.addWidget(self.h_auto)

        def enable_slot():
            self.cfg.trig.enable = self.h_enable.isChecked()
            #print 'Enabled: ', self.cfg.trig.enable
            self.cfgChanged.emit()
        self.h_enable.toggled.connect(enable_slot)
        
        def auto_slot():
            self.cfg.trig.auto = self.h_auto.isChecked()
            #print 'Auto: ', self.cfg.trig.auto
            self.cfgChanged.emit()
        self.h_auto.toggled.connect(auto_slot)

        self.hh_chan = []
        for ch in range(self.cfg.MAXCHANNELS):
            h = MyRadio(self)
            h.setText('')
            #h.setFixedHeight(20)
            h.setAutoFillBackground(True)
            p = h.palette()
            p.setColor(QPalette.Button, esconfig.color(self.cfg, ch))
            h.setPalette(p)
            self.hh_chan.append(h)
            lay.addWidget(h)
            def mkSlot(ch):
                def rslot():
                    self.cfg.trig.source = ch
                    #print 'Selected: ', ch
                    self.cfgChanged.emit()
                return rslot
            h.clicked.connect(mkSlot(ch))
            
        lay.setSpacing(5)
        self.reconfig()

    def reconfig(self):
        self.h_enable.setChecked(self.cfg.trig.enable)
        self.h_auto.setChecked(self.cfg.trig.auto)
        for k in range(self.cfg.MAXCHANNELS):
            self.hh_chan[k].setChecked(self.cfg.trig.source == k)
            vis = self.cfg.conn.hw[k] is not None \
                and not np.isnan(self.cfg.conn.hw[k])
            self.hh_chan[k].setVisible(vis)
            if vis:
                c = int(self.cfg.conn.hw[k])
                name = self.cfg.hw.channels[c]
                self.hh_chan[k].setText(f"({name})")
       

    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()
    win = ESTrigger(cfg)
    win.show()
    app.exec_()
    
