#!/usr/bin/python
import os
import sys
import subprocess
import re
import ipaddress

def isprivate(ipstr):
    """Check if the given IP is from a private IP range."""
    if (ipstr == None or ipstr == ''):
       return False;
       
    return ipaddress.ip_address(unicode(ipstr)).is_private

def localip(pcapfile, vpnaddresses=[]):
    """
    Try to guess the device IP in the given pcap using bunch of 
    heuristics:

    * It's one of the VPN addresses (non-hostview captures)
    * Hostview capture:
      - assume that a private IP is the local IP when dst is public
      - assume that src/dst port < 1024 is the server side
      - assume that dns req/res src/dst is the local host
    
    Returns None if we cannot determine the local IP.
    """
    if (pcapfile == None):
        return None

    # read first pkt to/from a known server port from the pcap
    cmd = ['tshark',
           '-Y','tcp.port == 80 or tcp.port == 443 or tcp.port == 53 or tcp.port == 110 or tcp.port == 993 or tcp.port == 123',
           '-c','1',
           '-T','fields',
           '-e','frame.time_epoch',
           '-e','ip.src',
           '-e','ip.dst',
           '-e','tcp.srcport',
           '-e','tcp.dstport',
           '-E','separator=;', 
           '-r',pcapfile]
    
    out = None
    try:
        out = subprocess.check_output(cmd)
    except:
        pass
    
    if (out != None and len(out) > 0):
        (ts,srcip,dstip,tcpsrc,tcpdst) = out.split(';')

        if (srcip in vpnaddresses):
            return srcip

        if (dstip in vpnaddresses):
            return dstip

        if (isprivate(srcip) and not isprivate(dstip)):
            return srcip

        if (isprivate(dstip) and not isprivate(srcip)):
            return dstip

        if (tcpsrc!=None and tcpsrc.isdigit() and int(tcpsrc) < 1024):
            return dstip

        if (tcpdst!=None and tcpdst.isdigit() and int(tcpdst) < 1024):
            return srcip

    # same with UDP, assume that the side with 53 is not the localhost
    cmd = ['tshark',
           '-Y','udp.port == 53',
           '-c','1',
           '-T','fields',
           '-e','frame.time_epoch',
           '-e','ip.src',
           '-e','ip.dst',
           '-e','udp.srcport',
           '-e','udp.dstport',
           '-E','separator=;', 
           '-r',pcapfile]
    
    out = None
    try:
        out = subprocess.check_output(cmd)
    except:
        pass
    
    if (out != None and len(out) > 0):
        (ts,srcip,dstip,tcpsrc,tcpdst) = out.split(';')

        if (srcip in vpnaddresses):
            return srcip

        if (dstip in vpnaddresses):
            return dstip

        if (isprivate(srcip) and not isprivate(dstip)):
            return srcip

        if (isprivate(dstip) and not isprivate(srcip)):
            return dstip

        if (tcpsrc != None and tcpsrc.isdigit() and int(tcpsrc) == 53):
            return dstip

        if (tcpdst != None and tcpdst.isdigit() and int(tcpdst) == 53):
            return srcip

    # Fallback: try to find any DNS req (assume always outgoing)
    out = None
    cmd = ['tshark','-2','-c','1',
           '-T','fields',
           '-e','ip.src',
           '-R','dns.flags.response eq 0', # is a req
           '-r',pcapfile]
    try:
        out = subprocess.check_output(cmd)
    except:
        pass

    if (out != None and len(out) > 0):
        return out
    
    # Fallback2: try to find any DNS resp (assume always incoming)
    out = None
    cmd = ['tshark','-2','-c','1',
           '-T','fields',
           '-e','ip.dst',
           '-R','dns.flags.response eq 1', # is a resp
           '-r',pcapfile]            
    try:
        out = subprocess.check_output(cmd)
    except:
        pass

    if (out != None and len(out) > 0):
        return out

    # read any pkt
    cmd = ['tshark',
           '-c','1',
           '-T','fields',
           '-e','frame.time_epoch',
           '-e','ip.src',
           '-e','ip.dst',
           '-e','tcp.srcport',
           '-e','tcp.dstport',
           '-E','separator=;', 
           '-r',pcapfile]
    
    out = None
    try:
        out = subprocess.check_output(cmd)
    except:
        pass
    
    if (out != None and len(out) > 0):
        (ts,srcip,dstip,tcpsrc,tcpdst) = out.split(';')

        if (srcip in vpnaddresses):
            return srcip

        elif (dstip in vpnaddresses):
            return dstip

        elif (isprivate(srcip) and not isprivate(dstip)):
            return srcip

        elif (isprivate(dstip) and not isprivate(srcip)):
            return dstip

        elif (tcpsrc!=None and tcpsrc.isdigit() and int(tcpsrc) < 1024):
            return dstip

        elif (tcpdst!=None and tcpdst.isdigit() and int(tcpdst) < 1024):
            return srcip

    return None
