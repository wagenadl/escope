# esconfig.py - This file is part of EScope/ESpark
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


# esconfig.py - Basic configuration parameters for escope

from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import numpy as np
from . import esnidaq
from . import espicodaq
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


_prefix = 'pnuµm kMG' # accept u and mu for micro, report mu
_prvalue = 10**np.array([-12, -9, -6, -6, -3, 0, 3, 6, 9, np.inf])

def suitableunit(num, uni):
    """Finds appropriate metric prefix for a number

    SUITABLEUNIT(value, unit) returns a version of UNIT with a
    suitable prefix for the VALUE.

    For instance, NICEUNIT(0.23, 'mV') returns '230 µV'.
    """

    if num == 0:
        return uni

    if len(uni) > 1:
        if uni[0] in _prefix:
            num = num * _prvalue[_prefix.index(uni[0])]
            uni = uni[1:]

    usepfx = ''
    for pfx, pfval in zip(_prefix, _prvalue):
        if abs(num) >= pfval:
            usepfx = pfx
    return (usepfx + uni).strip()
    

def asunit(num, uni, newunit):
    if num == 0:
        return num

    if len(uni) > 1:
        if uni[0] in _prefix:
            num = num * _prvalue[_prefix.index(uni[0])]
            uni = uni[1:]

    if len(newunit) > 1:
        if newunit[0] in _prefix:
            num = num / _prvalue[_prefix.index(newunit[0])]
            newunit = newunit[1:]

    if newunit != uni:
        raise ValueError("Mismatched units")
    return num

def decimalstosuit(num, example, digits=3):
    trail = int(digits - max(0, np.round(np.log10(example))))
    if trail <= 0:
        trail = 0
    fmt = f"%.{trail}f"
    return fmt % num

def niceunit(num, uni):
    """Converts a number with a unit to nicer units

    str = NICEUNIT(number,unit) attaches the given unit to the number.
    For instance, NICEUNIT(0.23, 'V') returns '230 mV'.
    """

    uni1 = suitableunit(num, uni)
    num = asunit(num, uni, uni1)
    s = ("%.5g" % num) + " " + uni1
    return s.replace("-", "−")


def niceunitmatching(num, eg, uni):
    uni1 = suitableunit(eg, uni)
    num = asunit(num, uni, uni1)
    eg = asunit(eg, uni, uni1)
    s = decimalstosuit(num, eg*10) + " " + uni1
    return s.replace("-", "−")


def findadapters():
    lst=[('dummy',)]
    nidevs = esnidaq.deviceList()
    for dev in nidevs:
        lst.append(('nidaq', dev))
    picodevs = espicodaq.deviceList()
    for dev in picodevs:
        lst.append(('picodaq', dev))
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
    sr.min = 1000
    sr.max = 200000
    # Get min and max from hardware?
    sr.values = reasonable(sr.min, sr.max)
    sr.value = sr.values[np.argmin((sr.values-10000)**2)]
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
    elif typ=='picodaq':
        dev = ada[1]
        chs = espicodaq.devAIChannels(dev)
    else:
        chs = []
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
    cfg.VERSION = "escope-3.3"

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
