"""
  MAVProxy console

  uses lib/console.py for display
"""

import os, sys, math, time

#from MAVProxy.modules.lib import wxconsole
#from MAVProxy.modules.lib import textconsole
from MAVProxy.modules.lib import ersconsole
from MAVProxy.modules.lib import ers_util
from MAVProxy.modules.mavproxy_map import mp_elevation
from pymavlink import mavutil
from MAVProxy.modules.lib import mp_util
from MAVProxy.modules.lib import mp_module
from MAVProxy.modules.lib import wxsettings
from MAVProxy.modules.lib.mp_menu import *


class ERSModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(ERSModule, self).__init__(mpstate, "ERS", "Something", public=True)
        self.in_air = False
        self.start_time = 0.0
        self.total_time = 0.0
        self.speed = 0
        self.max_link_num = 0
        self.last_sys_status_health = 0
        #self.ERS_console = ersconsole.ERSConsole(title='ERS Console')
        self.ERS_console = ersconsole.ERSConsole(title='ERS Console')
        # setup some default status information
        self.ERS_console.set_status('Mode', 'UNKNOWN', row=0, fg='blue')
        self.ERS_console.set_status('Kill', 'UNKNOWN', row=0, fg='blue')
        self.ERS_console.set_status('ARM', 'ARM', fg='grey', row=0)
        self.ERS_console.set_status('GPS', 'GPS: --', fg='red', row=0)
        self.ERS_console.set_status('Vcc', 'Vcc: --', fg='red', row=0)
        self.ERS_console.set_status('Radio', 'Radio: --', row=0)
        self.ERS_console.set_status('INS', 'INS', fg='grey', row=0)
        self.ERS_console.set_status('MAG', 'MAG', fg='grey', row=0)
        self.ERS_console.set_status('AS', 'AS', fg='grey', row=0)
        self.ERS_console.set_status('RNG', 'RNG', fg='grey', row=0)
        self.ERS_console.set_status('AHRS', 'AHRS', fg='grey', row=0)
        self.ERS_console.set_status('EKF', 'EKF', fg='grey', row=0)
        self.ERS_console.set_status('LOG', 'LOG', fg='grey', row=0)
        self.ERS_console.set_status('Heading', 'Hdg ---/---', row=2)
        self.ERS_console.set_status('Alt', 'Alt ---', row=2)
        self.ERS_console.set_status('AGL', 'AGL ---/---', row=2)
        #self.ERS_console.set_status('AirSpeed', 'AirSpeed --', row=2)
        self.ERS_console.set_status('GPSSpeed', 'GPSSpeed --', row=2)
        self.ERS_console.set_status('Thr', 'Thr ---', row=2)
        self.ERS_console.set_status('Roll', 'Roll ---', row=2)
        self.ERS_console.set_status('Pitch', 'Pitch ---', row=2)
        self.ERS_console.set_status('Wind', 'Wind ---/---', row=2)
        self.ERS_console.set_status('WP', 'WP --', row=3)
        self.ERS_console.set_status('WPDist', 'Distance ---', row=3)
        self.ERS_console.set_status('WPBearing', 'Bearing ---', row=3)
        #self.ERS_console.set_status('AltError', 'AltError --', row=3)
        #self.ERS_console.set_status('AspdError', 'AspdError --', row=3)
        self.ERS_console.set_status('FlightTime', 'FlightTime --', row=3)
        self.ERS_console.set_status('ETR', 'ETR --', row=3)
        self.ERS_console.set_status('Button', 'NONE', row=3, bg='orange')

        self.ERS_console.ElevationMap = mp_elevation.ElevationModel()

        # create the main menu
        if mp_util.has_wxpython:
            self.menu = MPMenuTop([])
            self.add_menu(MPMenuSubMenu('MAVProxy',
                                        items=[MPMenuItem('Settings', 'Settings', 'menuSettings'),
                                               MPMenuItem('Map', 'Load Map', '# module load map')]))

    def add_menu(self, menu):
        '''add a new menu'''
        self.menu.add(menu)
        self.ERS_console.set_menu(self.menu, self.menu_callback)

    def unload(self):
        '''unload module'''
        self.ERS_console.close()
        self.ERS_console = textconsole.SimpleConsole()

    def menu_callback(self, m):
        '''called on menu selection or button click'''
        if isinstance(m, ers_util.ERSMessage):
            type = m.getMsgType()
            text = m.getMsgText()

            if type == ers_util.EM_M_HOLD:
                self.ERS_console.set_status('Button', 'HOLD', bg='green')
                self.set_mode('HOLD')
            elif type == ers_util.EM_M_AUTO:
                self.ERS_console.set_status('Button', 'AUTO', bg='green')
                self.set_mode('AUTO')
            elif type == ers_util.EM_M_MANUAL:
                self.ERS_console.set_status('Button', 'MANUAL', bg='green')
                self.set_mode('MANUAL')                
            elif type == ers_util.EM_M_ACRO:
                self.ERS_console.set_status('Button', 'ACRO', bg='green')  
                self.set_mode('ACRO')  
            elif type == ers_util.EM_M_STOP:
                self.ERS_console.set_status('Button', 'STOP', bg='red') 
                self.master.mav.command_long_send(self.target_system,  # target_system
                                                self.target_component,
                                                mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # command
                                                0, # confirmation                                                
                                                1, # ground speed
                                                0, # speed (m/s)
                                                0, # throttle
                                                0, # absolute
                                                0, 0, 0) # Empty                
            elif type == ers_util.EM_K_KILL:
                self.ERS_console.set_status('Button', 'KILL', bg='red')
                self.master.mav.command_long_send(self.target_system,
                                                   self.target_component,
                                                   mavutil.mavlink.MAV_CMD_DO_ENGINE_CONTROL,
                                                   0, # confirmation                                                   
                                                   0, # stop engine
                                                   0, # warm (0) / cold (1) start
                                                   0, # height delay
                                                   0, 0, 0, 0)                                   
            elif type == ers_util.EM_K_START:
                self.ERS_console.set_status('Button', 'START', bg='green')
                self.master.mav.command_long_send(self.target_system,
                                                   self.target_component,
                                                   mavutil.mavlink.MAV_CMD_DO_ENGINE_CONTROL, 
                                                   0, # confirmation
                                                   1, # start engine
                                                   0, # warm (0) / cold (1) start
                                                   0, # height delay
                                                   0, 0, 0, 0)    
            elif type == ers_util.EM_K_RUN:
                self.ERS_console.set_status('Button', 'RUN', bg='green')
                self.master.mav.command_long_send(self.target_system,
                                                   self.target_component,
                                                   mavutil.mavlink.MAV_CMD_DO_ENGINE_CONTROL, 
                                                   0, # confirmation                                                   
                                                   2, # ignition on
                                                   0, # warm (0) / cold (1) start
                                                   0, # height delay
                                                   0, 0, 0, 0)                                    
            elif type == ers_util.EM_A_ARM:
                self.ERS_console.set_status('Button', 'ARM', bg='green')                     
                self.master.mav.command_long_send(self.target_system,  # target_system
                                                self.target_component,
                                                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, # command
                                                0, # confirmation
                                                1, # param1 (1 to indicate arm)
                                                0, # param2  (all other params meaningless)
                                                0, 0, 0, 0, 0) # param7                                                
            elif type == ers_util.EM_A_DISARM:
                self.ERS_console.set_status('Button', 'DISARM', bg='red')
                self.master.mav.command_long_send(self.target_system,  # target_system
                                                self.target_component,
                                                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, # command
                                                0, # confirmation
                                                0, # param1 (1 to indicate disarm)
                                                0, # param2  (all other params meaningless)
                                                0, 0, 0, 0, 0) # param7
            return
            return
            
        if m.returnkey.startswith('# '):
            cmd = m.returnkey[2:]
            if m.handler is not None:
                if m.handler_result is None:
                    return
                cmd += m.handler_result
            self.mpstate.functions.process_stdin(cmd)
        if m.returnkey == 'menuSettings':
            wxsettings.WXSettings(self.settings)

    def set_mode(self, new_mode):
        mode_mapping = self.master.mode_mapping()
        if new_mode not in mode_mapping:
            print('Unknown mode %s: ' % new_mode)
            return
        modenum = mode_mapping[new_mode]
        self.master.set_mode(modenum)
            
    def estimated_time_remaining(self, lat, lon, wpnum, speed):
        '''estimate time remaining in mission in seconds'''
        idx = wpnum
        if wpnum >= self.module('wp').wploader.count():
            return 0
        distance = 0
        done = set()
        while idx < self.module('wp').wploader.count():
            if idx in done:
                break
            done.add(idx)
            w = self.module('wp').wploader.wp(idx)
            if w.command == mavutil.mavlink.MAV_CMD_DO_JUMP:
                idx = int(w.param1)
                continue
            idx += 1
            if (w.x != 0 or w.y != 0) and w.command in [mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                                                        mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM,
                                                        mavutil.mavlink.MAV_CMD_NAV_LOITER_TURNS,
                                                        mavutil.mavlink.MAV_CMD_NAV_LOITER_TIME,
                                                        mavutil.mavlink.MAV_CMD_NAV_LAND,
                                                        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF]:
                distance += mp_util.gps_distance(lat, lon, w.x, w.y)
                lat = w.x
                lon = w.y
                if w.command == mavutil.mavlink.MAV_CMD_NAV_LAND:
                    break
        return distance / speed



    def mavlink_packet(self, msg):
        '''handle an incoming mavlink packet'''
        type = msg.get_type()
        bg = 'white' # default
        fg = 'black' # default
        master = self.master
        # add some status fields
        if type in [ 'GPS_RAW', 'GPS_RAW_INT' ]:    # GPS
            if type == "GPS_RAW":
                num_sats1 = master.field('GPS_STATUS', 'satellites_visible', 0)
            else:
                num_sats1 = msg.satellites_visible
            num_sats2 = master.field('GPS2_RAW', 'satellites_visible', -1)
            if num_sats2 == -1:
                sats_string = "%u" % num_sats1
            else:
                sats_string = "%u/%u" % (num_sats1, num_sats2)
            if ((msg.fix_type >= 3 and master.mavlink10()) or
                (msg.fix_type == 2 and not master.mavlink10())):
                if (msg.fix_type >= 4):
                    fix_type = "%u" % msg.fix_type
                else:
                    fix_type = ""
                self.ERS_console.set_status('GPS', 'GPS: OK%s (%s)' % (fix_type, sats_string), bg='green')
            else:
                self.ERS_console.set_status('GPS', 'GPS: %u (%s)' % (msg.fix_type, sats_string), bg='red')
            if master.mavlink10():
                gps_heading = int(self.mpstate.status.msgs['GPS_RAW_INT'].cog * 0.01)
            else:
                gps_heading = self.mpstate.status.msgs['GPS_RAW'].hdg
            self.ERS_console.set_status('Heading', 'Hdg: %s/%u' % (master.field('VFR_HUD', 'heading', '-'), gps_heading))
            self.ERS_console.set_status('HAcc', 'HAcc: %.1f' % msg.h_acc)
        elif type == 'VFR_HUD':                     # HUD
            if master.mavlink10():
                alt = master.field('GPS_RAW_INT', 'alt', 0) / 1.0e3
            else:
                alt = master.field('GPS_RAW', 'alt', 0)
            home = self.module('wp').get_home()
            if home is not None:
                home_lat = home.x
                home_lng = home.y
            else:
                home_lat = None
                home_lng = None
            lat = master.field('GLOBAL_POSITION_INT', 'lat', 0) * 1.0e-7
            lng = master.field('GLOBAL_POSITION_INT', 'lon', 0) * 1.0e-7
            rel_alt = master.field('GLOBAL_POSITION_INT', 'relative_alt', 0) * 1.0e-3
            agl_alt = None
            if self.settings.basealt != 0:
                agl_alt = self.ERS_console.ElevationMap.GetElevation(lat, lng)
                if agl_alt is not None:
                    agl_alt = self.settings.basealt - agl_alt
            else:
                try:
                    agl_alt_home = self.ERS_console.ElevationMap.GetElevation(home_lat, home_lng)
                except Exception as ex:
                    print(ex)
                    agl_alt_home = None
                if agl_alt_home is not None:
                    agl_alt = self.ERS_console.ElevationMap.GetElevation(lat, lng)
                if agl_alt is not None:
                    agl_alt = agl_alt_home - agl_alt
            if agl_alt is not None:
                agl_alt += rel_alt
                vehicle_agl = master.field('TERRAIN_REPORT', 'current_height', None)
                if vehicle_agl is None:
                    vehicle_agl = '---'
                else:
                    vehicle_agl = self.height_string(vehicle_agl)
                self.ERS_console.set_status('AGL', 'AGL: %s/%s' % (self.height_string(agl_alt), vehicle_agl))
            self.ERS_console.set_status('Alt', 'Alt: %s' % self.height_string(rel_alt))
            #self.ERS_console.set_status('AirSpeed', 'AirSpeed %s' % self.speed_string(msg.airspeed))
            self.ERS_console.set_status('GPSSpeed', 'GPSSpeed: %s' % self.speed_string(msg.groundspeed))
            self.ERS_console.set_status('Thr', 'Thr %u %% %u' % (msg.throttle, master.field('SERVO_OUTPUT_RAW', 'servo3_raw', None)))
            t = time.localtime(msg._timestamp)
            flying = False
            if self.mpstate.vehicle_type == 'copter':
                flying = self.master.motors_armed()
            else:
                flying = msg.groundspeed > 1
            if flying and not self.in_air:
                self.in_air = True
                self.start_time = time.mktime(t)
            elif flying and self.in_air:
                self.total_time = time.mktime(t) - self.start_time
                self.ERS_console.set_status('FlightTime', 'FlightTime %u:%02u' % (int(self.total_time)/60, int(self.total_time)%60))
            elif not flying and self.in_air:
                self.in_air = False
                self.total_time = time.mktime(t) - self.start_time
                self.ERS_console.set_status('FlightTime', 'FlightTime %u:%02u' % (int(self.total_time)/60, int(self.total_time)%60))
        elif type == 'ATTITUDE':                # ATTITUDE
            self.ERS_console.set_status('Roll', 'Roll: %u' % math.degrees(msg.roll))
            self.ERS_console.set_status('Pitch', 'Pitch: %u' % math.degrees(msg.pitch))
        elif type in ['SYS_STATUS']:            # SYS STATUS
            sensors = { 'AS'   : mavutil.mavlink.MAV_SYS_STATUS_SENSOR_DIFFERENTIAL_PRESSURE,
                        'MAG'  : mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_MAG,
                        'INS'  : mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_ACCEL | mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_GYRO,
                        'AHRS' : mavutil.mavlink.MAV_SYS_STATUS_AHRS,
                        'RC'   : mavutil.mavlink.MAV_SYS_STATUS_SENSOR_RC_RECEIVER,
                        'TERR' : mavutil.mavlink.MAV_SYS_STATUS_TERRAIN,
                        'RNG'  : mavutil.mavlink.MAV_SYS_STATUS_SENSOR_LASER_POSITION,
                        'LOG'  : mavutil.mavlink.MAV_SYS_STATUS_LOGGING,
            }
            announce = [ 'RC' ]
            for s in sensors.keys():
                fg='black'
                bg='white'
                bits = sensors[s]
                present = ((msg.onboard_control_sensors_present & bits) == bits)
                enabled = ((msg.onboard_control_sensors_enabled & bits) == bits)
                healthy = ((msg.onboard_control_sensors_health & bits) == bits)
                if not present:
                    fg = 'black'
                elif not enabled:
                    fg = 'grey'
                elif not healthy:
                    bg = 'red'
                else:
                    bg = 'green'
                # for terrain show yellow if still loading
                if s == 'TERR' and fg == 'green' and master.field('TERRAIN_REPORT', 'pending', 0) != 0:
                    fg = 'yellow'
                self.ERS_console.set_status(s, s, fg=fg, bg=bg)
            for s in announce:
                bits = sensors[s]
                enabled = ((msg.onboard_control_sensors_enabled & bits) == bits)
                healthy = ((msg.onboard_control_sensors_health & bits) == bits)
                was_healthy = ((self.last_sys_status_health & bits) == bits)
                if enabled and not healthy and was_healthy:
                    self.say("%s fail" % s)
            self.last_sys_status_health = msg.onboard_control_sensors_health

        elif type == 'WIND':                 # WIND   
            self.ERS_console.set_status('Wind', 'Wind: %u/%.2f' % (msg.direction, msg.speed))

        elif type == 'EKF_STATUS_REPORT':   # EKF STATUS
            highest = 0.0
            vars = ['velocity_variance',
                    'pos_horiz_variance',
                    'pos_vert_variance',
                    'compass_variance',
                    'terrain_alt_variance']
            for var in vars:
                v = getattr(msg, var, 0)
                highest = max(v, highest)
            if highest >= 1.0:
                bg = 'red'
            elif highest >= 0.5:
                bg = 'yellow'
            else:
                bg = 'green'
            self.ERS_console.set_status('EKF', 'EKF', fg=fg, bg=bg)

        elif type == 'HWSTATUS':            # HW STATUS
            if msg.Vcc >= 4600 and msg.Vcc <= 5300:
                fg = 'green'
            else:
                fg = 'red'
            self.ERS_console.set_status('Vcc', 'Vcc: %.2f' % (msg.Vcc * 0.001), fg=fg)
        elif type == 'POWER_STATUS':        # POWER STATUS
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_CHANGED:
                fg = 'red'
            else:
                fg = 'green'
            status = 'PWR:'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_USB_CONNECTED:
                status += 'U'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_BRICK_VALID:
                status += 'B'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_SERVO_VALID:
                status += 'S'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_PERIPH_OVERCURRENT:
                status += 'O1'
            if msg.flags & mavutil.mavlink.MAV_POWER_STATUS_PERIPH_HIPOWER_OVERCURRENT:
                status += 'O2'
            self.ERS_console.set_status('PWR', status, fg=fg)
            self.ERS_console.set_status('Srv', 'Srv: %.2f' % (msg.Vservo*0.001), fg='green')
        elif type in ['RADIO', 'RADIO_STATUS']:# RADIO
            if msg.rssi < msg.noise+10 or msg.remrssi < msg.remnoise+10:
                bg = 'red'
            elif msg.rssi < msg.noise+30 or msg.remrssi < msg.remnoise+30:
                bg = 'yellow'
            else:
                bg = 'white'
            self.ERS_console.set_status('Radio', 'Radio: %u/%u %u/%u' % (msg.rssi, msg.noise, msg.remrssi, msg.remnoise), fg=fg, bg=bg)
        elif type == 'HEARTBEAT':           # HEARTBEAT - MODE and ARM
            fmode = master.flightmode
            if self.settings.vehicle_name:
                fmode = self.settings.vehicle_name + ':' + fmode
            self.ERS_console.set_status('Mode', '%s' % fmode, fg='blue')
            
            armstring = 'UNKNOWN'
            if self.master.motors_armed():
                arm_colour = 'green'
                armstring = 'ARM'
            else:
                arm_colour = 'red'
                armstring = 'DISARM'
            # add safety switch state
            if 'SYS_STATUS' in self.mpstate.status.msgs:
                if (self.mpstate.status.msgs['SYS_STATUS'].onboard_control_sensors_enabled & mavutil.mavlink.MAV_SYS_STATUS_SENSOR_MOTOR_OUTPUTS) == 0:
                    armstring += '(SAFE)'
            self.ERS_console.set_status('ARM', armstring, bg=arm_colour)
            if self.max_link_num != len(self.mpstate.mav_master):
                for i in range(self.max_link_num):
                    self.ERS_console.set_status('Link%u'%(i+1), '', row=1)
                self.max_link_num = len(self.mpstate.mav_master)
            for m in self.mpstate.mav_master:
                linkdelay = (self.mpstate.status.highest_msec - m.highest_msec)*1.0e-3
                linkline = "Link %s: " % (self.link_label(m))
                #fg = 'dark green'
                if m.linkerror:
                    linkline += "down"
                    bg = 'red'
                else:
                    packets_rcvd_percentage = 100
                    if (m.mav_count+m.mav_loss) != 0: #avoid divide-by-zero
                        packets_rcvd_percentage = (100.0 * m.mav_count) / (m.mav_count + m.mav_loss)

                    linkbits = ["%u pkts" % m.mav_count,
                                "%u lost" % m.mav_loss,
                                "\n%.2fs delay" % linkdelay,
                    ]
                    try:
                        if m.mav.signing.sig_count:
                            # other end is sending us signed packets
                            if not m.mav.signing.secret_key:
                                # we've received signed packets but
                                # can't verify them
                                bg = 'yellow'
                                linkbits.append("!KEY")
                            elif not m.mav.signing.sign_outgoing:
                                # we've received signed packets but aren't
                                # signing outselves; this can lead to hairloss
                                bg = 'yellow'
                                linkbits.append("!SIGNING")
                            if m.mav.signing.badsig_count:
                                bg = 'yellow'
                                linkbits.append("%u badsigs" % m.mav.signing.badsig_count)
                    except AttributeError as e:
                        # mav.signing.sig_count probably doesn't exist
                        pass

                    linkline += "OK {rcv_pct:.1f}%\n({bits})".format(
                        rcv_pct=packets_rcvd_percentage,
                        bits=", ".join(linkbits))

                    if linkdelay > 1 and bg == 'white':
                        bg = 'yellow'

                self.ERS_console.set_status('Link%u'%m.linknum, linkline, row=1, fg=fg, bg=bg)
        elif type in ['WAYPOINT_CURRENT', 'MISSION_CURRENT']:
            wpmax = self.module('wp').wploader.count()
            if wpmax > 0:
                wpmax = "/%u" % wpmax
            else:
                wpmax = ""
            self.ERS_console.set_status('WP', 'WP: %u%s' % (msg.seq, wpmax))
            lat = master.field('GLOBAL_POSITION_INT', 'lat', 0) * 1.0e-7
            lng = master.field('GLOBAL_POSITION_INT', 'lon', 0) * 1.0e-7
            if lat != 0 and lng != 0:
                airspeed = master.field('VFR_HUD', 'airspeed', 30)
                if abs(airspeed - self.speed) > 5:
                    self.speed = airspeed
                else:
                    self.speed = 0.98*self.speed + 0.02*airspeed
                self.speed = max(1, self.speed)
                time_remaining = int(self.estimated_time_remaining(lat, lng, msg.seq, self.speed))
                self.ERS_console.set_status('ETR', 'ETR: %u:%02u' % (time_remaining/60, time_remaining%60))

        elif type == 'NAV_CONTROLLER_OUTPUT':
            self.ERS_console.set_status('WPDist', 'Distance %s' % self.dist_string(msg.wp_dist))
            self.ERS_console.set_status('WPBearing', 'Bearing %u' % msg.target_bearing)
            if msg.alt_error > 0:
                alt_error_sign = "L"
            else:
                alt_error_sign = "H"
            if msg.aspd_error > 0:
                aspd_error_sign = "L"
            else:
                aspd_error_sign = "H"
            if math.isnan(msg.alt_error):
                alt_error = "NaN"
            else:
                alt_error = "%d%s" % (msg.alt_error, alt_error_sign)
            #self.ERS_console.set_status('AltError', 'AltError %s' % alt_error)
            #self.ERS_console.set_status('AspdError', 'AspdError %.1f%s' % (msg.aspd_error*0.01, aspd_error_sign))
            self.ERS_console.set_status('Xtrack', 'Xtrack: %.1f' % msg.xtrack_error)
        elif type == 'SERVO_OUTPUT_RAW':
            steer_servo=msg.servo4_raw
            self.ERS_console.set_status('Steer', 'Steer: %u' % steer_servo)
            
            kill_servo=int(msg.servo7_raw) # ERC_INGITION
            self.ERS_console.set_status('KillPWM', '%u' % kill_servo)
            
            starter_servo=int(msg.servo8_raw) # ERC_STARTER
            self.ERS_console.set_status('StartPWM', '%u' % starter_servo)

            if (kill_servo == ers_util.EPWM_K_KILL):
                self.ERS_console.set_status('Kill', 'KILL')
            elif (kill_servo == ers_util.EPWM_K_RUN & starter_servo == ers_util.EPWM_K_RUN):
                self.ERS_console.set_status('Kill', 'START')
            elif (kill_servo == ers_util.EPWM_K_RUN):
                self.ERS_console.set_status('Kill', 'RUN')

        elif type == 'COMMAND_ACK':
            ack_cmd=msg.command
            ack_stat=msg.result
            if (ack_stat == 0):
                self.ERS_console.set_status('ACK', '%u' % ack_cmd)
            
def init(mpstate):
    '''initialise module'''
    return ERSModule(mpstate)
