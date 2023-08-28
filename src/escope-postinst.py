#!/usr/bin/env python

import os
import sys

mydir = os.path.dirname(sys.argv[0])

dappdata = get_special_folder_path("CSIDL_DESKTOPDIRECTORY") + '\EScope Data'
if not os.path.isdir(dappdata):
    os.mkdir(dappdata)
    directory_created(dappdata)

ddesktop = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
dstartmenu = get_special_folder_path("CSIDL_PROGRAMS")

tgt = os.path.join(sys.exec_prefix,"python.exe")

desc= "EScope"
arg = os.path.join(mydir, "escope")
shrt = os.path.join(ddesktop, "escope.lnk")
create_shortcut(tgt, desc,shrt,arg,dappdata)
shrt = os.path.join(dstartmenu, "escope.lnk")
create_shortcut(tgt, desc,shrt,arg,dappdata)

desc= "ESpark"
arg = os.path.join(mydir, "espark")
shrt = os.path.join(ddesktop, "espark.lnk")
create_shortcut(tgt, desc,shrt,arg,dappdata)
shrt = os.path.join(dstartmenu, "espark.lnk")
create_shortcut(tgt, desc,shrt,arg,dappdata)
