# estmarks.py - This file is part of EScope/ESpark
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


# estmarks.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
from . import esconfig
import numpy as np

def limscale(scl):
    if scl<100e-6:
        return 100e-6
    if scl>10.0:
        return 10.0
    return scl

def mkpoly(xx,yy):
    poly = QPolygon(len(xx))
    for k in range(len(xx)):
        poly.setPoint(k,int(xx[k]),int(yy[k]))
    return poly

EST_TIMESCALE = 1
EST_TRIGDELAY = 2

class ESTMarks(QWidget):
    timeChanged = pyqtSignal()
    trigChanged = pyqtSignal()
    trigEnabled = pyqtSignal()

    def __init__(self, cfg, parent=None):
        QWidget.__init__(self, parent)
        self.cfg = cfg
        self.xp_time = np.nan
        self.xp_trig = np.nan
        self.divp = 0

        self.tracking = None # None, or one of EST_TIMESCALE, EST_TRIGDELAY
        self.wheeling = None

    def paintEvent(self, evt):
        p = QPainter(self)
        pn = p.pen()
        f = QFont(*self.cfg.font)
        #f.setPointSize(7)
        p.setFont(f)
        
        hp = self.height()
        wp = self.width() + 0.
        x0 = self.cfg.hori.xlim[0] + 0.
        x1 = self.cfg.hori.xlim[1]
        self.divp = wp/(x1-x0)

        if self.tracking==EST_TRIGDELAY:
            xp = self.trackx
        else:
            xp = wp * (self.cfg.trig.delay_div-x0)/(x1-x0)
        sclh = hp/4
        pn.setWidth(2)
        pn.setColor(QColor("#dddddd"))
        p.setPen(pn)
        if self.cfg.trig.enable:
            p.setBrush(QColor("#dddddd"))
        else:
            p.setBrush(QColor("black"))
        p.drawPolygon(mkpoly([xp, xp+sclh, xp-sclh],
                             [hp-sclh*2,hp-1,hp-1]))
        p.drawLine(int(xp), 0, int(xp), int(hp-sclh*2))
        self.xp_trig = xp
        self.dxp_trig = sclh
            
        pn.setColor(QColor("white"))
        pn.setWidth(4)
        pn.setCapStyle(Qt.FlatCap)
        p.setPen(pn)
        xp = wp * (x1-.5-x0)/(x1-x0)
        p.drawLine(int(xp+self.divp/2.), 5, int(xp-self.divp/2.), 5)
        self.xp_time = xp
        if self.tracking==EST_TIMESCALE:
            scl = self.scl
        else:
            scl = self.cfg.hori.s_div
        p.drawText(int(xp)-50, 0, 100, self.height(),
                   Qt.AlignHCenter | Qt.AlignBottom,
                   esconfig.niceunit(scl,'s'))

    def wheelEvent(self,evt):
        k = self.wheeling
        if k is None:
            evt.ignore()
            return

        if k==EST_TIMESCALE:
            self.delta_accum = self.delta_accum + evt.angleDelta().y()/120./2.
            scl = self.cfg.hori.s_div
            
            while self.delta_accum>=1:
                scl = esconfig.scale125(scl,1)
                self.delta_accum = self.delta_accum - 1
            while self.delta_accum<=-1:
                scl = esconfig.scale125(scl,-1)
                self.delta_accum = self.delta_accum + 1
            scl = limscale(scl)

            if scl!=self.cfg.hori.s_div:
                self.cfg.hori.s_div = scl
                self.update()
                #print 'Time scale changed to %s/division' % \
                #      esconfig.niceunit(scl,'s')
                self.timeChanged.emit()
        elif k==EST_TRIGDELAY:
            delta = evt.delta()
            if delta!=0:
                t = self.cfg.trig.delay_div - delta/120./2.
                if t<self.cfg.hori.xlim[0]:
                    t = self.cfg.hori.xlim[0]
                elif t>self.cfg.hori.xlim[1]:
                    t = self.cfg.hori.xlim[1]
                if t!=self.cfg.trig.delay_div:
                    self.cfg.trig.delay_div = t
                    self.update()
                    print(f'Trigger delay changed to {t:.1f} divisions')
                    self.trigChanged.emit()

    def mousePressEvent(self,evt):
        x=evt.x()

        if self.xp_trig is not None and abs(self.xp_trig-x)<self.dxp_trig:
            k = EST_TRIGDELAY
        elif abs(self.xp_time-x)<self.divp/2:
            k = EST_TIMESCALE
        else:
            k = None

        self.tracking = k
        self.wheeling = k
        self.delta_accum = 0
        self.trackx0 = x

        if k==EST_TIMESCALE:
            self.scl0 = self.cfg.hori.s_div
            self.scl = self.scl0
        elif k==EST_TRIGDELAY:
            self.trackxstart = self.xp_trig
            self.trackx = self.trackxstart

    def mouseDoubleClickEvent(self, evt):
        k = self.wheeling
        if k==EST_TRIGDELAY:
            self.cfg.trig.enable = not self.cfg.trig.enable
            #print self.cfg.trig.enable
            self.trigEnabled.emit()
            self.update()

    def mouseMoveEvent(self,evt):
        if self.tracking==EST_TIMESCALE:
            dscl = (evt.x()-self.trackx0) / self.divp
            self.scl = limscale(esconfig.scale125(self.scl0, dscl))
            self.update()
        elif self.tracking==EST_TRIGDELAY:
            x=evt.x()
            self.trackx = self.trackxstart + x-self.trackx0
            if self.trackx<0:
                self.trackx = 0
            elif self.trackx>=self.width():
                self.trackx = self.width()-1
            self.update()

    def mouseReleaseEvent(self,evt):
        k = self.tracking
        if k is None:
            return
        
        self.tracking = None
        x=evt.x()
        if k==EST_TIMESCALE:
            dscl = (x-self.trackx0) / self.divp
            self.scl = limscale(esconfig.scale125(self.scl0, dscl))
            must_emit = self.scl!=self.cfg.hori.s_div
            self.cfg.hori.s_div = self.scl
            self.update()
            if must_emit:
                #print 'Scale changed to %g s/div' % self.scl
                self.timeChanged.emit()
        elif k==EST_TRIGDELAY:
            x1p = self.trackxstart + x-self.trackx0
            wp = self.width()+0.
            x0 = self.cfg.hori.xlim[0] + 0.
            x1 = self.cfg.hori.xlim[1]
            x = x0 + (x1-x0) * x1p/wp
            if x<self.cfg.hori.xlim[0]:
                x = self.cfg.hori.xlim[0]
            elif x>self.cfg.hori.xlim[1]:
                x = self.cfg.hori.xlim[1]
            must_emit = x!=self.cfg.trig.delay_div
            self.cfg.trig.delay_div = x
            self.update()
            if must_emit:
                print('Trigger delay changed to {x:.1f} divisions')
                self.trigChanged.emit()
 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()
    cfg.trig.enable = True
    win = ESTMarks(cfg)
    win.resize(500,30)
    p=win.palette()
    p.setColor(QPalette.Window,QColor("black"))
    win.setPalette(p)
    win.show()
    app.exec_()
    
