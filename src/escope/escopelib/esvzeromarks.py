# esvzeromarks.py - This file is part of EScope/ESpark
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

def mkpoly(xx,yy):
    poly = QPolygon(len(xx))
    for k in range(len(xx)):
        poly.setPoint(k,xx[k],yy[k])
    return poly

class ESVZeroMarks(QWidget):
    cfgChanged = pyqtSignal(int)

    def __init__(self, cfg, parent=None):
        QWidget.__init__(self, parent)
        self.cfg = cfg
        self.xp = np.zeros(self.cfg.MAXCHANNELS) + np.nan
        self.yp = np.zeros(self.cfg.MAXCHANNELS) + np.nan
        self.rp = 1
        self.tracking = None
        self.wheeling = None

    def paintEvent(self, evt):
        p = QPainter(self)
        hp = self.height()
        wp = self.width()
        hsclp = (0.9*wp)/(self.cfg.MAXCHANNELS+1)
        rsclp = hsclp
        self.rp = rsclp
        for k in range(self.cfg.MAXCHANNELS):
            if np.isnan(self.cfg.conn.hw[k]):
                self.xp[k] = np.nan
                self.yp[k] = np.nan
            else:
                p.setPen(esconfig.color(self.cfg, k))
                if self.cfg.vert.coupling[k]==2:
                    p.setBrush(QColor("black"))
                else:
                    p.setBrush(esconfig.color(self.cfg, k))

                xrp = hsclp*(.5+self.cfg.MAXCHANNELS-k)
                xlp = xrp - 2*rsclp
                self.xp[k] = (xrp+xlp)/2.

                if self.tracking==k:
                    yp = self.tracky
                else:
                    y = self.cfg.vert.offset_div[k]
                    y0 = self.cfg.vert.ylim[0] + 0.
                    y1 = self.cfg.vert.ylim[1]
                    yp = hp * (1 - (y-y0)/(y1-y0))

                if yp < 0:
                    # Up arrow
                    p.drawPolygon(mkpoly([xlp, xrp, (xlp+xrp)/2],
                                         [2.5*rsclp, 2.5*rsclp, 0]))
                    self.yp[k] = .75*rsclp
                elif yp >= hp:
                    # Down arrow
                    p.drawPolygon(mkpoly([xlp, xrp, (xlp+xrp)/2],
                                         [hp-2.5*rsclp-1, hp-2.5*rsclp-1, hp-1]))
                    self.yp[k] = hp-.75*rsclp
                else:
                    # Regular marker
                    p.drawEllipse(QPoint(int(xlp+xrp)//2, int(yp)),
                                  int(1.5*rsclp), int(1.5*rsclp))
                    p.drawLine(int(xrp), int(yp), int(wp), int(yp))
                    self.yp[k] = yp

    def wheelEvent(self,evt):
        if self.wheeling is None:
            evt.ignore()
            return

        delta=evt.angleDelta().y()
        k = self.wheeling
            
        if delta!=0:
            y = self.cfg.vert.offset_div[k] + delta/120./2.
            self.cfg.vert.offset_div[k] = y
            self.update()
            print(f'Offset {k} changed to {y:.1f} divisions')
            self.cfgChanged.emit(k)

    def mousePressEvent(self,evt):
        x = evt.x()
        y = evt.y()
        k = np.nanargmin((self.xp-x)**2+(self.yp-y)**2)
        if abs(self.yp[k]-y)>self.rp or self.xp[k]-x>self.rp:
            k = None
        self.tracking = k
        self.wheeling = k
        if k is not None:
            self.trackystart = self.yp[k]
            self.tracky0 = y
            self.tracky = self.trackystart

    def mouseMoveEvent(self,evt):
        if self.tracking is not None:
            y=evt.y()
            self.tracky = self.trackystart + y - self.tracky0
            self.update()

    def mouseReleaseEvent(self,evt):
        k = self.tracking
        if k is None:
            return
        
        self.tracking = None
        
        y=evt.y()
        y1p = self.trackystart + y - self.tracky0
        hp = self.height()+0.
        y0 = self.cfg.vert.ylim[0] + 0.
        y1 = self.cfg.vert.ylim[1]
        y = y0 + (y1-y0)*(1-y1p/hp)
        must_emit = y != self.cfg.vert.offset_div[k]
        self.cfg.vert.offset_div[k] = y
        self.update()
        if must_emit:
            print(f'Offset {k} changed to {y:.1f} divisions')
            self.cfgChanged.emit(k)


    def mouseDoubleClickEvent(self,evt):
        k = self.wheeling
        if k is None:
            return
        if self.cfg.vert.coupling[k]==1:
            self.cfg.vert.coupling[k]=2
        else:
            self.cfg.vert.coupling[k]=1
        self.update()
        self.cfgChanged.emit(k)
            
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()
    win = ESVZeroMarks(cfg)
    win.resize(50,200)
    win.show()
    app.exec_()
    
