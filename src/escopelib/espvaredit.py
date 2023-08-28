# espvaredit.py

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np
import espconfig

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
            return espconfig.unniceunit(txt, self.cfg.conn.units[self.k]) /  \
                   self.cfg.conn.scale[self.k]
        else:
            try:
                return float(txt)
            except:
                return np.nan
        
