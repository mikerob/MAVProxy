#!/usr/bin/env python

"""
  MAVProxy ERS display console, implemented in a child process
  
  Adapted from wxconsole.MessageConsole - removed textconsole.SimpleConsole, only uses frame
 
"""
import threading
import textconsole, sys, time
from wxconsole_util import Value, Text
import platform
if platform.system() == 'Darwin':
    from billiard import Pipe, Process, Event, forking_enable, freeze_support
else:
    from multiprocessing import Pipe, Process, Event, freeze_support

class ERSConsole():
    '''
    a message console for MAVProxy
    '''
    def __init__(self,
                 title='MAVProxy: ERS'):
        if platform.system() == 'Darwin':
            forking_enable(False)
        self.title  = title
        self.menu_callback = None
        self.parent_pipe_recv,self.child_pipe_send = Pipe(duplex=False)
        self.child_pipe_recv,self.parent_pipe_send = Pipe(duplex=False)
        self.close_event = Event()
        self.close_event.clear()
        self.child = Process(target=self.child_task)
        self.child.start()
        self.child_pipe_send.close()
        self.child_pipe_recv.close()
        t = threading.Thread(target=self.watch_thread)
        t.daemon = True
        t.start()

    def child_task(self):
        '''child process - this holds all the GUI elements'''
        self.parent_pipe_send.close()
        self.parent_pipe_recv.close()

        import wx_processguard
        from wx_loader import wx
        from ersconsole_ui import ERSFrame
        app = wx.App(False)
        app.frame = ERSFrame(state=self, title=self.title)
        app.frame.SetDoubleBuffered(True)
        app.frame.Show()
        app.MainLoop()

    def watch_thread(self):
        '''watch for menu and button events from child'''
        from mp_settings import MPSetting
        try:
            while True:
                msg = self.parent_pipe_recv.recv()
                if self.menu_callback is not None:
                    self.menu_callback(msg)
                time.sleep(0.1)
        except EOFError:
            pass

    def write(self, text, fg='black', bg='white'):
        '''write to the console'''
        try:
            self.parent_pipe_send.send(Text(text, fg, bg))
        except Exception:
            pass

    def set_status(self, name, text='', row=0, fg='black', bg='white'):
        '''set a status value'''
        if self.is_alive():
            self.parent_pipe_send.send(Value(name, text, row, fg, bg))

    def set_menu(self, menu, callback):
        if self.is_alive():
            self.parent_pipe_send.send(menu)
            self.menu_callback = callback

    def close(self):
        '''close the console'''
        self.close_event.set()
        if self.is_alive():
            self.child.join(2)

    def is_alive(self):
        '''check if child is still going'''
        return self.child.is_alive()

        
if __name__ == "__main__":
    # test the console
    freeze_support()
    console = ERSConsole()
    while console.is_alive():
        console.write('Tick', fg='red')
        console.write(" %s " % time.asctime())
        console.set_status('GPS', 'GPS: OK', fg='blue', bg='green')
        console.set_status('Link1', 'Link1:\n OK', fg='green', bg='white')
        console.set_status('Date', 'Date: %s' % time.asctime(), fg='black', row=2)
        time.sleep(0.5)
