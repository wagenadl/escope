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
