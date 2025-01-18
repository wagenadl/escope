from picodaq.background import DAQProcess


        
def test_short():
    sdat = np.sin(2*np.pi*np.arange(0, 0.02, 1e-4) / 0.02).reshape(-1, 1)
    pd = Backend(rate=10*kHz, aichannels=[0], aochannels=[0])
    pd.write(sdat, None)
    
    def report(rd):
        dat = rd.read()
        if dat is None:
            print("None")
        else:
            print(dat.shape, np.mean(dat), np.std(dat))
    rd = Reader(pd.conn, lambda: report(rd))
    for k in range(3):
        time.sleep(1)
        print(rtime(), "write", k)
        pd.write(sdat, None)
    print(rtime(), "stopping reader")
    rd.stop()
    print(rtime(), "closing backend")
    rd = None
    pd.close()
    print(rtime(), "backend closed")

if __name__ == "__main__":
    test_short()
    
