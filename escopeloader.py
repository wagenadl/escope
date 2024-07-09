import numpy as np
import pickle
import matplotlib.pyplot as plt
plt.ion()


def _unpackstr(s):
    return s[1:-1]


def _unpackset(s, lines):
    s = s.strip()
    while lines and not s.endswith('}'):
        s += " " + lines.pop(0).strip()
    vv = []
    s = s[1:-1].strip()
    while s:
        if s.startswith("'"):
            idx = s[1:].index("'")
            vv.append(s[1:idx+1])
            s = s[idx+2:].strip()
        elif ' ' in s:
            idx = s.index(" ")
            v = s[:idx]
            if "." in v:
                vv.append(float(v))
            else:
                vv.append(int(v))
            s = s[idx+1:].strip()
    return vv


def loadescope(fn):
    '''Load a recording from EScope
    Arguments:
        fn - Filename to load. This may be the “.txt” or the “.dat” file
    Returns:
        data - Data as a numpy array
        info - Auxiliary information

    Data is shaped as CxNxL, where:
        C is the number of channels in the recording
        N is the number of sweeps
        L is the length of each sweep
    
    Info is a dictionary with the following contents:
        "rundate" - the YYYYMMDD-HHMMSS formatted time when data were acquired
        "rate_hz" - the sampling rate (in Hertz)
        "channels" - the names of the input channels
        "scale" - the physical meaning of a value of 1.0 in each channel
    '''

    if fn.endswith(".txt") or fn.endswith(".dat"):
        fn = fn[:-4]
    info = {}
    with open(fn + ".txt") as fd:
        lines = fd.readlines()
        while lines:
            line = lines.pop(0)
            if " = " in line:
                k, v = line.split(" = ")
                v = v.strip()
                print(f"key=[{k}] value=[{v}]")
                if v.startswith("{"):
                    v = _unpackset(v, lines)
                elif v.startswith("'"):
                    v = _unpackstr(v)
                elif "." in v:
                    v = float(v)
                else:
                    v = int(v)
                info[k] = v

    with open(fn + ".dat", "rb") as fd:
        data = fd.read()
    print(info)
    data = np.frombuffer(data)
    C = len(info['channels'])
    S = info['scans_per_sweep']
    N = len(data) // S // C
    
    data = data[:N*S*C].reshape(N, S, C).transpose([2,0,1])
    return data, info


def plotescope(data, info):
    '''Example of how to plot data from EScope
    Arguments:
        data - must be a CxNxL array from loadescope()
        info - must be an auxiliary information dictionary from loadescope()
    Returns:
        -
    Plots all the channels in a single figure; sweeps are concatenated
    together.
    '''
    C, N, S = data.shape
    tt = np.arange(N*S) / info['rate_hz']
    plt.plot(tt, data.reshape(C,N*S).T)
    plt.xlabel('Time (s)')
    cs = [f"{c} ({s})" for c,s in zip(info['channels'], info['scale'])]
    plt.ylabel("; ".join(cs))
    plt.title(info['rundate'])
