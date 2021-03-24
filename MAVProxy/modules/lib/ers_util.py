EM_ERROR = 0
EM_M_HOLD = 1
EM_M_AUTO = 2
EM_M_MANUAL = 3
EM_M_ACRO = 4
EM_M_STOP =5
EM_K_KILL = 10
EM_K_START = 11
EM_K_RUN = 12
EM_A_ARM = 20
EM_A_DISARM = 21

# PWM values for kill system - not used
EPWM_K_KILL = 1150
EPWM_K_RUN = 1850

# RC channels for ignition and start
ERC_IGNITION = 7 # hard coded currently
ERC_STARTER = 8 # hard coded currently


class ERSMessage:
    def __init__(self, type=EM_M_HOLD, text = ''):
        self.msgType = type
        self.msgText = text
        if not self.msgType in [EM_ERROR, EM_M_HOLD, EM_M_AUTO, EM_M_MANUAL, EM_M_ACRO, EM_M_STOP, EM_K_KILL, EM_K_START, EM_K_RUN, EM_A_ARM, EM_A_DISARM]:
            self.msgType = EM_ERROR
            
    def getMsgType(self):
        return self.msgType
        
    def getMsgText(self):
        return self.msgText