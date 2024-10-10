# esptypebox.py - This file is part of EScope/ESpark
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


# esptypebox.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from . import espconfig

class ESPTypeBox(QComboBox):
    userChanged = pyqtSignal(str, int)
    
    def __init__(self, cfg, k, parent=None):
        QComboBox.__init__(self, parent)
        self.cfg = cfg
        self.k = k
        self.rebuild(False)

    def rebuild(self, digital=False):
        self.clear()
        vals = [espconfig.Pulsetype.OFF]
        if digital:
            vals.append(espconfig.Pulsetype.TTL)
        else:
            vals.append(espconfig.Pulsetype.MONOPHASIC)
            vals.append(espconfig.Pulsetype.BIPHASIC)
            vals.append(espconfig.Pulsetype.RAMP)
            vals.append(espconfig.Pulsetype.SINE)
        for v in vals:
            self.addItem(str(espconfig.Pulsetype(v)), v)
        self.reset()
        self.activated.connect(self.foo)

    def reset(self):
        k = self.findData(self.cfg.pulse[self.k].type.value)
        self.setCurrentIndex(k)
        
    def foo(self):
        self.userChanged.emit('type.base', int(self.k))
        
    def value(self):
        return espconfig.Pulsetype(self.currentData())
