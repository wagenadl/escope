# loader.py - This file is part of EScope/ESpark
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
import json
import urllib
from typing import List, Optional, Union, Tuple

from .units import Units


def _readurl(url: str, binary: bool = False) -> Union[str, bytes]:
    if url.startswith("http"):
        with urllib.request.urlopen(url) as fd:
            data = fd.read()
            if binary:
                return data
            else:
                return data.decode('utf-8')
    else:
        if binary:
            with open(url, "rb") as fd:
                return fd.read()
        else:
            with open(url, "rt") as fd:
                return fd.read()


def load(fn: str) -> Tuple[np.ndarray, dict]:
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

    info = json.loads(_readurl(fn + ".escope"))
    data = _readurl(fn + ".dat", binary=True)
    if "config" not in info:
        info["config"] = json.loads(_readurl(fn + ".config"))

    if info["version"] >= "escope-3.2":
        data = np.frombuffer(data, dtype=np.float32)
    else:
        data = np.frombuffer(data)
    
    C = len(info['channels'])
    if info['config']['trig']['enable'] and info['config']["capt_enable"]:
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
    import matplotlib.pyplot as plt
    COLORS = [ [ 0.9, 0.4, 0 ], [ 0, 0.6, 1 ], [ .8, 0, .9 ], [ 0., .8, 0. ],
               [ .9, 0, 0 ], [ 0, 0.4, 0 ], [ 0, 0, .8 ], [ 0.5, 0.3, 0 ] ]

    units = []
    factors = []
    C = data.shape[0]
    for c in range(C):
        scale = info["scale"][c]
        uni = " ".join(scale.split(" ")[1:]) # drop numeric prefix
        if uni == 'V':
            uni = 'mV'
        units.append(uni)
        factors.append(Units(scale).asunits(uni))

    hassweeps = len(data.shape) == 3
    plt.clf()
    if hassweeps:
        C, N, L = data.shape
        tt = np.arange(L) / info['rate_Hz']
        for n in range(N):
            for c in range(C):
                plt.plot(tt, data[c,n] * factors[c], color=COLORS[c])
    else:
        C, T = data.shape
        tt = np.arange(T) / info['rate_Hz']
        for c in range(C):
            plt.plot(tt, data[c] * factors[c], color=COLORS[c])
    plt.xlabel('Time (s)')
    plt.legend([f"{chn} ({uni})" for chn, uni in zip(info['channels'], units)])
    plt.title(info['rundate'])


class Recording:
    '''Object-oriented access to EScope data

    The constructor loads data from a “.escope” file. If the name starts
    with “http://” or “https://”, the file is downloaded from the internet.
    
    '''

    def __init__(self, filename: str):
        '''Load a recording from a .escope file.'''
        self._data, self._info = load(filename)

    def info(self) -> dict:
        '''Information about the recording as a dictionary.
        '''
        return self._info

    def data(self, channel: int | str,
             units: Optional[str] = None) \
             -> Union[np.ndarray | Tuple[np.ndarray, str]]:
        '''Data for a given channel and corresponding units.

        Arguments
        ---------

        channel
            An integer index specifying the channel number or a
            string name for the channel (which must exist in the
            "channels" of the info() dict.

        units (optional)
            Desired units for returned data

        Returns
        -------

        If *units* are specified, the raw data are converted into those
        units and only the result is returned.

        If *units* are not specified, a tuple of data and their units
        is returned.

        For continuous acquisition or a single sweep, data are
        returned as a length-T vector where T is the number of samples
        in the recording. For triggered acquisition, data are returned
        as an NxT array, where N is the number of triggers and T is
        the number of samples per sweep.
        '''

        if type(channel)==str:
            channel = self._info["channels"].index(channel)
        
        scale = self._info["scale"][channel]
        if units is None:
            units = " ".join(scale.split(" ")[1:]) # drop numeric prefix
            return Units(self._data[channel], scale).asunits(units), units
        else:
            return Units(self._data[channel], scale).asunits(units)

    def time(self) -> np.ndarray:
        '''Timestamp vector in seconds.'''

        T = self._data.shape[-1]
        return np.arange(T) / self._info["rate_Hz"]

    def plot(self) -> None:
        '''Quick plot of the entire recording.'''
        
        plot(self._data, self._info)
        
    def rawdata(self, channel: Optional[int] = None) -> np.ndarray:
        '''Raw data from the recording.

        Arguments
        ---------
        channel (optional)
            An integer index specifying the channel number.

        Returns
        -------

        Data for a single channel or all channels

        For continuous acquisition or a single sweep, data are
        returned as a CxT array where C is the number of channels and
        T is the number of samples. For triggered acquisition, data
        are returned as a CxNxT array, where N is the number of
        triggers and T is the number of samples per sweep.

        If *channel* is specified, the result is either a length-T
        vector or an NxT array.

        '''
        
        if channel is None:
            return self._data
        else:
            return self._data[channel]
        
