# dbus-prowl
a small python script to watch for desktop notifications (org.freedesktop.Notifications) and forward them to prowl (http://www.prowlapp.com)

I got tired of having to walk into my office to see if HandBrake was done encoding.  

The HandBrake GUI on linux doesn't offer a "send file when done" option like the Mac and Windows versions do, but it will post a desktop notification when the queue is complete.  Since desktop notifications are published on dbus, I figured "how hard could it be to watch for notifications and forward them to Prowl"?

After trying a couple python modules to talk to dbus (python-dbus, pydbus) and finding none of them suitable, I gave up and made the handful of dbus calls directly through the python gio and glib bindings.

```
$ dbus-prowl.py --help
usage: dbus-prowl.py [-h] [-n] [-d] [-a APPLICATION] [-k APIKEY]
                     [--update-defaults] [--set-defaults] [--print-config]

Forward desktop notifications to Prowl.

optional arguments:
  -h, --help            show this help message and exit
  -n, --simulate        dry-run, no actual prowl api calls
  -d, --debug           emit debug level spew
  -a APPLICATION, --application APPLICATION
                        forward notifications from application
  -k APIKEY, --apikey APIKEY
                        Prowl API key - create at
                        https://www.prowlapp.com/api_settings.php
  --update-defaults     update api key if provided and merge app list into
                        defaults
  --set-defaults        store provided api key and application list as
                        defaults
  --print-config        print configured api key and application list

$ dbus-prowl.py -k <apikey> -a HandBrake --set-defaults
2017-12-05 13:24:54,768 dbus-prowl INFO not forwarding notification from application 'notify-send'
2017-12-05 13:39:37,708 dbus-prowl INFO forwarding notification from application 'HandBrake'

<ctrl-c>

$ dbus-prowl.py --print-config
configuration:
api key: <apikey>
notifications will be forwarded for the following applications:
    handbrake

```
