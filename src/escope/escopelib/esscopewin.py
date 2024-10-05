from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import numpy as np
import sys

from . import esconfig

from numba import jit

@jit(nopython=True)
def trueblue(xx, ichn, stride, yy):
    X = xx.shape[0]
    Y = len(yy)//2
    if Y==0 or X==0:
        return
    i0 = 0
    for k in range(Y):
        i1 = (k+1)*X//Y
        ymin = xx[i0, ichn]
        ymax = ymin
        for n in range(i0+1, i1):
            x = xx[n,ichn]
            if x < ymin:
                ymin = xx[n, ichn]
            elif x>ymax:
                ymax = x
        yy[k] = ymin
        yy[2*Y-1-k] = ymax
        i0 = i1


def sample(xx, ichn, stride, yy):
    X = xx.shape[0]
    Y = len(yy)
    if Y==0 or X==0:
        return
    xi = np.array(np.floor(np.arange(Y+1)*X/Y),dtype=int)
    yy[:Y] = xx[xi[:-1],ichn]


@jit(nopython=True)
def limpoly1(yy, ymin, ymax):
    Y = len(yy)
    Y2 = len(yy)-1
    for k in range(Y):
        if yy[k]<=ymin:
            yy[k] = ymin
        elif yy[k]>=ymax:
            yy[k] = ymax


@jit(nopython=True)
def limpoly2(yy, ymin, ymax):
    Y = len(yy)/2
    Y2 = len(yy)-1
    for k in range(Y):
        if yy[k]<=ymin:
            yy[k] = ymin
            yy[Y2-k] = ymin
        elif yy[Y2-k]>=ymax:
            yy[k] = ymax
            yy[Y2-k] = ymax


def mkpoly(xx,yy,offset,scale, hp):
    #print 'mkpoly', offset, scale
    poly = QPolygon(len(xx))
    for k in range(len(xx)):
        poly.setPoint(k, int(xx[k]), int(offset+scale*yy[k]))
    return poly

