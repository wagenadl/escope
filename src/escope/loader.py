import numpy as np
import json


def load(fn: str) -> tuple[np.ndarray, dict]:
    '''Load a recording from EScope 3.0

    Parameters:
        fn: Filename to load. This should be the ".escope" file.

    Returns:
        data - Data as a numpy array (see below)

        info - Auxiliary information as a dict containing:
                 "rundate" - the YYYYMMDD-HHMMSS formatted time when data were acquired
                 "rate_Hz" - the sampling rate (in Hertz)
                 "channels" - the names of the input channels
                 "scale" - the physical meaning of a value of 1.0 in each channel

    If the data were captured with triggering enabled, the shape of the returned 
    array will be CxNxL, where

        C is the number of channels in the recording
        N is the number of sweeps
        L is the length of each sweep

    If the data were captured without triggering, the shape will be CxT where C is 
    as above and

        T is the total length of the acquisition

    If the data were saved using "Save sweep", the shape is always CxL.

    Use len(data.shape) to conveniently test whether multiple individual sweeps are 
    represented.

    Note that scale factors are not applied. You will need to check info["scale"]
    and apply them yourself.
    '''

    if fn.endswith(".dat"):
        fn = fn[:-4]
    elif fn.endswith(".config"):
        fn = fn[:-7]
    elif fn.endswith(".escope"):
        fn = fn[:-7]

    with open(fn + ".escope") as fd:
        info = json.load(fd)
    with open(fn + ".dat", "rb") as fd:
        data = fd.read()
    with open(fn + ".config") as fd:
        config = json.load(fd)
    data = np.frombuffer(data)
    
    C = len(info['channels'])
    if config['trig']['enable'] and config["capt_enable"]:
        S = info['sweep_scans']
        N = len(data) // S // C
        if len(data) > N*S*C:
            print(f"Discarding partial sweep at end of acquisition: {(len(data) - N*S*C)/C} scans")
            data = data[:N*S*C]
        data = data.reshape(N, S, C).transpose(2,0,1)
    else:
        T = len(data) // C
        if len(data) > T*C:
            print(f"Discarding partial scan at end of acquisition")
            data = data[:T*C]
        data = data.reshape(T, C).transpose(1,0)
    return data, info


def plot(data: np.ndarray, info: dict):
    '''Example of how to plot data from EScope

    Parameters:
        data: must be a CxNxL array from load()
        info: must be an information dictionary from load()

    This function plots all the channels in a single figure;
    sweeps are concatenated together.
    '''
    COLORS = [ [ 0.9, 0.4, 0 ], [ 0, 0.6, 1 ], [ .8, 0, .9 ], [ 0., .8, 0. ],
               [ .9, 0, 0 ], [ 0, 0.4, 0 ], [ 0, 0, .8 ], [ 0.5, 0.3, 0 ] ]


    import matplotlib.pyplot as plt
    plt.ion()
    
    hassweeps = len(data.shape) == 3
    plt.clf()
    if hassweeps:
        C, N, L = data.shape
        tt = np.arange(L) / info['rate_Hz']
        for n in range(N):
            for c in range(C):
                plt.plot(tt, data[c,n], color=COLORS[c])
    else:
        C, T = data.shape
        tt = np.arange(T) / info['rate_Hz']
        for c in range(C):
            plt.plot(tt, data[c], color=COLORS[c])
    plt.xlabel('Time (s)')
    plt.legend([f"{chn} ({scl})" for chn, scl in zip(info['channels'], info['scale'])])
    plt.title(info['rundate'])
