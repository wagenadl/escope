import numpy as np
import pickle
import matplotlib.pyplot as plt
plt.ion()

root = "/home/wagenaar/Documents/EScopeData"
expt = "20231018-123149"

with open(root + "/" + expt + ".escope", "rb") as fd:
    pkl = pickle.load(fd)

with open(root + "/" + expt + ".dat", "rb") as fd:
    dat = fd.read()
    
usehw = list(np.nonzero(np.logical_not(np.isnan(pkl.conn.hw)))[0])
nchns = len(usehw)
channels = [pkl.hw.channels[k] for k in usehw]
units = [pkl.conn.units[k] for k in usehw]
scale = [pkl.conn.scale[k] for k in usehw]
fs_Hz = pkl.hw.acqrate.value

ar = np.frombuffer(dat)
L = len(ar) // nchns
ar = ar.reshape(L, nchns)

plt.clf()
plt.plot(ar)

######################################################################
def unpackstr(s):
    return s[1:-1]

def unpackset(s, lines):
    s = s.strip()
    while lines and not s.endswith('}'):
        s += " " + lines.pop(0).strip()
    vv = []
    print("unpackset", s)
    s = s[1:-1].strip()
    while s:
        print("unpacking", s)
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

dct = {}
with open(root + "/" + expt + ".txt") as fd:
    lines = fd.readlines()
    while lines:
        line = lines.pop(0)
        if " = " in line:
            k, v = line.split(" = ")
            v = v.strip()
            print(f"key=[{k}] value=[{v}]")
            if v.startswith("{"):
                v = unpackset(v, lines)
            elif v.startswith("'"):
                v = unpackstr(v)
            elif "." in v:
                v = float(v)
            else:
                v = int(v)
            dct[k] = v
print(dct)

######################################################################
def loadescope(fn):
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
                    v = unpackset(v, lines)
                elif v.startswith("'"):
                    v = unpackstr(v)
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
    
    data = data.reshape(N, S, C).transpose([2,0,1])
    return data, info

#%%
data1, info = loadescope("/home/wagenaar/Documents/EScopeData/20231018-123154-011")
data2, info = loadescope("/home/wagenaar/Documents/EScopeData/20231018-123149")

def plotescope(data, info):
    C, N, S = data.shape
    tt = np.arange(N*S) / info['rate_hz']
    plt.plot(tt, data.reshape(C,N*S).T)
    plt.xlabel('Time (s)')
    cs = [f"{c} ({s})" for c,s in zip(info['channels'], info['scale'])]
    plt.ylabel("; ".join(cs))
    plt.title(info['rundate'])

plt.figure(1)
plt.clf()
plotescope(data1, info)

plt.figure(2)
plt.clf()
plotescope(data2, info)
