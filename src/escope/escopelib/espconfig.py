# espconfig.py - This file is part of EScope/ESpark
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


# espconfig.py - Basic configuration parameters for espark

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import numpy as np
from . import esnidaq
from . import espicodaq
import time

from .Struct import Struct

_MAXCHANNELS = 4

class Monovalue:
    def __init__(self, base=0):
        self.base = base+0.0
    def __repr__(self):
        return f'Monovalue(base={self.base})'

class Bivalue:
    def __init__(self, base=0, delta=0):
        self.base = base+0.0
        self.delta = delta+0.0
    def __repr__(self):
        return f'Bivalue(base={self.base}, delta={self.delta})'

class Trivalue:
    def __init__(self, base=0, delta=0, delti=0):
        self.base = base+0.0
        self.delta = delta+0.0
        self.delti = delti+0.0
    def __repr__(self):
        return f'Trivalue(base={self.base}, delta={self.delta}, delti={self.delti})'

class Pulsetype:
    OFF = 0
    MONOPHASIC = 1
    BIPHASIC = 2
    RAMP = 3
    SINE = 4
    TTL = 5
    
    def __init__(self, val=OFF):
        self.value = val
        
    def __str__(self):
        if self.value==self.OFF:
            return 'Off'
        elif self.value==self.MONOPHASIC:
            return 'Monophasic'
        elif self.value==self.BIPHASIC:
            return 'Biphasic'
        elif self.value==self.RAMP:
            return 'Ramp'
        elif self.value==self.SINE:
            return 'Sine'
        elif self.value==self.TTL:
            return 'TTL'
        else:
            return f"{self.value}"
    def __repr__(self):
        return f"Pulsetype(Pulsetype.{str(self).upper()})"
    def have1dur(self):
        return self.value != self.OFF
    def have1amp(self):
        return self.value in [ self.MONOPHASIC, self.BIPHASIC, self.RAMP, self.SINE]
    def have2dur(self):
        return self.value in [ self.BIPHASIC, self.SINE ]
    def have2durUSE(self):
        return self.value in [ self.BIPHASIC ]
    def have2amp(self):
        return self.value in [self.BIPHASIC, self.RAMP, self.SINE ]
        

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
    unewminor = vals[np.round(3*unewsub)]
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

def scaleunit(uni, fac):
    """Scales a unit by several factors of 1000

    For instance, uni = SCALEUNIT('mV',0.001) returns 'uV'."""

    prf = 'pnum kMG'
    prv=10.**np.array([-12, -9, -6, -3, 0, 3, 6, 9, np.inf])
    mul=1;
    uni1 = uni
    if len(uni)>1:
        if uni[0] in prf:
            mul=prv[prf.index(uni[0])]
            uni=uni[1:]
    mul*=fac
    for k in range(len(prf),0,-1):
        if mul<prv[k]:
            if prf[k-1]!=' ':
                uni1 = prf[k-1] + uni
            else:
                uni1 = uni
    return uni1    

def unniceunit(s, uni):
    """Performs the opposite conversion of NICEUNIT

    num = UNNICEUNIT(string,unit) picks off the unit from the end of STRING
    and converts the result to the given UNIT.
    For instance, UNNICEUNIT('2.3 mV','uV') return 2300.
    If the conversion fails (e.g., because of incompatible units), the 
    result is NaN. However, '0' is always acceptable. """
    
    prf = 'pnum kMG'
    prv = 10.**np.array([-12, -9, -6, -3, 0, 3, 6, 9, np.inf])
    mul = 1;
    if len(uni) > 1:
        if uni[0] in prf:
            mul = prv[prf.index(uni[0])]
            uni = uni[1:]

    try:
        barenum = float(s)
        if barenum == 0:
            return 0
    except ValueError:
        pass
            
    if len(uni) > 0:
        if s[-len(uni):] != uni:
            return np.nan
        s = s[:-len(uni)]
    if s=='':
        return np.nan
    if s[-1] in prf:
        mul=mul/prv[prf.index(s[-1])]
        s = s[:-1]
    try:
        return float(s) / mul
    except ValueError:
        return np.nan
       

def findadapters():
    lst=[('dummy',)]
    nidevs = esnidaq.deviceList()
    for dev in nidevs:
        lst.append(('nidaq',dev))
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

def genrates(ada):
    typ = ada[0]
    sr = Struct()
    sr.min = 1000
    sr.max = 200000
    # Get min and max from hardware?
    sr.values = reasonable(sr.min, sr.max)
    sr.value = sr.values[np.argmin((sr.values-10000)**2)]
    return sr

