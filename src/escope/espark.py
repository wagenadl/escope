#!/usr/bin/python3

# espark.py

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import os
import re
import pickle
import numpy as np
from .escopelib import esparkwin

######################################################################
def main():
    print(f"This is ESpark {esparkwin.VERSION}")
    print("(C) 2010–2024 Daniel A. Wagenaar")
    print("ESpark is free software. Click “About” to learn more.")

    os.chdir(os.path.expanduser("~/Documents"))
    if not os.path.exists("EScopeData"):
        os.mkdir("EScopeData")
    os.chdir("EScopeData")
    app = QApplication(sys.argv)
    cfg = esparkwin.espconfig.basicconfig()
    mw = esparkwin.MainWin(cfg, True)
    mw.show()
    app.processEvents()#QEventLoop.AllEvents, maxtime=1)
    mw.resize(1400, 900) 
    app.processEvents()#QEventLoop.AllEvents, maxtime=1)
    mw.resize(1402, 900)
    app.exec_()
    
if __name__=='__main__':
    main()
