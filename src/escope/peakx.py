# peakx.py - This file is part of EScope/ESpark
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


#from numba import jit
import numpy as np
from typing import Optional, Tuple

#@jit
#def _schmittcore(data, thr_on, thr_off):
#    trans = []
#    isup = False
#    for k in range(len(data)):
#        if data[k]<=thr_off if isup else data[k]>=thr_on:
#            trans.append(k)
#            isup = not isup
#    ion = trans[::2]
#    ioff = trans[1::2]
#    return ion, ioff

def _schmittcore(data, thr_on, thr_off):
    trans = []
    isup = False
    upcros = np.diff((data >= thr_on).astype(int)) > 0
    dncros = np.diff((data <= thr_off).astype(int)) > 0
    anyi = np.nonzero(upcros | dncros)[0]
    for i in anyi:
        if isup:
            if dncros[i]:
                trans.append(i)
                isup = False
        else:
            if upcros[i]:
                trans.append(i)
                isup = True

    trans = np.array(trans) + 1      
    ion = trans[::2]
    ioff = trans[1::2]
    return ion, ioff
    

class STARTTYPE:
    DROP_PARTIAL = 0
    INCLUDE_PARTIAL = 1
    
class ENDTYPE:
    DROP_PARTIAL = 0
    BROKEN_PARTIAL = 1
    INCLUDE_PARTIAL = 2
    

def schmitt(data: np.ndarray,
            thr_on: Optional[float] = None,
            thr_off: Optional[float] = None,
            endtype: int = ENDTYPE.INCLUDE_PARTIAL,
            starttype: int = STARTTYPE.INCLUDE_PARTIAL) \
            -> Tuple[np.array, np.array]:
    """Schmitt trigger of a continuous process

    Parameters
    ----------

    data
        The data to trawl for threshold crossings

    thr_on
        The upward threshold. If not given, defaults to 2/3.

    thr_off
        The downward threshold. If not given, defaults to ½ *thr_on*

    endtype
        If DATA is high at the end, the last downward crossing will
        be len(DATA). This optional argument modifies this behavior:

        If set to ENDTYPE.DROP_PARTIAL (0), the last upward crossing
        is ignored if there is no following downward crossing.

        If set to ENDTYPE.BROKEN_PARTIAL (1), the last upward crossing
        may be reported without a corresponding downward crossing, so 
        the two return values do not have the same length.
    
    starttype
        If DATA is high at the beginning, the first ION value will
        be 0. This optional argument modifies this behavior:

        If set to STARTTYPE.DROP_PARTIAL (0), such a “partial peak”
        is dropped.

    Returns
    -------

    ion
        The indices where DATA crosses up through *thr_on* coming from
        below *thr_off*

    ioff
        The indices where DATA crosses down through *thr_off* coming from
        above *thr_on*

    """
    
    if thr_on is None:
        if data.dtype==bool:
            thr_on = True
        else:
            thr_on = 2./3
    if thr_off is None:
        if data.dtype==bool:
            thr_off = False
        else:
            thr_off = thr_on / 2.
    if data.ndim != 1:
        raise ValueError('Input must be 1-d array')

    iup, idn = _schmittcore(data, thr_on, thr_off)

    if endtype==0:
        if len(iup)>len(idn):
            iup = iup[:len(idn)] # Drop last up transition
    elif endtype==1:
        pass # There may be an extra up transition
    elif endtype==2:
        if len(iup)>len(idn):
            idn.append(len(data))
    else:
        raise ValueError('Invalid end type')
    
    if starttype==0:
        if len(iup)>0 and iup[0]==0:
            iup = iup[1:]
            idn = idn[1:]
    elif starttype==1:
        pass
    else:
        raise ValueError('Invalid start type')

    return np.array(iup), np.array(idn)


def schmitt2(data: np.array, thr_a: float, thr_b: float) \
        -> Tuple[np.array, np.array, np.array, np.array]:
    '''Double Schmitt triggering

    Arguments
    ---------

    data
        The data to trawl for threshold crossings

    thr_a
        The “high” threshold

    thr_b
        The “low” threshold

    Returns
    -------

    on_a
        the up crossings through *thr_a*

    off_a
        the down crossings through *thr_a*

    on_b
        the up crossings through *thr_b*

    off_b
        the down corssings through *thr_b*

    Notes
    -----

    It is required that THR_B < THR_A.

    There are two equivalent ways to think about the result:
    
    (1) *on_a*, *off_a* are the up and down crossings through *thr_a*;
        *on_b*, *off_b* are the up and down crossings through *thr_b*.

    (2) *on_a*, *off_a* describe the broadest possible peak above *thr_a*;
        *on_b*, *off_b* describe the narrowest possible peak above *thr_b*.
        (But *on_b*, *off_b* describe wider peaks than *on_a*, *off_a*,
        since *thr_b* < *thr_a*.)
   
    A peak that exceeds *thr_b* but never exceeds *thr_a* is not
    reported.'''
   
    on_a, off_b = schmitt(data, thr_a, thr_b)
    off_a, on_b = schmitt(np.flip(data), thr_a, thr_b)
    off_a = np.flip(len(data) - off_a)
    on_b = np.flip(len(data) - on_b)
    return on_a, off_a, on_b, off_b


def schmittpeak(data: np.array, iup: np.array, idn: np.array) -> np.array:
    '''Find peaks in data after Schmitt triggering

    Arguments
    ---------

    data
        The data to trawl for threshold crossings

    ion
        The indices where DATA crosses up through *thr_on* coming from
        below *thr_off*, as returned by a previous call to *schmitt*

    ioff
        The indices where DATA crosses down through *thr_off* coming from
        above *thr_on*, as returned by a previous call to *schmitt*


    Returns
    -------

    Indices of peaks between pairs of upward and downward threshold
    crossings.

    Notes
    -----

    To avoid partial peaks at the beginning and end of *data*, consider
    using *starttype* = STARTTYPE.DROP_PARTIAL and/or
    *endtype* = ENDTYPE.DROP_PARTIAL when calling *schmitt*.

    '''

    ipk = np.zeros(iup.shape, dtype=iup.dtype)
    for k in range(len(iup)):
        ipk[k] = iup[k]+ np.argmax(data[iup[k]:idn[k]])
    return ipk


if __name__=='__main__':
    data = np.random.randn(100)
    iup, idn = schmitt(data, 1, -1)

    dat32 = data.astype(np.float32)
    iup1, idn1 = schmitt(dat32, 1, -1)

    iupa, idna, iupb, idnb = schmitt2(data, 1, -1)
    print(f'data = {data[:20]}')
    print(f'... {data[80:]}')
    print(f'iupa = {iupa}')
    print(f'idna = {idna}')
    print(f'iupb = {iupb}')
    print(f'idnb = {idnb}')
    ipk = schmittpeak(data, iupa, idna)
    print(f'ipk = {ipk}')