def outputchannels(ada):
    typ = ada[0]
    if typ=='dummy':
        chs = []
        for k in range(2):
            chs.append(f'ao{k}')
        for k in range(2):
            chs.append(f'P1.{k}')
            
    elif typ=='nidaq':
        dev = ada[1]
        chs = esnidaq.devAOChannels(dev)
        chs += esnidaq.devDOChannels(dev)
    elif typ=='picodaq':
        dev = ada[1]
        chs = espicodaq.devAOChannels(dev)
        chs += espicodaq.devDOChannels(dev)
    return chs

def confighardware(cfg):
    cfg.hw.genrate = genrates(cfg.hw.adapter)
    cfg.hw.channels = outputchannels(cfg.hw.adapter)
    N = min(2, len(cfg.hw.channels))

    cfg.conn.hw = [None for k in range(cfg.MAXCHANNELS)]
    for n in range(N):
        cfg.conn.hw[n] = n
    cfg.conn.scale = np.ones(cfg.MAXCHANNELS)
    cfg.conn.units = ['V'] * cfg.MAXCHANNELS

def datetime():
    t0 = time.localtime()
    dat = time.strftime('%Y%m%d',t0)
    tim = time.strftime('%H%M%S',t0)
    return (dat,tim)
    
def basicconfig():
    cfg = Struct()
    cfg.VERSION = "espark-3"
    cfg.MAXCHANNELS = _MAXCHANNELS
    cfg.FONTSIZE = 10
    f = QFont()
    cfg.font = [f.family(), cfg.FONTSIZE]

    cfg.hw = Struct()
    cfg.conn = Struct()
    cfg.train = [None] * cfg.MAXCHANNELS
    cfg.pulse = [None] * cfg.MAXCHANNELS

    cfg.hw.adapters = findadapters()
    cfg.hw.adapter = cfg.hw.adapters[0]
    for ada in cfg.hw.adapters:
        if ada[0] != 'dummy':
            cfg.hw.adapter = ada
            break

    confighardware(cfg)

    for k in range(cfg.MAXCHANNELS):
        cfg.train[k] = Struct()
        cfg.train[k].ntrains = Monovalue(1)
        cfg.train[k].period_s = Bivalue(1)
        cfg.train[k].npulses = Bivalue(1)
        cfg.train[k].ipi_s = Trivalue(0.1)
        cfg.train[k].delay_s = Monovalue(0.0) #  if k==0 else 0.0)
    
    for k in range(cfg.MAXCHANNELS):
        cfg.pulse[k] = Struct()
        cfg.pulse[k].type = Pulsetype(Pulsetype.MONOPHASIC if k==0
                                 else Pulsetype.OFF)
        cfg.pulse[k].amp1_u = Trivalue(1)
        cfg.pulse[k].amp2_u = Trivalue(-1)
        cfg.pulse[k].dur1_s = Trivalue(0.010)
        cfg.pulse[k].dur2_s = Trivalue(0.010)

    return cfg

def mktiming(cfg, k):
    fs_hz = cfg.hw.genrate.value

    nexttrainstart_s = cfg.train[k].delay_s.base
    thisend_s = 0
    maxend_s = 0
    ntr = cfg.train[k].ntrains.base
    Npu = cfg.train[k].npulses.base
    if cfg.train[k].npulses.delta>0:
        Npu += cfg.train[k].npulses.delta * (ntr-1)
    ntr = int(ntr)
    Npu = int(Npu)
    tstart_s=np.zeros((ntr, Npu))
    tend_s=np.zeros((ntr, Npu))
    
    if ntr==0 or Npu==0 or cfg.pulse[k].type.value==Pulsetype.OFF:
        return (int(maxend_s*fs_hz), tstart_s*fs_hz, tend_s*fs_hz)

    if cfg.pulse[k].type.value==Pulsetype.SINE:
        ipi_s = cfg.pulse[k].dur1_s
    else:
        ipi_s = cfg.train[k].ipi_s
    
    for itr in range(int(cfg.train[k].ntrains.base)):
        nextstart_s = nexttrainstart_s
        for ipu in range(int(cfg.train[k].npulses.base + 
                             itr*cfg.train[k].npulses.delta)):
            tstart_s[itr,ipu] = nextstart_s
            thisend_s = nextstart_s + cfg.pulse[k].dur1_s.base + \
                        itr*cfg.pulse[k].dur1_s.delta + \
                        ipu*cfg.pulse[k].dur1_s.delti
            if cfg.pulse[k].type.value==Pulsetype.BIPHASIC:
                thisend_s += cfg.pulse[k].dur2_s.base + \
                             itr*cfg.pulse[k].dur2_s.delta + \
                             ipu*cfg.pulse[k].dur2_s.delti
            tend_s[itr,ipu] = thisend_s
            nextstart_s += ipi_s.base + itr*ipi_s.delta + ipu*ipi_s.delti
            if thisend_s>maxend_s:
                maxend_s = thisend_s
        nexttrainstart_s += cfg.train[k].period_s.base + \
                            itr*cfg.train[k].period_s.delta
    return (int(maxend_s*fs_hz), tstart_s*fs_hz, tend_s*fs_hz)

