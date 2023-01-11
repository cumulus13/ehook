#!/usr/bin/env python

from __future__ import print_function

from make_colors import make_colors
from xnotify import notify
import os, sys
import socket
from configset import configset
import syslogx
import datetime
import re
import traceback
from pydebugger.debug import debug

PID = os.getpid()

class ehook:#(object):
    
    CONFIGNAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ehook.ini')
    CONFIG = configset(CONFIGNAME)

    def __init__(self, exc_type, exc_value, tb, **kwargs):

        #local_vars = {}
        #super(ehook, self)
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.tb = tb
        data, data_color, raw_data, raw_data_color = self.tracert()
        
        app = "ehook"
        title = "Traceback"
        event = 'Error'
        icon = list(filter(lambda k: os.path.isfile(k), [os.path.splitext(os.path.realpath(__file__))[0] + "." + i for  i in ['png', 'jpg']] + [os.path.join(os.path.dirname(os.path.realpath(__file__)), 'traceback') + "." + i for  i in ['png', 'jpg']])) 
        #print("icon:", icon)
        kwargs.update({'app': app,})
        kwargs.update({'title': title,})
        kwargs.update({'event': event,})
        kwargs.update({'sticky': True,})
        if icon: kwargs.update({'icon': icon[0],})
        #icon = os.path.join(os.path.dirname(os.path.realpath(__file__)), icon)
        
        syslog_server = re.split("\n|\t|,", self.CONFIG.get_config('syslog', 'host')) or kwargs.get('syslog_server')
        syslog_server = [i.strip() for i in syslog_server]
        debug(syslog_server = syslog_server)
        if isinstance(syslog_server, list):
            for i in syslog_server:
                self.debug_server_client(data, data_color, i.split(":")[0])
        else:
            self.debug_server_client(data, data_color, syslog_server)
        kwargs.update({'syslog_server': syslog_server,})
        notify.send(message_color = data_color, message = "\n".join(raw_data[1:]), **kwargs)
    
    def sent_to_syslog(self, message, severity=None, facility=None, host = None, port = None):
        
        severity = severity or 3
        facility = facility or 3
        host = host or self.CONFIG.get_config('syslog', 'host') or '127.0.0.1'
        port = port or self.CONFIG.get_config('syslog', 'port') or 514
        if "," in host:
            host = [i.strip() for i in host.split(",")]
        else:
            if not isinstance(host, list): host = [host]
        if hasattr(message, 'decode'):
            message = message.decode('utf-8')
        for i in host:
            if ":" in i:
                HOST, PORT = str(i).split(":")
                HOST = HOST.strip()
                PORT = PORT.strip()
                PORT = PORT or 514
                print("sent to %s:%s" % (HOST, str(PORT)))
                syslogx.syslog(message, severity, facility, HOST, int(PORT))
            else:
                syslogx.syslog(message, severity, facility, i, port)
                
    
    def debug_server_client(self, msg, msg_color = None, host = None, port = None):
        
        dtime = make_colors(datetime.datetime.strftime(datetime.datetime.now(), '%Y:%m:%d'), 'white', 'red') + \
        make_colors('~', 'white') + \
        make_colors(datetime.datetime.strftime(datetime.datetime.now(), '%H:%M:%S'), 'white', 'green') + \
        make_colors(datetime.datetime.strftime(datetime.datetime.now(), '%f'), 'white', 'magenta') + \
            "[%s]" % PID
        
        if sys.version_info.major == 3:
            msg = msg.encode('utf-8')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        host = host or self.CONFIG.get_config('server', 'host') or '127.0.0.1'
        port = port or self.CONFIG.get_config('server', 'port') or 50000
        if not host:
            try:
                if sys.version_info.major == 3:
                    msg_color = bytes(dtime + " " + msg_color, encoding = 'utf-8')
                else:
                    msg_color = dtime + " " + msg_color
                s.sendto((msg_color or msg), (host, port))
            except:
                traceback.format_exc()
                print(msg)
                self.sent_to_syslog(msg)
            s.close()        
            #return False
        if "," in host:
            host = [i.strip() for i in host.split(",")]
        else:
            host = [host]
        for i in host:
            if ":" in i:
                host1, port1 = str(i).strip().split(":")
                port1 = int(port1.strip()) or port
                host1 = host1.strip()
                try:
                    if sys.version_info.major == 3:
                        msg_color = bytes(dtime + " " + msg_color, encoding = 'utf-8')
                    else:
                        msg_color = dtime + " " + msg_color
                    s.sendto((msg_color or msg), (host1, port1))
                except:
                    traceback.format_exc()
                    print(msg)
                    self.sent_to_syslog(msg)
                s.close()                
                #print "%s:%s 0" % (host, str(port))
                break
            else:
                host = i.strip()
                #print "%s:%s 1" % (host, str(port))
                if sys.version_info.major == 3:
                    msg_color = bytes(dtime + " " + msg_color, encoding = 'utf-8')
                else:
                    msg_color = dtime + " " + msg_color
                s.sendto((msg_color or msg), (host, port))
                s.close()
                break

    def tracert(self):
        trace = ["Traceback: "]
        trace_color = []
        while self.tb:
            filename = self.tb.tb_frame.f_code.co_filename
            name = self.tb.tb_frame.f_code.co_name
            line_no = self.tb.tb_lineno
            data_color = make_colors("Traceback:", 'b', 'y') + " " + \
                make_colors(self.exc_type.__name__, 'lw', 'r') + " (" + \
                make_colors(self.exc_value, 'lw', 'm') + "), File " + \
                make_colors(filename, 'b', 'lg') + ", line " + \
                make_colors(line_no, 'lw', 'bl') + ", in " + \
                make_colors(name, 'b', 'lc')
            print(data_color)
            trace_color.append(data_color)
            data = str(self.exc_type.__name__) + ": " + str(self.exc_value) + "), File " + filename + ", line " + str(line_no) + ", in " + name
            trace.append(data)
            #print(f"File {filename} line {line_no}, in {name}")

            #local_vars = tb.tb_frame.f_locals
            #print(f"{exc_type.__name__}, Message: {exc_value}")
            self.tb = self.tb.tb_next
        #print(f"Local variables in top frame: {local_vars}")
        return "\n".join(trace), "\n".join(trace_color), trace, trace_color

if __name__ == '__main__':
    print(make_colors("run testing ...", 'lw', 'r'))
    import sys
    sys.excepthook = ehook
    #print(sys.argv[1])
    def do_stuff():
        # ... do something that raises exception
        raise ValueError("Some error message")
    
    do_stuff()
