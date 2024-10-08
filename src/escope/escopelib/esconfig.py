# esconfig.py - Basic configuration parameters for escope

from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import numpy as np
from . import esnidaq
import time

from .Struct import Struct

def datetimestr():
    return time.strftime("%Y%m%d-%H%M%S",time.localtime())

def scale125(uold, du):
    uold10 = np.log10(uold)
    uolddecade = np.floor(uold10)
    uoldminor = 10**(uold10-uolddecade)
    if uoldminor>=4.99:
        uoldsub=2./3
    elif uoldminor>=1.99:
        uoldsub=1./3
    else:
        uoldsub=0.
    uoldf = uolddecade + uoldsub
    unewf = np.round(3*uoldf + du)/3
    unewdecade = np.floor(unewf)
    unewsub = unewf - unewdecade
    vals=np.array([1, 2, 5])
    unewminor = vals[int(3*unewsub+.5)]
    unew = 10**unewdecade * unewminor
    return unew

   

def niceunit(num,uni):
    """Converts a number with a unit to nicer units

    str = NICEUNIT(number,unit) attaches the given unit to the number.
    For instance, NICEUNIT(0.23,'V') returns '230 mV'.
    """
    if num==0:
        return "0 " + uni
    
    sgn=np.sign(num)
    num=np.abs(num)
    prf='pnum kMG'
    prv=10**np.array([-12, -9, -6, -3, 0, 3, 6, 9, np.inf])
    if len(uni)>1:
        if uni[0] in prf:
            num = num * prv[prf.index(uni[0])]
            uni = uni[1:]
    for k in range(len(prf),0,-1):
        if num<prv[k]:
            if prf[k-1]!=' ':
                uni1 = prf[k-1] + uni
            else:
                uni1 = uni
            s = "%.5g" % (num/prv[k-1]) + ' ' + uni1
    if sgn<0:
        s='-' + s
    return s


def findadapters():
    lst=[('dummy',)]
    nidevs = esnidaq.deviceList()
    for dev in nidevs:
        lst.append(('nidaq',dev))
    return lst

def reasonable(xmin,xmax):
    x0 = np.floor(np.log10(xmin))
    x1 = np.ceil(np.log10(xmax+1))
    choices = np.array([xmin])
    for x in 10**np.arange(x0,x1):
        for y in np.array([1,2,5])*x:
            if y>=xmin and y<=xmax and y!=choices[-1]:
                choices = np.hstack((choices, y))
    if choices[-1]<xmax:
        choices = np.hstack((choices, xmax))
    return choices

def acqrates(ada):
    typ = ada[0]
    sr = Struct()
    sr.min = 5000
    sr.max = 20000
    if typ=='nidaq':
        # Get min and max from hardware?
        pass
    sr.values = reasonable(sr.min,sr.max)
    sr.value = sr.values[int(len(sr.values)/2)]
    return sr

def inputchannels(ada):
    typ = ada[0]
    if typ=='dummy':
        chs = []
        for k in range(8):
            chs.append(f'ai{k}')
    elif typ=='nidaq':
        dev = ada[1]
        chs = esnidaq.devAIChannels(dev)
    return chs

def confighardware(cfg):
    cfg.hw.acqrate = acqrates(cfg.hw.adapter)
    cfg.hw.channels = inputchannels(cfg.hw.adapter)
    N = min(2, len(cfg.hw.channels))

    cfg.conn.hw = np.zeros(cfg.MAXCHANNELS) + np.nan
    for n in range(N):
        cfg.conn.hw[n] = n
    cfg.conn.scale = np.ones(cfg.MAXCHANNELS)
    cfg.conn.units = ['V'] * cfg.MAXCHANNELS

    # The matlab version now check whether the Channels dialog was open,
    # and if so, reopened it. For us, that cannot be done here.

def datetime():
    t0 = time.localtime()
    dat = time.strftime('%Y%m%d',t0)
    tim = time.strftime('%H%M%S',t0)
    return (dat,tim)

_colors = {}
def color(cfg, k):
    cc = cfg.COLORS[k]
    if cc not in _colors:
        _colors[cc] = QColor(int(255*cc[0]), int(255*cc[1]), int(255*cc[2]))
    return _colors[cc]

def basicconfig():
    cfg = Struct()
    cfg.VERSION = "escope-3.2"

    cfg.MAXCHANNELS = 8
    cfg.COLORS = [ (1,1,0), (0,.8,1), (1,0,1), (.3,1,.3),
                   (1,0,0), (0,.6,0), (0,0,1), (.8,.5,0) ]
    cfg.FONTSIZE = 10
    f = QFont()
    cfg.font = [f.family(), cfg.FONTSIZE]

    cfg.hw = Struct()
    cfg.conn = Struct()
    cfg.hori = Struct()
    cfg.vert = Struct()
    cfg.trig = Struct()

    cfg.hw.adapters = findadapters()
    cfg.hw.adapter = cfg.hw.adapters[0]
    for ada in cfg.hw.adapters:
        if ada[0] != 'dummy':
            cfg.hw.adapter = ada
            break

    confighardware(cfg)

    cfg.hori.s_div = 0.010;
    cfg.hori.run = False
    cfg.hori.runstart = datetime()
    cfg.hori.sweepno = 0
    cfg.hori.xlim = (0, 10)
    
    cfg.vert.unit_div = np.ones(cfg.MAXCHANNELS)
    cfg.vert.offset_div = 3.5 - np.arange(cfg.MAXCHANNELS)
    cfg.vert.coupling = np.ones(cfg.MAXCHANNELS) # 0=off, 1=DC, 2=AC
    cfg.vert.ylim = (-5, 5)

    cfg.trig.enable = False
    cfg.trig.auto = False
    cfg.trig.count = np.inf
    cfg.trig.source = 0 # Channel #
    cfg.trig.level_div = 0
    cfg.trig.direction = 1 # 1=up, -1=down
    cfg.trig.delay_div = 5

    cfg.capt_enable = False
    
    return cfg
