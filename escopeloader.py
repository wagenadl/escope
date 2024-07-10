import numpy as np
import json
import matplotlib.pyplot as plt
plt.ion()

def load(fn: str) -> tuple[np.ndarray, dict]:
    '''Load a recording from EScope 3.0

    Parameters:
        fn: Filename to load. This should be the ".escope" file.

    Returns:
        data - Data as a CxNxL numpy array, where
            - C is the number of channels in the recording
            - N is the number of sweeps
            - L is the length of each sweep

        info - Auxiliary information as a dict containing:
            - "rundate" - the YYYYMMDD-HHMMSS formatted time when data were acquired
            - "rate_Hz" - the sampling rate (in Hertz)
            - "channels" - the names of the input channels
            - "scale" - the physical meaning of a value of 1.0 in each channel
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
    data = np.frombuffer(data)
    C = len(info['channels'])
    S = info['sweep_scans']
    N = len(data) // S // C
    if len(data) > N*S*C:
        print(f"Discarding partial sweep at end of acquisition: {(len(data) - N*S*C)/C} scans")
    data = data[:N*S*C].reshape(N, S, C).transpose([2,0,1])
    return data, info


def plot(data: np.ndarray, info: dict):
    '''Example of how to plot data from EScope

    Parameters:
        data: must be a CxNxL array from load()
        info: must be an information dictionary from load()

    This function plots all the channels in a single figure;
    sweeps are concatenated together.
    '''
    C, N, S = data.shape
    tt = np.arange(N*S) / info['rate_Hz']
    plt.plot(tt, data.reshape(C, N*S).T)
    plt.xlabel('Time (s)')
    plt.legend([f"{chn} ({scl})" for chn, scl in zip(info['channels'], info['scale'])])
    plt.title(info['rundate'])
