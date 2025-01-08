# esvscalemarks.py - This file is part of EScope/ESpark
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


# esvzeromarks.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
from . import esconfig
import numpy as np

def limscale(scl):
    if scl<5e-3:
        return 5e-3
    if scl>10:
        return 10
    return scl

def mkpoly(xx,yy):
    poly = QPolygon(len(xx))
    for k in range(len(xx)):
        poly.setPoint(k, int(xx[k]), int(yy[k]))
    return poly

ESV_TRIGLEVEL = 1001

class ESVScaleMarks(QWidget):
    sclChanged = pyqtSignal(int)
    trigChanged = pyqtSignal()

    def __init__(self, cfg, parent=None):
        QWidget.__init__(self, parent)
        self.cfg = cfg
        self.yy = np.arange(self.cfg.MAXCHANNELS)*1.25
        self.yy = np.mean(self.yy) - self.yy
        self.yp = np.zeros(self.cfg.MAXCHANNELS) + np.nan
        self.divp = 0

        self.tracking = None
        self.wheeling = None

    def paintEvent(self, evt):
        p = QPainter(self)
        pn = p.pen()
        
        hp = self.height()
        wp = self.width()
        y0 = self.cfg.vert.ylim[0] + 0.
        y1 = self.cfg.vert.ylim[1]
        self.divp = hp/(y1-y0)

        if self.cfg.trig.enable:
            cc = esconfig.color(self.cfg, self.cfg.trig.source)
            pn.setColor(cc)
            pn.setWidth(2)
            p.setPen(pn)
            if self.cfg.trig.auto:
                p.setBrush(QColor("black"))
            else:
                p.setBrush(cc)
            if self.tracking==ESV_TRIGLEVEL:
                yp = self.tracky
            else:
                y=self.cfg.trig.level_div
                yp = hp * (1 - (y-y0)/(y1-y0))
            self.dyp_trig = wp/6.
            self.yp_trig = yp
            p.drawPolygon(mkpoly([0.,wp/8.,wp/4.],
                                 [yp,yp-self.cfg.trig.direction*wp/6.,yp]))

        pn.setWidth(4)
        pn.setCapStyle(Qt.FlatCap)
        p.setPen(pn)
        for k in range(self.cfg.MAXCHANNELS):
            if np.isnan(self.cfg.conn.hw[k]):
                self.yp[k] = np.nan
            else:
                pn.setColor(esconfig.color(self.cfg, k))
                p.setPen(pn)
                yp = hp * (1 - (self.yy[k]-y0)/(y1-y0))
                p.drawLine(5, int(yp+self.divp/2.), 5, int(yp-self.divp/2.))
                self.yp[k]=yp
                if self.tracking==k:
                    scl = self.scl
                else:
                    scl = self.cfg.vert.unit_div[k]
                p.drawText(0, int(yp-20), self.width() - 4, 40,
                           Qt.AlignVCenter | Qt.AlignRight,
                           esconfig.niceunit(scl * self.cfg.conn.scale[k],
                                             self.cfg.conn.units[k]))

    def wheelEvent(self,evt):
        k = self.wheeling
        if k is None:
            evt.ignore()
            return

        if k==ESV_TRIGLEVEL:
            delta=evt.angleDelta().y()
            if delta!=0:
                y = self.cfg.trig.level_div + delta/120./2.
                if y<self.cfg.vert.ylim[0]:
                    y=self.cfg.vert.ylim[0]
                elif y>=self.cfg.vert.ylim[1]:
                    y=self.cfg.vert.ylim[1]
                if y!=self.cfg.trig.level_div:
                    self.cfg.trig.level_div = y
                    self.update()
                    print(f'Trigger level changed to {y:.1f} divisions')
                    self.trigChanged.emit()
        else:
            self.delta_accum = self.delta_accum + evt.angleDelta().y()/120./2.
            scl = self.cfg.vert.unit_div[k]
            while self.delta_accum>=1:
                scl = esconfig.scale125(scl,1)
                self.delta_accum = self.delta_accum - 1
            while self.delta_accum<=-1:
                scl = esconfig.scale125(scl,-1)
                self.delta_accum = self.delta_accum + 1
            scl = limscale(scl)
            if scl!=self.cfg.vert.unit_div[k]:
                self.cfg.vert.unit_div[k] = scl
                self.update()
                #print 'Scale %i changed to %g %s' % (k,scl,cfg.conn.units[k])
                self.sclChanged.emit(k)

    def mouseDoubleClickEvent(self,evt):
        k = self.wheeling
        if k is None:
            return
        if k==ESV_TRIGLEVEL:
            if evt.button()==Qt.RightButton:
                self.cfg.trig.auto = not self.cfg.trig.auto
            else:
                self.cfg.trig.direction = -self.cfg.trig.direction
            self.update()
            self.trigChanged.emit()

    def mousePressEvent(self,evt):
        x=evt.x()
        y=evt.y()

        if self.cfg.trig.enable and abs(y-self.yp_trig)<self.dyp_trig:
            k = ESV_TRIGLEVEL
        else:        
            k = np.nanargmin((self.yp-y)**2)
            if abs(self.yp[k]-y) > self.divp:
                k=None
        self.tracking = k
        self.wheeling = k
        self.delta_accum = 0
        if k==ESV_TRIGLEVEL:
            self.tracky0 = y
            self.trackystart = self.yp_trig
            self.tracky = self.trackystart
        elif k is not None:
            self.tracky0 = y
            self.scl0 = self.cfg.vert.unit_div[k]
            self.scl = self.scl0

    def mouseMoveEvent(self,evt):
        if self.tracking==ESV_TRIGLEVEL:
            y=evt.y()
            self.tracky = self.trackystart + y-self.tracky0
            if self.tracky<0:
                self.tracky=0
            elif self.tracky>=self.height():
                self.tracky=self.height()-1
            self.update()
        elif self.tracking is not None:
            dscl = (evt.y()-self.tracky0) / self.divp
            self.scl = limscale(esconfig.scale125(self.scl0, -dscl))
            self.update()

    def mouseReleaseEvent(self,evt):
        k = self.tracking
        if k is None:
            return
        
        self.tracking = None

        if k==ESV_TRIGLEVEL:
            y=evt.y()
            y1p = self.trackystart + y-self.tracky0
            hp = self.height()+0.
            if y1p<0:
                y1p=0
            elif y1p>=hp:
                y1p=hp-1
            y0 = self.cfg.vert.ylim[0] + 0.
            y1 = self.cfg.vert.ylim[1]
            y = y0 + (y1-y0)*(1-y1p/hp)
            must_emit = y!=self.cfg.trig.level_div
            self.cfg.trig.level_div = y
            self.update()
            if must_emit:
                print(f'Trigger level changed to {y:.1f} divisions')
                self.trigChanged.emit()
        else:
            dscl = (evt.y()-self.tracky0) / self.divp
            self.scl = limscale(esconfig.scale125(self.scl0, -dscl))
            must_emit = self.scl!=self.cfg.vert.unit_div[k]
            self.cfg.vert.unit_div[k] = self.scl
            self.update()
            if must_emit:
                #s = esconfig.niceunit(self.scl, self.cfg.conn.units[k])
                #print 'Scale %i changed to %s' % (k,s)
                self.sclChanged.emit(k)
            
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()
    cfg.trig.enable = True
    win = ESVScaleMarks(cfg)
    p=win.palette()
    p.setColor(QPalette.Window,QColor("black"))
    win.setPalette(p)
    win.resize(50,200)
    win.show()
    app.exec_()
    