class ESScopeWin(QWidget):
    sweepComplete = pyqtSignal()
    sweepStarted = pyqtSignal()
    
    def __init__(self,cfg,parent=None):
        """Constructor.

        A reference to the configuration is maintained throughout the
        lifetime of this widget. External agents can change the configuration,
        then tell us about it so we can update our graphics.
        """
        QWidget.__init__(self,parent)
        self.cfg = cfg
        self.dat = None
        self.dat_pre_s = 0
        self.dat_post_s = 0
        self.yy = None
        self.xx = None
        self.src = None
        self.cc = None
        self.traces = None
        self.write_idx = None
        #self.mutex = QMutex()
        self.dispStyle = 0
        # Display styles: 0=dots, 1=lines, 2=true blue
        self.quitting = False

    def setDisplayStyle(self, sty):
        self.dispStyle = sty
        self.xx = None
        self.yy = None
        self.update()

    def closeEvent(self, evt):
        if not self.quitting:
            self.quitting = True
            QApplication.quit()

    def paintEvent(self, evt):
        p = QPainter(self)
        pn = p.pen()

        # Draw grid lines
        pn.setStyle(Qt.DotLine)
        pn.setColor(QColor("#aaaaaa"))
        p.setPen(pn)
        x0 = self.cfg.hori.xlim[0]+0.
        x1 = self.cfg.hori.xlim[1]
        y0 = self.cfg.vert.ylim[0]+0.
        y1 = self.cfg.vert.ylim[1]
        wp = self.width()
        hp = self.height()
        for x in np.arange(x0,x1+1e-10):
            xp = wp*(x-x0)/(x1-x0)
            if xp>=wp:
                xp=wp-1
            p.drawLine(int(xp), 0, int(xp), int(hp))
        for y in np.arange(y0,y1+1e-10):
            yp = hp * (1 - (y-y0)/(y1-y0))
            if yp>=hp:
                yp=hp-1
            p.drawLine(0, int(yp), int(wp), int(yp))
        pn.setStyle(Qt.SolidLine)
        p.setPen(pn)
        yp = hp * (1 - (0.-y0)/(y1-y0))
        p.drawLine(0, int(yp), int(wp), int(yp))

        # Draw traces
        if self.write_idx is not None and self.write_idx>0 and self.dat is not None:
            nchan = self.dat.shape[1]
            w = self.width()
            sweep_s = self.cfg.hori.s_div * (self.cfg.hori.xlim[1] -
                                             self.cfg.hori.xlim[0])

            # Let's find out where the data should be plotted
            # We have data starting at self.dat_pre before the trigger marker.
            # What we want to display is:
            want_pre_s = self.cfg.hori.s_div * (self.cfg.trig.delay_div -
                                                self.cfg.hori.xlim[0])
            # Our data further more extends self.dat_post after the trigger.
            # What we want to display is:
            want_post_s = self.cfg.hori.s_div * (self.cfg.hori.xlim[1] -
                                                 self.cfg.trig.delay_div)
            if want_pre_s>self.dat_pre_s:
                # We don't have enough at the beginning.
                # Some part of the display will be left black.
                x0 = int(w * (want_pre_s-self.dat_pre_s)/sweep_s)
                i0 = 0
            else:
                x0 = 0
                i0 = int(self.cfg.hw.acqrate.value *
                         (self.dat_pre_s - want_pre_s))
            if want_post_s>self.dat_post_s:
                # We don't have enough at the end.
                x1 = int(w*(1-(want_post_s-self.dat_post_s)/sweep_s))
                i1 = self.dat.shape[0]
            else:
                x1 = w
                i1 = int(self.dat.shape[0] -
                         self.cfg.hw.acqrate.value *
                         (self.dat_post_s - want_post_s))

            if self.dispStyle==2:
                neededLength = 2*(x1-x0)
            else:
                neededLength = (x1-x0)
            if self.xx is None or (len(self.xx)>0 and self.xx[0]!=x0) \
                   or len(self.xx)!=2*(x1-x0):
                if self.dispStyle==2:
                    self.xx = np.hstack((np.arange(x0,x1),
                                         np.arange(x1-1,x0-1,-1)))
                else:
                    self.xx = np.arange(x0,x1)
            if self.yy is None:
                self.yy = [None] * nchan
            for k in range(nchan):
                if self.yy[k] is None or len(self.yy[k])!=len(self.xx):
                    self.yy[k] = np.zeros(self.xx.shape)
                if self.dispStyle==2:
                    trueblue(self.dat[i0:i1,:], k, nchan, self.yy[k])
                else:
                    sample(self.dat[i0:i1,:], k, nchan, self.yy[k])
        if self.yy is not None:
            for k in range(len(self.yy)):
                p.setBrush(self.cc[k])
                p.setPen(self.cc[k])
                trc = self.traces[k]
                scl = -hp/self.cfg.vert.unit_div[trc]/(y1-y0)
                if self.cfg.vert.coupling[trc]==2:
                    v0 = np.mean(self.yy[k])
                else:
                    v0 = 0
                off = hp*(y1-self.cfg.vert.offset_div[trc])/(y1-y0) - scl*v0
                if self.dispStyle==2:
                    limpoly2(self.yy[k], (hp-1-off)/scl, -off/scl)
                else:
                    limpoly1(self.yy[k], (hp-1-off)/scl, -off/scl)
                poly = mkpoly(self.xx, self.yy[k], off, scl, hp)
                if self.dispStyle==0:
                    # Dots
                    p.drawPoints(poly)
                elif self.dispStyle==1:
                    p.drawPolyline(poly)
                else:
                    # True blue
                    p.drawPolygon(poly)
        p.end()

    def resizeEvent(self, evt):
        self.yy = None
        self.xx = None
        self.update()

    def rebuild(self):
        self.xx = None
        self.yy = None
        self.cc = []
        self.traces = []
        for trc in range(len(self.cfg.conn.hw)):
            hw = self.cfg.conn.hw[trc]
            if ~np.isnan(hw):
                self.cc.append(esconfig.color(self.cfg, trc))
                self.traces.append(trc)

    def forceFeed(self, dat):
        self.startRun(None)
        n = dat.shape[0]
        self.dat[:n,:] = dat
        self.write_idx = n
        self.dat_pre_s = self.cfg.hori.s_div * (self.cfg.trig.delay_div -
                                                self.cfg.hori.xlim[0])
        self.dat_post_s = self.cfg.hori.s_div * (self.cfg.hori.xlim[1] -
                                                 self.cfg.trig.delay_div)
        
    def startRun(self, src):
        self.src = src
        nch = 0
        for a in self.cfg.conn.hw:
            if not np.isnan(a):
                nch += 1
        per_s = self.cfg.hori.s_div * (self.cfg.hori.xlim[1] -
                                       self.cfg.hori.xlim[0])
        self.dat = np.zeros((int(per_s*self.cfg.hw.acqrate.value), nch))
        self.write_idx = 0
        self.read_idx = 0
        if src:
            src.dataAvailable.connect(self.feedData)
            src.trigAvailable.connect(self.feedTrig)
        self.rebuild()

    def stopRun(self):
        src = None

    def feedTrig(self):
        self.read_idx = 0
        self.write_idx = 0
        #self.feedData() #?

    def sweepIsComplete(self):
        print("sweepiscomplete?", self.write_idx, self.dat.shape)
        return self.dat is not None and self.write_idx>=self.dat.shape[0]

    def feedData(self):
        #lock = QMutexLocker(self.mutex)
        print("feeddata")
        if self.sweepIsComplete():
            self.write_idx = 0
        if self.write_idx == 0:
            self.dat_pre_s = self.cfg.hori.s_div * (self.cfg.trig.delay_div -
                                                    self.cfg.hori.xlim[0])
            self.dat_post_s = self.cfg.hori.s_div * (self.cfg.hori.xlim[1] -
                                                     self.cfg.trig.delay_div)
                                                 
        now = self.src.getData(self.dat[self.write_idx:,:])
        print("now", now)
        if self.write_idx==0 and now > 0:
            self.sweepStarted.emit()
        # print 'feeddata: ', self.write_idx, now, self.dat.shape[0]
        self.write_idx += now
        #del lock
        
        if self.sweepIsComplete():
            self.update()
            self.sweepComplete.emit()
        elif self.cfg.hori.s_div>0.1:
            self.update()
        
    def newVertical(self, itrace):
        """Inform of changes in the vertical positioning of one trace.

        The actual changes must have been made to the configuration already.
        """
        self.update()

    def newHorizontal(self):
        """Inform of changes in horizontal positioning of all traces.

        The actual changes must have been made to the configuration already.
        """
        self.update()

    
if __name__ == '__main__':
    if True:
        xx = np.random.rand(1000,1)
        ymin = np.zeros(20)
        trueblue(xx,0,1,ymin)
        print(ymin)

    app = QApplication(sys.argv)
    cfg = esconfig.basicconfig()
    cfg.trig.enable = True
    win = ESScopeWin(cfg)
    p=win.palette()
    p.setColor(QPalette.Window,QColor("black"))
    win.setPalette(p)
    win.resize(600,400)
    win.show()
    app.exec_()
    
