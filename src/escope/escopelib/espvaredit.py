# espvaredit.py - This file is part of EScope/ESpark
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


# espvaredit.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import numpy as np
from . import espconfig

class ESPVarEdit(QLineEdit):
    userChanged = pyqtSignal(str,int)
        
    def __init__(self, cfg, typname, k, varname, subname, parent=None):
        QLineEdit.__init__(self, parent)
        self.cfg = cfg
        self.typname = typname
        self.k = k
        self.varname = varname
        self.subname = subname
        self.reset()
        self.editingFinished.connect(self.foo)

    def reset(self):
        val = self.cfg.__dict__[self.typname][self.k] \
              .__dict__[self.varname].__dict__[self.subname]
        if self.varname[-2:]=='_s':
            if self.typname=='pulse' and val==0:
                self.setText('0 ms')
            else:
                self.setText(espconfig.niceunit(val, 's'))
        elif self.varname[-2:]=='_u':
            self.setText(espconfig.niceunit(val * self.cfg.conn.scale[self.k],
                                            self.cfg.conn.units[self.k]))
        else:
            self.setText('%i' % val)

    def foo(self):
        self.userChanged.emit(self.varname + "." + self.subname, int(self.k))

    def value(self):
        txt = str(self.text())
        if self.varname[-2:]=='_s':
            return espconfig.unniceunit(txt, 's')
        elif self.varname[-2:]=='_u':
            v = espconfig.unniceunit(txt, self.cfg.conn.units[self.k])
            return v / self.cfg.conn.scale[self.k]
        else:
            try:
                return float(txt)
            except:
                return np.nan
        