def filltrain(cfg, k, timing, vvv):
    tau = 1./cfg.hw.genrate.value
    for itr in range(int(cfg.train[k].ntrains.base)):
        for ipu in range(int(cfg.train[k].npulses.base +
                             itr*cfg.train[k].npulses.delta)):
            fillpulse(cfg, k, itr, ipu,
                      vvv[int(timing[1][itr,ipu]):int(timing[2][itr,ipu]+1)])

def mktrain(cfg, k):
    timing = mktiming(cfg, k)
    marg = max(timing[0]//20, 1000)
    ttt = (np.arange(-marg, timing[0]+marg))/cfg.hw.genrate.value
    vvv = np.zeros(ttt.shape)
    filltrain(cfg, k, timing, vvv[marg:])
    return (ttt, vvv)
    
def fillpulse(cfg, k, itr, ipu, vv):
    fs_hz = cfg.hw.genrate.value
    amp1 = cfg.pulse[k].amp1_u.base + \
           itr*cfg.pulse[k].amp1_u.delta + \
           ipu*cfg.pulse[k].amp1_u.delti
    dur1 = int(fs_hz * (cfg.pulse[k].dur1_s.base +
                        itr*cfg.pulse[k].dur1_s.delta + 
                        ipu*cfg.pulse[k].dur1_s.delti))
    amp2 = cfg.pulse[k].amp2_u.base + \
           itr*cfg.pulse[k].amp2_u.delta + \
           ipu*cfg.pulse[k].amp2_u.delti
    dur2 = int(fs_hz * (cfg.pulse[k].dur2_s.base +
                        itr*cfg.pulse[k].dur2_s.delta + 
                        ipu*cfg.pulse[k].dur2_s.delti))

    typ = cfg.pulse[k].type.value
    if typ==Pulsetype.OFF:
        pass
    elif typ==Pulsetype.MONOPHASIC:
        vv[:dur1] = amp1
    elif typ==Pulsetype.BIPHASIC:
        vv[:dur1] = amp1
        vv[dur1:dur1+dur2] = amp2
    elif typ==Pulsetype.RAMP:
        tt = np.arange(dur1)
        vv[:dur1] = amp1 + (amp2-amp1)*tt/dur1
    elif typ==Pulsetype.SINE:
        tt = np.arange(dur1)
        vv[:dur1] = amp1*np.sin(2*np.pi*(tt-dur2)/dur1)+amp2
    elif typ==Pulsetype.TTL:
        vv[:dur1] = 5.0
    else:
        raise ValueError(f'Unknown pulsetype: {typ}')

def hastrainchange(cfg, k):
    if cfg.pulse[k].type.have1dur():
        if cfg.pulse[k].dur1_s.delta:
            return True
    if cfg.pulse[k].type.have2durUSE():
        if cfg.pulse[k].dur2_s.delta:
            return True
    if cfg.pulse[k].type.have1amp():
        if cfg.pulse[k].amp1_u.delta:
            return True
    if cfg.pulse[k].type.have2amp():
        if cfg.pulse[k].amp2_u.delta:
            return True
    return False

def haspulsechange(cfg, k):
    if cfg.pulse[k].type.have1dur():
        if cfg.pulse[k].dur1_s.delti:
            return True
    if cfg.pulse[k].type.have2durUSE():
        if cfg.pulse[k].dur2_s.delti:
            return True
    if cfg.pulse[k].type.have1amp():
        if cfg.pulse[k].amp1_u.delti:
            return True
    if cfg.pulse[k].type.have2amp():
        if cfg.pulse[k].amp2_u.delti:
            return True
    return False


def mkpulse(cfg, k, itr, ipu, margin=True):
    fs_hz = cfg.hw.genrate.value
    if cfg.pulse[k].type.have1dur():
        dur1 = int(fs_hz * (cfg.pulse[k].dur1_s.base +
                            itr*cfg.pulse[k].dur1_s.delta + 
                            ipu*cfg.pulse[k].dur1_s.delti))
    else:
        dur1 = 0
    if cfg.pulse[k].type.have2durUSE():
        dur2 = int(fs_hz * (cfg.pulse[k].dur2_s.base +
                            itr*cfg.pulse[k].dur2_s.delta + 
                            ipu*cfg.pulse[k].dur2_s.delti))
    else:
        dur2 = 0

    if margin:
        marg = max((dur1+dur2)//20, 2)
    else:
        marg = False

    tt = (np.arange(-marg, dur1+dur2+marg)) / fs_hz
    vv = np.zeros(tt.shape)
    fillpulse(cfg, k, itr, ipu, vv[marg:])
    return (tt, vv)
