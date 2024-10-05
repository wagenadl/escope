import numpy as np
import sys
from numba import jit
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

@jit
def trueblue(xx, yy):
    '''Find min and max in bins

    ymin and ymax are output arrays; they must be the same size'''
    X = len(xx)
    Y = len(yy)//2
    ix0 = 0
    if X:
        mn = mx = xx[0]
    else:
        mn = mx = 0
    for i in range(Y):
        ix1 = int((i+1)*X/Y)
        if ix1 > ix0:
            mn = mx = xx[ix0]
        ix0 += 1
        while ix0 < ix1:
            x = xx[ix0]
            if x<mn:
                mn = x
            elif x>mx:
                mx = x
            ix0 += 1
        yy[i] = mn
        yy[2*Y-1-i] = mx
        
def mkpoly(xx,yy,offset,scale):
    poly = QPolygon(len(xx))
    for k in range(len(xx)):
        poly.setPoint(k,xx[k],scale*(yy[k]+offset))
    return poly


class ESPGraph(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setSizePolicy(QSizePolicy.Expanding,
                           QSizePolicy.Expanding)
        self.cla()

    def setXLabel(self, s):
        self.tlabel = s
        self.update()

    def setYLabel(self, s):
        self.vlabel = s
        self.update()
        
    def cla(self):
        self.tdat = []
        self.vdat = []
        self.cols = []
        self.partcol = []
        self.yy = None
        self.xx = None
        self.xlabel = ''
        self.ylabel = ''
        self.tlim=[0, 1]
        self.vlim=[0, 1]
        self.update()

    def plot(self,x,y, col=[0,0,1]):
        self.tdat.append(x)
        self.vdat.append(y)
        self.cols.append(QColor(int(col[0]*255),
                                int(col[1]*255),
                                int(col[2]*255)))
        self.partcol.append([])

    def colorify(self, x0, x1, col=[0.,0.,1.]):
        self.partcol[-1].append((x0,x1,QColor(int(col[0]*255),
                                              int(col[1]*255),
                                              int(col[2]*255))))

    def autolim(self):
        t0 = np.inf
        t1 = -np.inf
        v0 = np.inf
        v1 = -np.inf
        N = len(self.tdat)
        for k in range(N):
            t0 = min(t0, self.tdat[k][0])
            t1 = max(t1, self.tdat[k][-1])
            v0 = min(v0, np.min(self.vdat[k]))
            v1 = max(v1, np.max(self.vdat[k]))
        if t0>t1:
            t0=0
            t1=1
        if v0>v1:
            v0=0
            v1=1
        dt = (t1-t0)/20.0
        dv = (v1-v0)/20.0
        self.tlim = [t0-dt, t1+dt]
        self.vlim = [v0-dv, v1+dv]
        self.update()

    def resizeEvent(self, evt):
        self.xx=None
        self.yy=None
        self.update()

    def calcwp(self):
        W = self.width()
        return max(W-30,10)

    def calchp(self):
        H = self.height()
        return max(H-20,10)

    def t2x(self, t):
        wp = self.calcwp()
        return wp*(t-self.tlim[0])/(self.tlim[1]-self.tlim[0])

    def v2y(self, v):
        hp = self.calchp()
        return hp*(self.vlim[1]-v)/(self.vlim[1]-self.vlim[0])

    def paintEvent(self, evt):
        p = QPainter(self)
        pn = p.pen()
        pn.setWidthF(1)
        #pn.setStyle(Qt.NoPen)
        N = len(self.tdat)
        t0 = self.tlim[0]
        t1 = self.tlim[1]
        v0 = self.vlim[0]
        v1 = self.vlim[1]
        if self.xx is None or len(self.xx)!=N:
            self.xx = [None] * N
        if self.yy is None or len(self.yy)!=N:
            self.yy = [None] * N
        for k in range(N):
            t0k = self.tdat[k][0]
            dtk = self.tdat[k][1] - self.tdat[k][0]
            t1k = self.tdat[k][-1]+dtk
            x0k = int(self.t2x(t0k))
            x1k = int(self.t2x(t1k))
            if self.xx[k] is None:
                self.xx[k] = np.hstack((np.arange(x0k,x1k),
                                        np.arange(x1k-1,x0k-1,-1)))
            L = len(self.xx[k])//2
            if self.yy[k] is None:
                self.yy[k] = np.zeros(self.xx[k].shape)
                trueblue(self.vdat[k], self.yy[k])
                for i in range(1,L):
                    if self.yy[k][i]>self.yy[k][2*L-i]:
                        self.yy[k][i]=self.yy[k][2*L-i]
                    if self.yy[k][2*L-1-i]<self.yy[k][i-1]:
                        self.yy[k][2*L-1-i]=self.yy[k][i-1]
            pn.setColor(self.cols[k])
            p.setPen(pn)
            p.setBrush(self.cols[k])
            xx = self.xx[k][:L]
            yl = self.v2y(self.yy[k])
            yh = self.v2y(self.yy[k][len(xx):])
            for i in range(len(xx)):
                p.drawLine(QLineF(xx[i],yl[i],xx[i],yh[L-1-i]))
            for cc in self.partcol[k]:
                x0c = int(self.t2x(cc[0]))
                x1c = int(self.t2x(cc[1]))
                print('colorify', cc[0], cc[1], t0, t1, x0c,x1c)
                if x0c<x0k:
                    x0c=x0k
                elif x0c>x1k:
                    x0c=x1k
                if x1c<x0c:
                    x1c=x0c
                elif x1c>x1k:
                    x1c=x1k
                pn.setColor(cc[2])
                p.setPen(pn)
                p.setBrush(cc[2])
                print('colorify ->', x0k, x1k, x0c, x1c)
                x0c -= x0k
                x1c -= x0k
                xx = self.xx[k][x0c:x1c]
                L = len(xx)
                yl = self.v2y(self.yy[k][x0c:x1c])
                yh = self.v2y(self.yy[k][2*L-x1c:2*L-x0c])
                print(L, len(yl), len(yh), len(self.xx[k]), len(self.yy[k]))
                for i in range(L):
                    p.drawLine(QLineF(xx[i],yl[i], xx[i],yh[L-1-i]))
               
