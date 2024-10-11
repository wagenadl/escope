# spikex.py - This file is part of EScope/ESpark
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


import numpy as np
from typing import List, Optional

from . import peakx


_corrfac = {}
def _estimatemuckfactor(chunksize, nchunks=1000, ipart=25):
    myid = (chunksize, nchunks, ipart)
    if myid in _corrfac:
        return _corrfac[myid]
    dat = np.reshape(np.random.randn(chunksize*nchunks), (chunksize, nchunks))
    rms = np.std(dat, 0)
    K = int(ipart * nchunks / 100 + 0.5)
    est = np.partition(rms, K)[K]
    _corrfac[myid] = est
    return est


def rmsnoise(dat: np.ndarray[float],
             chunksize: int = 300,
             percentile: int = 25) -> float:
    '''Estimated RMS noise in a data trace

    Arguments
    ---------

    dat
        The data to be investigated as a length-T vector

    chunksize (optional)
        The number of samples per chunk. Reasonable values are
        whatever corresponds to 5 or 10 ms at your sampling rate.

    percentile (optional)
        The percentile at which to sample the chunks. Usually, the
        default is reasonable, but if you have extremely high firing
        rates, a lower number may work better.

    Returns
    -------

    The estimated RMS noise in the data

    Description
    ------------
    
    The data are split into small chunks and the RMS signal power is
    calculated for each chunk. In some of the chunks, that power will
    be dominated by the presence of spike or stimulus artifacts.
    However, in a decent fraction of chunks there are no spikes, so
    the RMS power in those chunks represents the actual RMS noise.
    
    This function attempts to extract the RMS noise from such chunks
    by sorting the chunks by their signal power, and finding the 25-th
    percentile. It corrects the result based on assumption of
    approximate Gaussianity.

    '''

    chunksize = int(chunksize)
    L = len(dat)
    N = L // chunksize # number of chunks
    cf = _estimatemuckfactor(chunksize, N, percentile)
    dat = np.reshape(dat[:N*chunksize], [N, chunksize])
    rms = np.std(dat, 1)
    K = int(percentile*N/100 + 0.5)
    est = np.partition(rms, K)[K]
    return est / cf


def detectspikes(yy: np.ndarray[float],
                 threshold: float,
                 polarity: int = 0,
                 tkill: int = 50,
                 upperthresh: Optional[float] = None) -> np.ndarray[int]:
    """Simple spike detection

    Parameters
    ----------
    yy
        A NumPy array of floats representing the data

    threshold
        The threshold for spike detection. Typically, 5× the value
        from *rmsnoise* is a reasonable threshold.

    polarity (optional)
        The polarity of the spikes (0 for both, 1 for positive,
        -1 for negative)

    tkill (optional)
        The minimum distance between spikes (in samples)

    upperthresh (optional)
        The maximum spike amplitude. If given, peaks that exceed it
        are not returned, so you can use *detectspikes* iteratively
        for very basic spike sorting.

    Returns
    -------

    A numpy array of integers indicating the indices of detected
    spikes within the recording

    Description
    -----------

    The algorithm first finds peaks (positive and/or negative
    depending on the *polarity* parameter) that exceed the
    threshold. Then, it drops minor peaks that are within *tkill*
    samples of major peaks. Finally, peaks that exceed *upperthresh*
    (if given) are discarded.

    """

    def droptoonear(ipk, hei, tkill):
        done = False
        while not done:
            done = True
            for k in range(len(ipk) - 1):
                if ipk[k+1] - ipk[k] < tkill:
                    done = False
                    if hei[k] < hei[k+1]:
                        hei[k] = 0
                    else:
                        hei[k+1] = 0
            idx = np.nonzero(hei)
            ipk = ipk[idx]
            hei = hei[idx]
        return ipk
            
    if polarity >= 0:
        iup, idn = peakx.schmitt(yy, threshold, 0)
        ipk = peakx.schmittpeak(yy, iup, idn)
        if tkill is not None:
            ipk = droptoonear(ipk, yy[ipk], tkill)
    else:
        ipk = None   

    if polarity <= 0:
        zz = -yy
        iup, idn = peakx.schmitt(zz, threshold, 0)
        itr = peakx.schmittpeak(zz, iup, idn)
        if tkill is not None:
            itr = droptoonear(itr, zz[itr], tkill)
    else:
        itr = None

    if ipk is None:
        res = itr
    elif itr is None:
        res = ipk
    else:
        res = np.sort(np.append(ipk, itr))

    if upperthresh is not None:
        res = res[np.abs(yy[res]) < upperthresh]

    return res

    
def cleancontext(idx: np.ndarray[int], dat: np.ndarray[float],
                 test: List[range] = [range(-25, -12), range(12, 25)],
                 testabs: List[range] = [range(-25, -4), range(4, 25)],
                 thr: float = 0.50,
                 absthr: float = 0.90) -> np.ndarray[int]:
    '''CLEANCONTEXT - Drop spikes if their context is not clean
    idx = CLEANCONTEXT(idx, dat) treats the spikes at IDX (from DETECTSPIKES
    run on DAT) to the classic filtering operation in MEABench. That is,
    spikes are dropped if :
      (1) there are samples with voltage >50% of peak voltage at a
          distance of 12 to 25 samples before or after the main peak,
    or
      (2) there are samples with absolute voltage >90% of peak at a 
          distance of 4 to 25 samples before or after the main peak.
    
    Optional argument TEST may specify a list of ranges to test at 50%;
    TESTABS may specify a list of ranges to test at 90% with abs. value.
    THR and ABSTHR override the 0.5 and 0.9 default test thresholds. 
    Set THR or ABSTHR to None to avoid the corresponding test.

    Spikes too near the start or end of the recording are dropped 
    unconditionally.'''

    keep = np.zeros(idx.shape, dtype=idx.dtype)
    if type(test)==list:
        test = np.concatenate(test)
    if type(testabs)==list:
        testabs = np.concatenate(testabs)
    t0 = np.min([np.min(test), np.min(testabs)])
    t1 = np.max([np.max(test), np.max(testabs)])
    T = len(dat)
    hei = dat[idx]
    pol = np.sign(hei)
    for k in range(len(idx)):
        t = idx[k]
        if t + t0 < 0 or t + t1 >= T:
            continue
        if thr is not None:
            if pol[k]>0:
                if any(dat[t + test] > thr*hei[k]):
                    continue
            else:
                if any(dat[t + test] < thr*hei[k]):
                    continue
        if absthr is not None:
            if any(np.abs(dat[t + testabs]) > absthr*np.abs(hei[k])):
                continue
        keep[k] = t
    return keep[keep > 0]
