#!/usr/bin/env python3

import argparse
import configparser
import logging
import requests
import os
import os.path
try:
    from pid import PidFile, PidFileError
except:
    print("pid module not found, required to prevent multiple simultaneous instances.")
    exit(1)
import platform

try:
    from gi.repository import Gio, GLib
except:
    print("python gi (gobject-introspection) module not found, required to monitor dbus.")
    exit(1)

args=None
kProwlAPIBase='https://api.prowlapp.com/publicapi/'
kDbusProwlConfigFile=os.path.expanduser("~/.config/dbus-prowl/config.ini")

logger = logging.getLogger('dbus-prowl')

def is_notification(msg):
    return msg.get_message_type() == Gio.DBusMessageType.METHOD_CALL

def should_forward_notification(msg):
    if "*" in args.application:
        return True
    if msg.get_arg0() and msg.get_arg0().lower() in args.application:
        logger.info("forwarding notification from application '%s'" % msg.get_arg0())
        return True
    logger.info("not forwarding notification from application '%s'" % msg.get_arg0())
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
    if incoming and is_notification(msg) and should_forward_notification(msg):
        forward_notification(msg)
    # the dbus monitor code includes this comment:
    # /* Monitors must not allow libdbus to reply to messages, so we eat
    #  * the message. See bug 1719.
    #  */
    # so we do the same.
    if incoming:
        return Gio.DBusMessage()
    else:
        return msg

def main():
    parser = argparse.ArgumentParser(description="Forward desktop notifications to Prowl.")
    parser.add_argument('-n', '--simulate', action='store_true', default=False,
        help='dry-run, no actual prowl api calls')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
        help='emit debug level spew')
    parser.add_argument('-a', '--application', default=[], action='append',
        help='forward notifications from application')
    parser.add_argument('-k', '--apikey', type=str, default="",
        help='Prowl API key - create at https://www.prowlapp.com/api_settings.php')
    parser.add_argument('--update-defaults', action='store_true',
        help='update api key if provided and merge app list into defaults')
    parser.add_argument('--set-defaults', action='store_true',
        help='store provided api key and application list as defaults')
    parser.add_argument('--print-config', action='store_true',
        help='print configured api key and application list')
    global args; args = parser.parse_args()

    logfmt = '%(asctime)s %(name)s %(levelname)s %(message)s'
    loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(format=logfmt, level=loglevel)
    logger.setLevel(loglevel)

    os.makedirs(os.path.dirname(kDbusProwlConfigFile), exist_ok=True)
    config = configparser.ConfigParser()
    try:
        config.read(kDbusProwlConfigFile)
    except FileNotFoundError:
        pass

    if args.set_defaults:
        if not len(args.apikey):
            raise(ValueError("apikey must be specified to --set-defaults"))
        config['authentication'] = {}
        config['applications'] = {}
    else:
        if not args.apikey and len(config['authentication']['apikey']):
            args.apikey = config['authentication']['apikey']

        for key in config['applications']:
            if key not in args.application and config['applications'][key] == 'forward':
                args.application.append(key)

    if args.update_defaults or args.set_defaults:
        if len(args.apikey):
            config['authentication']['apikey'] = args.apikey
        if len(args.application):
            for app in args.application:
                if app not in config['applications']:
                    config['applications'][app] = 'forward'
        with open(kDbusProwlConfigFile, 'w') as configfile:
            config.write(configfile)
            logger.info("defaults saved...")

    if args.print_config:
        print("configuration:")
        print("api key: " + args.apikey)
        print("notifications will be forwarded for the following applications:")
        for application in args.application:
            print( "    " + application)

    args.application = [x.lower() for x in args.application]
    # get the session bus singleton
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    # add our message filter
    bus.add_filter(msg_flt, None, None)
    # become a bus monitor
    logger.debug("becoming dbus monitor")
    bus.call("org.freedesktop.DBus", "/org/freedesktop/DBus", 
             "org.freedesktop.DBus.Monitoring", "BecomeMonitor",
             GLib.Variant("(asu)", 
                ((["type=method_call,interface=org.freedesktop.Notifications,member=Notify"],0))),
             None,
             Gio.DBusCallFlags.NONE, -1, None)
    logger.debug("entering glib mainloop")
    GLib.MainLoop().run()

if __name__ == '__main__':
    try:
        with PidFile(force_tmpdir=True) as p:
            main()
    except PidFileError:
        logger.error("couldn't create pid/lock file - is another instance already running?")
        exit(1)