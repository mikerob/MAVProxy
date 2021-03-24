import time
import os
import mp_menu
from pymavlink import mavutil
from wxconsole_util import Value, Text
from wx_loader import wx
import ers_util
ERSMessage = ers_util.ERSMessage 


class ERSFrame(wx.Frame):
    """ The main frame of the console"""

    def __init__(self, state, title):
        self.state = state
        
        wx.Frame.__init__(self, None, title=title, size=(800,720))
        self.panel = wx.Panel(self)
        state.frame = self

        # initial values - has a kill / run / start command been sent (Cmd) and has it been executed (stat)
        self.ERSKillCmd = 'NONE'
        self.ERSKillStat = 'NONE'
        self.ERSModeCmd = 'NONE'
        self.ERSModeStat = 'NONE'
        self.ERSArmCmd = 'NONE'
        self.ERSArmStat = 'NONE'
        
        # values for the status bar
        self.values = {}

        self.menu = None
        self.menu_callback = None

        self.control = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL)
        
        t_font = self.control.GetFont()
        t_font.SetPointSize(14)
        t_font=t_font.Bold()
        self.panel.SetFont(t_font)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        # start with one status row
        self.status = [wx.BoxSizer(wx.HORIZONTAL)]
        self.vbox.Add(self.status[0], 0, flag=wx.ALIGN_LEFT | wx.TOP)
        #self.vbox.Add(self.control, 1, flag=wx.LEFT | wx.BOTTOM | wx.GROW)

        # create some sizers
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.GridBagSizer(hgap=1, vgap=0)
        self.hSizer = wx.BoxSizer(wx.HORIZONTAL)

        # Controls
        self.stopSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.modeSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.armSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Mode buttons
        self.M_HoldBtn = wx.Button(self.panel, wx.ID_ANY, '&HOLD')
        self.M_StopBtn = wx.Button(self.panel, wx.ID_ANY, '&STOP')
        self.M_AutoBtn = wx.Button(self.panel, wx.ID_ANY, 'AUTO')
        self.M_ManBtn = wx.Button(self.panel, wx.ID_ANY, 'MANUAL')
        self.M_AcroBtn = wx.Button(self.panel, wx.ID_ANY, 'ACRO')

        # Arrange modes in sizer
        self.stopSizer.Add(self.M_HoldBtn,2,wx.ALL|wx.EXPAND,2)
        self.stopSizer.Add(self.M_StopBtn,1,wx.ALL|wx.EXPAND,2)
        self.modeSizer.Add(self.M_ManBtn,1,wx.ALL|wx.EXPAND, 2)
        self.modeSizer.Add(self.M_AcroBtn,1,wx.ALL|wx.EXPAND,2)
        self.modeSizer.Add(self.M_AutoBtn,1,wx.ALL|wx.EXPAND, 2)
        self.Bind(wx.EVT_BUTTON, self.OnHold, self.M_HoldBtn)
        self.Bind(wx.EVT_BUTTON, self.OnAuto, self.M_AutoBtn)
        self.Bind(wx.EVT_BUTTON, self.OnAcro, self.M_AcroBtn)
        self.Bind(wx.EVT_BUTTON, self.OnMan, self.M_ManBtn)
        self.Bind(wx.EVT_BUTTON, self.OnStop, self.M_StopBtn)

        # Arm / disarm controle
        self.A_ArmBtn = wx.Button(self.panel, wx.ID_ANY, '&ARM')
        self.A_DisarmBtn = wx.Button(self.panel, wx.ID_ANY, '&DISARM')
        self.armSizer.Add(self.A_DisarmBtn,2,wx.ALL|wx.EXPAND,2)
        self.armSizer.Add(self.A_ArmBtn,2,wx.ALL|wx.EXPAND,2)
        self.Bind(wx.EVT_BUTTON, self.OnArm, self.A_ArmBtn)
        self.Bind(wx.EVT_BUTTON, self.OnDisarm, self.A_DisarmBtn)
        
        # Kill engine controls
        self.killSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.K_KillBtn = wx.Button(self.panel, wx.ID_ANY, "&KILL")
        self.killSizer.Add(self.K_KillBtn, 2, wx.ALL|wx.EXPAND,2)  
        self.Bind(wx.EVT_BUTTON, self.OnKill, self.K_KillBtn)

        # Run / Start engine controls
        self.engSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.K_StartBtn = wx.Button(self.panel, wx.ID_ANY, "&START")
        self.engSizer.Add(self.K_StartBtn, 1, wx.ALL|wx.EXPAND,1)  
        self.Bind(wx.EVT_BUTTON, self.OnStart, self.K_StartBtn)
        self.K_RunBtn = wx.Button(self.panel, wx.ID_ANY, "RUN")
        self.engSizer.Add(self.K_RunBtn, 1, wx.ALL|wx.EXPAND,2)
        self.Bind(wx.EVT_BUTTON, self.OnRun, self.K_RunBtn)

        # Enables addressing by name string
        self.btnsDict = {'HOLD' : self.M_HoldBtn,
                        'AUTO'  : self.M_AutoBtn,
                        'MANUAL': self.M_ManBtn,
                        'ACRO'  : self.M_AcroBtn,
                        'STOP'  : self.M_StopBtn,
                        'KILL'  : self.K_KillBtn,
                        'START' : self.K_StartBtn,
                        'RUN'   : self.K_RunBtn,
                        'ARM'   : self.A_ArmBtn,
                        'DISARM': self.A_DisarmBtn}
        # Status data
        self.s_date = wx.StaticText(self.panel, label="Date: XXXX", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.values['Date']=self.s_date
        
        # Block of ACAWS
        self.acawsGrid = wx.GridBagSizer(vgap=5, hgap=5)
        thisrow = 0
        self.s_rc = wx.StaticText(self.panel, label="RC", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.acawsGrid.Add(self.s_rc, pos=(thisrow,0), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['RC']=self.s_rc
        self.s_mag = wx.StaticText(self.panel, label="MAG", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.acawsGrid.Add(self.s_mag, pos=(thisrow,1), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['MAG']=self.s_mag
        self.s_ekf = wx.StaticText(self.panel, label="EKF", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.acawsGrid.Add(self.s_ekf, pos=(thisrow,2), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['EKF']=self.s_ekf
        thisrow=1
        self.s_ins = wx.StaticText(self.panel, label="INS", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.acawsGrid.Add(self.s_ins, pos=(thisrow,0), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['INS']=self.s_ins
        self.s_ahrs = wx.StaticText(self.panel, label="AHRS", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.acawsGrid.Add(self.s_ahrs, pos=(thisrow,1), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['AHRS']=self.s_ahrs
        self.s_log = wx.StaticText(self.panel, label="LOG", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.acawsGrid.Add(self.s_log, pos=(thisrow,2), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['LOG']=self.s_log
        
        self.acawsGrid.AddGrowableCol(0,1)
        self.acawsGrid.AddGrowableCol(1,1)
        self.acawsGrid.AddGrowableCol(2,1)
        

        self.selfGrid = wx.GridBagSizer(vgap=5, hgap=5)
        # Status Row 0
        thisrow=0
        self.s_mode = wx.StaticText(self.panel, label="Mode XXXX", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_mode, pos=(thisrow,0), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['Mode']=self.s_mode
        
        """self.s_arm = wx.StaticText(self.panel, label="ARM", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_arm, pos=(thisrow,1), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['ARM']=self.s_arm"""
        self.killPWMSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.s_killLabel = wx.StaticText(self.panel, label="Kill PWM:", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.killPWMSizer.Add(self.s_killLabel, 0, flag=wx.EXPAND|wx.ALL)
        self.s_killPWM = wx.StaticText(self.panel, label="0000", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.killPWMSizer.Add(self.s_killPWM, 1, flag=wx.EXPAND|wx.ALL)
        self.selfGrid.Add(self.killPWMSizer, pos=(thisrow,1), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['KillPWM']=self.s_killPWM
        
        self.selfGrid.AddGrowableCol(0,1)
        self.selfGrid.AddGrowableCol(1,1)
        
        # Status Row 1
        thisrow=thisrow+1
        self.s_GPS = wx.StaticText(self.panel, label="GPS --", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_GPS, pos=(thisrow,0), flag=wx.EXPAND|wx.ALL|wx.CENTER,)
        self.values['GPS']=self.s_GPS
        
        self.startPWMSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.s_startLabel = wx.StaticText(self.panel, label="Start PWM:", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.startPWMSizer.Add(self.s_startLabel, 0, flag=wx.EXPAND|wx.ALL)
        self.s_startPWM = wx.StaticText(self.panel, label="0000", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.startPWMSizer.Add(self.s_startPWM, 1, flag=wx.EXPAND|wx.ALL)
        self.selfGrid.Add(self.startPWMSizer, pos=(thisrow,1), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['StartPWM']=self.s_startPWM
        
        # Status Row 2
        thisrow=thisrow+1
        self.s_speed = wx.StaticText(self.panel, label="Speed ---", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_speed, pos=(thisrow,0), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['GPSSpeed']=self.s_speed
        
        self.s_xtrack = wx.StaticText(self.panel, label="Xtrack ---", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_xtrack,  pos=(thisrow,1), flag=wx.ALL|wx.EXPAND)
        self.values['Xtrack']=self.s_xtrack
        
        # Status Row 3
        thisrow=thisrow+1
        self.s_radio = wx.StaticText(self.panel, label="Radio ---", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_radio, pos=(thisrow,0), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['Radio']=self.s_radio
        
        self.s_HAcc = wx.StaticText(self.panel, label="HAcc: ", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_HAcc, pos=(thisrow,1),flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['HAcc']=self.s_HAcc
        
        # Status Row 4
        thisrow=thisrow+1
        self.s_link1 = wx.StaticText(self.panel, label="Link1 ---", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_link1, pos=(thisrow,0), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['Link0']=self.s_link1
        
        """ NEED TO GET LINK TO SPAN, ONLY ONE PER LINE """
        
        self.s_link2 = wx.StaticText(self.panel, label="Link2 ---", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_link2, pos=(thisrow,1), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['Link1']=self.s_link2
        
        # Status Row 5
        thisrow=thisrow+1
        self.s_thr = wx.StaticText(self.panel, label="Thr ---", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_thr, pos=(thisrow,0), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['Thr']=self.s_thr
        
        self.s_steer = wx.StaticText(self.panel, label="Steer ---", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.selfGrid.Add(self.s_steer, pos=(thisrow,1), flag=wx.EXPAND|wx.ALL|wx.CENTER)
        self.values['Steer']=self.s_steer

        # Battery 1 voltage
        # Battery 2 voltage
        self.statLine = wx.StaticLine(self.panel)
        
        self.hSizer.Add(grid, 0, wx.ALL, 5)
        self.mainSizer.Add(self.s_date,1,wx.ALL|wx.EXPAND,5)
        self.mainSizer.Add(self.killSizer,3,wx.ALL|wx.EXPAND,1)
        self.mainSizer.Add(self.stopSizer,3,wx.ALL|wx.EXPAND,1)
        self.mainSizer.Add(self.modeSizer,1,wx.ALL|wx.EXPAND,1)
        self.mainSizer.Add(self.engSizer,1,wx.ALL|wx.EXPAND,1)
        self.mainSizer.Add(self.armSizer,1,wx.ALL|wx.EXPAND,1)

        self.mainSizer.Add(self.statLine,0, wx.ALL|wx.EXPAND,5)
        self.mainSizer.Add(self.acawsGrid,1, wx.ALL|wx.EXPAND,5)
        self.mainSizer.Add(self.selfGrid,1,wx.ALL|wx.EXPAND,5)
        self.mainSizer.Add(self.control, 1, flag=wx.LEFT | wx.BOTTOM | wx.GROW)
        self.mainSizer.Add(self.vbox, 1, flag=wx.ALL|wx.EXPAND)
        
        self.panel.SetSizerAndFit(self.mainSizer)
        self.mainSizer.Fit(self)
        
        #self.panel.SetSizer(self.vbox)

        self.timer = wx.Timer(self)

        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(100)

        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_TEXT_URL, self.on_text_url)

        self.Show(True)
        self.pending = []

    def UpdateMode(self, stat='XXXX', cmd='XXXX'):
        #wx.MessageBox('Current: %s, New: %s' % (self.ERSModeStat, stat))
        if not stat == 'XXXX': # Mode status change
            if not self.ERSModeStat == 'NONE':
                self.btnsDict[self.ERSModeStat].SetBackgroundColour(wx.NullColour)
            if stat in self.btnsDict:
                self.btnsDict[stat].SetBackgroundColour((0,255,0))
                self.ERSModeStat = stat
                if self.ERSModeStat == self.ERSModeCmd:
                    #wx.MessageBox('Cmd: %s, Stat: %s' % (self.ERSModeCmd, self.ERSModeStat))
                    self.ERSModeCmd = 'NONE'
        if not cmd == 'XXXX': # Commanded mode change
            if not self.ERSModeCmd == 'NONE':
                self.btnsDict[self.ERSModeCmd].SetBackgroundColour(wx.NullColour)
            if cmd in self.btnsDict:
                self.btnsDict[cmd].SetBackgroundColour((255,0,0))
                self.ERSModeCmd = cmd

    def UpdateArm(self, stat='XXXX', cmd='XXXX'):
        # If stat has been set, then update button color to green
        if not stat == 'XXXX': # Arm status change
            if not self.ERSArmStat == 'NONE':
                self.btnsDict[self.ERSArmStat].SetBackgroundColour(wx.NullColour)
            if stat in self.btnsDict:
                self.btnsDict[stat].SetBackgroundColour((0,255,0))
                self.ERSArmStat = stat
                if self.ERSArmStat == self.ERSArmCmd:
                    self.ERSArmCmd = 'NONE'
        if not cmd == 'XXXX': # Commanded Arm change
            if not self.ERSArmCmd == 'NONE':
                self.btnsDict[self.ERSArmCmd].SetBackgroundColour(wx.NullColour)
            if cmd in self.btnsDict:
                self.btnsDict[cmd].SetBackgroundColour((255,0,0))
                self.ERSArmCmd = cmd

    def UpdateKill(self, stat='XXXX', cmd='XXXX'): # UPDATE
        # If stat has been set, then update button color to green
        if not stat == 'XXXX': # Kill status change
            if not self.ERSKillStat == 'NONE':
                self.btnsDict[self.ERSKillStat].SetBackgroundColour(wx.NullColour)
            if stat in self.btnsDict:
                self.btnsDict[stat].SetBackgroundColour((0,255,0))
                self.ERSKillStat = stat
                if self.ERSKillStat == self.ERSKillCmd:
                    self.ERSKillCmd = 'NONE'
        if not cmd == 'XXXX': # Commanded Kill change
            if not self.ERSKillCmd == 'NONE':
                self.btnsDict[self.ERSKillCmd].SetBackgroundColour(wx.NullColour)
            if cmd in self.btnsDict:
                self.btnsDict[cmd].SetBackgroundColour((255,0,0))
                self.ERSKillCmd = cmd

    # Callbacks defined on creation of button, set up msg for menu_callback in mavproxy_ers.py                
    def OnHold(self,event):
        #wx.MessageBox("MODE HOLD")
        msg = ERSMessage(type=ers_util.EM_M_HOLD, text='HOLD')
        self.send_message(msg)
        self.UpdateMode(cmd='HOLD')
        
    def OnAuto(self,event):
        #wx.MessageBox("MODE AUTO")
        msg = ERSMessage(type=ers_util.EM_M_AUTO, text='AUTO')
        self.send_message(msg)
        self.UpdateMode(cmd='AUTO')

    def OnAcro(self,event):
        #wx.MessageBox("MODE AUTO")
        msg = ERSMessage(type=ers_util.EM_M_ACRO, text='ACRO')
        self.send_message(msg)
        self.UpdateMode(cmd='ACRO')
    
    def OnMan(self,event):
        #wx.MessageBox("MODE AUTO")
        msg = ERSMessage(type=ers_util.EM_M_MANUAL, text='MANUAL')
        self.send_message(msg)
        self.UpdateMode(cmd='MANUAL')
        
    def OnStop(self,event):
        #wx.MessageBox("Set speed to 0, throttle to -90")
        msg = ERSMessage(type=ers_util.EM_M_STOP, text='STOP')
        self.send_message(msg)
        self.UpdateMode(cmd='STOP')

    def OnArm(self,event):
        msg = ERSMessage(type=ers_util.EM_A_ARM, text='ARM')
        self.send_message(msg)
        self.UpdateArm(cmd='ARM')
        
    def OnDisarm(self,event):
        msg = ERSMessage(type=ers_util.EM_A_DISARM, text='DISARM')
        self.UpdateMode()
        self.UpdateArm(cmd='DISARM')
        
    def OnKill(self,event): # UPDATE
        msg = ERSMessage(type=ers_util.EM_K_KILL, text=str(ers_util.EPWM_K_KILL))
        self.send_message(msg)
        self.UpdateKill(cmd='KILL')

    def OnStart(self,event): # UPDATE
        msg = ERSMessage(type=ers_util.EM_K_START, text='START')
        self.send_message(msg)
        self.UpdateKill(cmd='START')
        
    def OnRun(self,event): # UPDATE
        msg = ERSMessage(type=ers_util.EM_K_RUN, text=str(ers_util.EPWM_K_RUN))
        self.send_message(msg)
        self.UpdateKill(cmd='RUN')
        
    def send_message(self, msg):
        state = self.state
        if isinstance(msg, ERSMessage):
            if msg.msgType != ers_util.EM_ERROR:
                state.child_pipe_send.send(msg)
                return
            elif msg.msgType == ers_util.EM_ERROR:
                wx.MessageBox("Bad message")
 
    def on_menu(self, event):
        '''handle menu selections'''
        state = self.state
        ret = self.menu.find_selected(event)
        if ret is None:
            return
        ret.call_handler()
        state.child_pipe_send.send(ret)

    def on_text_url(self, event):
        '''handle double clicks on URL text'''
        try:
            import webbrowser
        except ImportError:
            return
        mouse_event = event.GetMouseEvent()
        if mouse_event.LeftDClick():
            url_start = event.GetURLStart()
            url_end = event.GetURLEnd()
            url = self.control.GetRange(url_start, url_end)
            try:
                # attempt to use google-chrome
                browser_controller = webbrowser.get('google-chrome')
                browser_controller.open_new_tab(url)
            except webbrowser.Error:
                # use the system configured default browser
                webbrowser.open_new_tab(url)

    def on_idle(self, event):
        time.sleep(0.05)

    # Timer function to check ACTUAL vehicle status and update UI elements as required - confirmation that ARM etc have occurred
    # How often does the timer run ??
    # Use this to machine gun HOLD and KILL
    def on_timer(self, event):
        state = self.state
        if state.close_event.wait(0.001):
            self.timer.Stop()
            self.Destroy()
            return
        # If we're still trying to change to HOLD mode, Disarm, Kill or Stop, send another message
        if self.ERSModeCmd == 'HOLD':
            msg = ERSMessage(type=ers_util.EM_M_HOLD, text='HOLD')
            self.send_message(msg)
        if self.ERSModeCmd == 'STOP':
            msg = ERSMessage(type=ers_util.EM_M_STOP, text='STOP')
            self.send_message(msg)
        if self.ERSArmCmd == 'DISARM':
            msg = ERSMessage(type=ers_util.EM_A_DISARM, text='DISARM')
            self.send_message(msg)
        if self.ERSKillCmd == 'KILL': 
            msg = ERSMessage(type=ers_util.EM_K_KILL, text='KILL')
            self.send_message(msg)
        
        # Copied from wxconsole_ui.py
        while state.child_pipe_recv.poll():
            obj = state.child_pipe_recv.recv()
            if isinstance(obj, Value):
                # request to set a status field
                if not obj.name in self.values:
                    # create a new status field
                    value = wx.StaticText(self.panel, -1, obj.text)
                    # possibly add more status rows
                    for i in range(len(self.status), obj.row+1):
                        self.status.append(wx.BoxSizer(wx.HORIZONTAL))
                        self.vbox.Insert(len(self.status)-1, self.status[i], 0, flag=wx.ALIGN_LEFT | wx.TOP)
                        self.vbox.Layout()
                    self.status[obj.row].Add(value, border=5)
                    self.status[obj.row].AddSpacer(20)
                    self.values[obj.name] = value
                value = self.values[obj.name]
                value.SetForegroundColour(obj.fg)
                value.SetBackgroundColour(obj.bg)
                value.SetLabel(obj.text)
                # If it's a MODE message and it's a change from current, or there's an outstanding command
                # Last condition is required in case the mode change comes in too quickly
                if (obj.name == 'Mode' and (not obj.text == self.ERSModeStat or not self.ERSModeCmd =='NONE')):
                    self.UpdateMode(stat=obj.text)
                # Update Arm status
                if (obj.name == 'ARM' and (not obj.text == self.ERSArmStat or not self.ERSArmCmd == 'NONE')):
                    self.UpdateArm(stat=obj.text)
                if (obj.name == 'Kill' and (not obj.text == self.ERSKillStat or not self.ERSKillCmd =='NONE')):
                    self.UpdateKill(stat=obj.text)
                if (obj.name == 'ACK'): # If we got an ACK packet showing success
                    # And it's for a change speed command and we were trying to change speed
                    if (int(obj.text) == mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED and self.ERSModeCmd == 'STOP'):
                         self.UpdateMode(stat = 'STOP') # Assume it succeeded
                         
                self.values['Date'].SetLabel('Date: %s' % time.asctime())
                self.panel.Layout()
            elif isinstance(obj, Text):
                '''request to add text to the console'''
                self.pending.append(obj)
                for p in self.pending:
                    # we're scrolled at the bottom
                    oldstyle = self.control.GetDefaultStyle()
                    style = wx.TextAttr()
                    style.SetTextColour(p.fg)
                    style.SetBackgroundColour(p.bg)
                    self.control.SetDefaultStyle(style)
                    self.control.AppendText(p.text)
                    self.control.SetDefaultStyle(oldstyle)
                self.pending = []
            elif isinstance(obj, mp_menu.MPMenuTop):
                if obj is not None:
                    self.SetMenuBar(None)
                    self.menu = obj
                    self.SetMenuBar(self.menu.wx_menu())
                    self.Bind(wx.EVT_MENU, self.on_menu)
                self.Refresh()
                self.Update()
