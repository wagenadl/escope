import numpy as np
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class ESPGraph(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure()
        self.axes = fig.add_axes([0.20,0.20,.78,.78])
        # self.axes = fig.add_subplot(111)
        # self.axes.hold(True)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding,
                           QSizePolicy.Expanding)
        self.setMinimumSize(100, 50)
        fig.set_facecolor('#eeeeee') # The Qt palette doesn't affect the fig.

    def setXLabel(self, s):
        self.axes.set_xlabel(s)

    def setYLabel(self, s):
        self.axes.set_ylabel(s)
        
    def cla(self):
        self.axes.cla()

    def plot(self,x,y, col=[0.,0.,1.]):
        return self.axes.plot(x,y, color=col)

    def autolim(self):
        self.axes.axis('tight')
        xx = self.axes.get_xlim()
        yy = self.axes.get_ylim()
        dx = (xx[1]-xx[0])/20
        dy = (yy[1]-yy[0])/20
        self.axes.set_xlim((xx[0]-dx,xx[1]+dx))
        self.axes.set_ylim((yy[0]-dy,yy[1]+dy))
        self.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = QWidget()
    lay = QHBoxLayout(win)
    fig = MyFig(win)
    lay.addWidget(fig)
    win.show()
    app.exec_()
