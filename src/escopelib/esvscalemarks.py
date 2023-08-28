# esvzeromarks.py

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
import esconfig
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
        poly.setPoint(k,xx[k],yy[k])
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
        f=p.font()
        f.setPixelSize(10)
        p.setFont(f)
        
        hp = self.height()
        wp = self.width()
        y0 = self.cfg.vert.ylim[0] + 0.
        y1 = self.cfg.vert.ylim[1]
        self.divp = hp/(y1-y0)

        if self.cfg.trig.enable:
            cc = self.cfg.colors[self.cfg.trig.source]
            pn.setColor(cc)
            pn.setWidth(0)
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

        pn.setWidth(2)
        p.setPen(pn)
        for k in range(self.cfg.MAXCHANNELS):
            if np.isnan(self.cfg.conn.hw[k]):
                self.yp[k] = np.nan
            else:
                pn.setColor(self.cfg.colors[k])
                p.setPen(pn)
                yp = hp * (1 - (self.yy[k]-y0)/(y1-y0))
                p.drawLine(5,yp+self.divp/2.,5,yp-self.divp/2.)
                self.yp[k]=yp
                if self.tracking==k:
                    scl = self.scl
                else:
                    scl = self.cfg.vert.unit_div[k]
                p.drawText(10, yp-10, 100, 20,
                           Qt.AlignVCenter,
                           esconfig.niceunit(scl * self.cfg.conn.scale[k],
                                             self.cfg.conn.units[k]))

    def wheelEvent(self,evt):
        k = self.wheeling
        if k==None:
            evt.ignore()
            return

        if k==ESV_TRIGLEVEL:
            delta=evt.delta()
            if delta!=0:
                y = self.cfg.trig.level_div + delta/120./2.
                if y<self.cfg.vert.ylim[0]:
                    y=self.cfg.vert.ylim[0]
                elif y>=self.cfg.vert.ylim[1]:
                    y=self.cfg.vert.ylim[1]
                if y!=self.cfg.trig.level_div:
                    self.cfg.trig.level_div = y
                    self.update()
                    print 'Trigger level changed to %.1f divisions' % y
                    self.trigChanged.emit()
        else:
            self.delta_accum = self.delta_accum + evt.delta()/120./2.
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
        if k==None:
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
            k = np.argmin(abs(self.yp-y))
            if abs(self.yp[k]-y)>self.divp:
                k=None
        self.tracking = k
        self.wheeling = k
        self.delta_accum = 0
        if k==ESV_TRIGLEVEL:
            self.tracky0 = y
            self.trackystart = self.yp_trig
            self.tracky = self.trackystart
        elif k!=None:
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
        elif self.tracking!=None:
            dscl = (evt.y()-self.tracky0) / self.divp
            self.scl = limscale(esconfig.scale125(self.scl0, -dscl))
            self.update()

    def mouseReleaseEvent(self,evt):
        k = self.tracking
        if k==None:
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
                print 'Trigger level changed to %.1f divisions' % y
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
    
