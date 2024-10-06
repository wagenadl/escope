#!/usr/bin/python3

import numpy as np
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


def rmsnoise(dat, chunksize=300, percentile=25):
    '''RMSNOISE - Estimated RMS noise in a data trace
    
    rms = RMSNOISE(dat) estimates the RMS noise in the given data (a
    1-d numpy array).  It is relatively insensitive to genuine spikes
    and simulus artifacts because it splits the data into small chunks
    and does the estimation within chunks. It then bases the final
    answer on the 25th percentile of estimates in chunks and corrects
    based on assumption of approximate Gaussianity. 

    Optional argument CHUNKSIZE specifies the length of chunks, in
    samples; good results are usually obtained when CHUNKSIZE corresponds
    to about 10 to 20 milliseconds of data.

    PERCENTILE specifies an alternative percentile for estimation. '''

    chunksize = int(chunksize)
    L = len(dat)
    N = L // chunksize # number of chunks
    cf = _estimatemuckfactor(chunksize, N, percentile)
    dat = np.reshape(dat[:N*chunksize], [N, chunksize])
    rms = np.std(dat, 1)
    K = int(percentile*N/100 + 0.5)
    est = np.partition(rms, K)[K]
    return est / cf


def detectspikes(yy, threshold, polarity=0, tkill=50, upperthresh=None):
    '''DETECTSPIKES - Simple spike detection
    idx = DETECTSPIKES(yy, threshold) performs simple spike detection:
      (1) Find peaks YY ≥ THRESHOLD;
      (2) Drop minor peaks within TKILL samples (default: 50) of major peaks;
      (3) Repeat for peaks YY ≤ -THRESHOLD.
    Optional argument POLARITY limits to positive (or negative) peaks if
    POLARITY > 0 (or < 0).
    Set TKILL=None to prevent step (2).
    A reasonable value for THRESHOLD could be 5× the value returned by
    RMSNOISE on your data.
    If UPPERTHRESH is given, spikes higher than that are not reported.'''

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

    
def cleancontext(idx, dat, test=[np.arange(-25, -12), np.arange(12, 25)],
                 testabs=[np.arange(-25, -4), np.arange(4, 25)],
                 thr=0.50, absthr=0.90):
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
