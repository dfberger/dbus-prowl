#!/usr/bin/env python3

import argparse
import configparser
import requests
import os
import os.path
import platform

from gi.repository import Gio, GLib

#
# TODO:
# * as "forward all"
# error handling from prowl api
# rate limiting
#


args=None
kProwlAPIBase='https://api.prowlapp.com/publicapi/'
kDbusProwlConfigFile=os.path.expanduser("~/.config/dbus-prowl/config.ini")

def should_forward_notification(msg):
    if len(args.application) == 0:
        return True
    if msg.get_arg0() and msg.get_arg0().lower() in args.application:
        return True
    return False

def forward_notification(msg):
    try:
        application = msg.get_arg0() + "@" + platform.node()
        event = msg.get_body().get_child_value(3).get_string()
        description = msg.get_body().get_child_value(4).get_string()
        if args.simulate:
            print("S: " + application + " : " + notification)
            return
        r = requests.post(kProwlAPIBase+'add', 
            data={'apikey'      :args.apikey,
                  'priority'    :0,
                  'application' :application,
                  'event'       :event,
                  'description' :description},
            timeout=5.0)
    except:
        pass

def msg_flt(bus, msg, incoming, userdata, unknown):
    if args.debug:
        print("incoming: " + str(incoming))
        print("userdata: " + str(userdata))
        print("unknown:  " + str(unknown))
        print(msg.print_(1))
        print("msg.get_arg0: " + str(msg.get_arg0()))
    if should_forward_notification(msg):
        forward_notification(msg)
    if incoming:
        return Gio.DBusMessage()
    else:
        return msg

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Forward desktop notifications to Prowl.")
    parser.add_argument('-n', '--simulate', action='store_true', help='dry-run, no actual prowl api calls')
    parser.add_argument('-d', '--debug', action='store_true', help='emit debug level spew')
    parser.add_argument('-a', '--application', default=[], action='append', 
        help='forward notifications from application')
    parser.add_argument('-k', '--apikey', type=str, help='Prowl API key')
    parser.add_argument('--save', action='store_true', help='persist app list and api key as defaults' )
    args = parser.parse_args()

    os.makedirs(os.path.dirname(kDbusProwlConfigFile), exist_ok=True)
    config = configparser.ConfigParser()
    try:
        config.read(kDbusProwlConfigFile)
        if len(config['authentication']['apikey']) and not args.apikey:
            args.apikey = config['authentication']['apikey']

        for key in config['applications']:
            if config['applications'][key] == 'forward' and key not in args.application:
                args.application.append(key)
    except FileNotFoundError:
        pass

    if args.save:
        if len(args.apikey):
            config['authentication'] = {}
            config['authentication']['apikey'] = args.apikey
        if len(args.application):
            config['applications'] = {} 
            for app in args.application:
                config['applications'][app] = 'forward'
        with open(kDbusProwlConfigFile, 'w') as configfile:
            config.write(configfile)

    args.application = [x.lower() for x in args.application]
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    bus.add_filter(msg_flt, None, None)
    bus.call("org.freedesktop.DBus", "/org/freedesktop/DBus", 
             "org.freedesktop.DBus.Monitoring", "BecomeMonitor",
             GLib.Variant("(asu)", 
                          ((["type=method_call,interface=org.freedesktop.Notifications,member=Notify"],0))),
             None,
             Gio.DBusCallFlags.NONE, -1, None)
    GLib.MainLoop().run()