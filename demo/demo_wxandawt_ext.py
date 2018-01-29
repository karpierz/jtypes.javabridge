#!/usr/bin/env python

"""demo_wxandawt.py - show how to start the Javabridge with wxPython and AWT

python-javabridge is licensed under the BSD license.  See the
accompanying file LICENSE for details.

Copyright (c) 2003-2009 Massachusetts Institute of Technology
Copyright (c) 2009-2013 Broad Institute
All rights reserved.

"""

from __future__ import absolute_import
import wx
from jt import javabridge

app = wx.App(False)
frame = wx.Frame(None)
frame.Sizer = wx.BoxSizer(wx.HORIZONTAL)

start_button = wx.Button(frame, label="Start VM")
frame.Sizer.Add(start_button, 1, wx.ALIGN_CENTER_HORIZONTAL)
def fn_start(event):
    javabridge.start_vm([])
    javabridge.activate_awt()
    start_button.Enable(False)
    launch_button.Enable(True)
    stop_button.Enable(True)
start_button.Bind(wx.EVT_BUTTON, fn_start)

launch_button = wx.Button(frame, label="Launch AWT frame")
frame.Sizer.Add(launch_button, 1, wx.ALIGN_CENTER_HORIZONTAL)
def fn_launch_frame(event):
    javabridge.execute_runnable_in_main_thread(javabridge.run_script("""
        new java.lang.Runnable() {
            run: function() {
                with(JavaImporter(java.awt.Frame)) Frame().setVisible(true);
            }
        };"""))
launch_button.Bind(wx.EVT_BUTTON, fn_launch_frame)
launch_button.Enable(False)

stop_button = wx.Button(frame, label="Stop VM")
frame.Sizer.Add(stop_button, 1, wx.ALIGN_CENTER_HORIZONTAL)
def fn_stop(event):
    import threading
    def do_kill_vm():
        javabridge.attach()
        javabridge.kill_vm()
        launch_button.Enable(False)
        wx.CallAfter(stop_button.Enable, False)
    thread = threading.Thread(target=do_kill_vm)
    thread.start()
stop_button.Bind(wx.EVT_BUTTON, fn_stop)
stop_button.Enable(False)

frame.Layout()
frame.Show()
app.MainLoop()
