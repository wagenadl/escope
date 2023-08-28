# esptypebox.py

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import espconfig

class ESPTypeBox(QComboBox):
    userChanged = pyqtSignal(str, int)
    
    def __init__(self, cfg, k, parent=None):
        QComboBox.__init__(self, parent)
        self.cfg = cfg
        self.k = k
        self.addItem('Off')
        self.addItem('Monophasic')
        self.addItem('Biphasic')
        self.addItem('Ramp')
        self.addItem('Sine')
        self.reset()
        self.activated.connect(self.foo)

    def reset(self):
        self.setCurrentIndex(self.cfg.pulse[self.k].type.value)
        
    def foo(self):
        self.userChanged.emit('type.base', int(self.k))
        
    def value(self):
        return espconfig.Pulsetype(self.currentIndex())
