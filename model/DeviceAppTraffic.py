#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime
from Base import Base
from Device import Device
from User import User

class DeviceAppTraffic(Base):
    """
    Total app traffic (5-tuple) in/out from the device + pkt size stats.
    """
    __tablename__ = 'deviceapptraffic'
    
    id = Column(Integer, primary_key=True)
    devid = Column(Integer, ForeignKey('devices.id'), nullable=False)

    # table will have an entry 1 / second
    ts = Column(DateTime, nullable=False, index=True)

    # 5-tuple (re-arranged so that src is always the local device IP)
    srcip = Column(String(128), nullable=False)
    dstip = Column(String(128), nullable=False, index=True)
    proto = Column(Integer, nullable=False)
    srcport = Column(Integer, nullable=False)
    dstport = Column(Integer, nullable=False, index=True)

    # SHA hash of the 5-tuple
    flowid = Column(String(64), nullable=False, index=True)

    # basic traffic info
    packets_in = Column(Integer)
    bytes_in = Column(Integer)
    packets_out = Column(Integer)
    bytes_out = Column(Integer)
    
    # service name based on well-known port (dstport)
    service = Column(String(512))

    # from hostview or android logger (TODO)
    appname = Column(String(512))
    
    def __repr__(self):
        return '<DeviceAppTraffic (ts=%s, service="%s", pkt_in=%s, pkt_out=%s)>' % (self.ts, self.service, self.packets_in, self.packets_out)

if __name__ == "__main__":
    """
    Create (or recreate if exists).
    """
    import os
    import sys
    import glob
    import subprocess
    import re
    import ipaddress
    import hashlib
    import utils
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine    
    from sqlalchemy.orm import sessionmaker
    
    WINDOW=10

    def process_pcap(dbs, d, pcap):
        """Process single pcap file"""
        
        # figure out IP (to do uplink/downlink correctly)
        deviceip = utils.localip(pcap, d.addresses)
        print pcap,str(d),deviceip

        if (deviceip == None):
            return
        
        cmd = ['tshark',
               '-Y','ip.addr == %s'%deviceip,
               '-T','fields',
               '-e','frame.time_epoch',
               '-e','ip.src',
               '-e','ip.dst',
               '-e','ip.proto',
               '-e','udp.srcport',
               '-e','udp.dstport',
               '-e','tcp.srcport',
               '-e','tcp.dstport',
               '-e','ip.len',             
               '-E','separator=;',
               '-E','occurrence=l',
               '-r',pcap]
        
        # flowid -> DeviceAppTraffic
        count = 0
        ecount = 0
        pcount = 0
        data = {}
        nextout = None
        
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        for line in iter(proc.stdout.readline, ''):                
            row = line.strip().split(';')
            
            ts = datetime.fromtimestamp(float(row[0]))
            
            if (nextout == None):
                # round to second and the +1
                nextout = ts - timedelta(microseconds=ts.microsecond)
                nextout = nextout + timedelta(seconds=WINDOW)
                
            elif (ts > nextout):
                for obj in data.values():
                    dbs.add(obj)
                data = {} # reset
                nextout = nextout + timedelta(seconds=WINDOW)
                count += 1
                    
            proto = None
            proto = int(row[3]) if row[3]!='' else 0

            srcport = 0
            dstport = 0            
            if (proto == 17): # udp
                srcport = int(row[4]) if row[4]!='' else 0
                dstport = int(row[5]) if row[5]!='' else 0
            elif (proto == 6): # tcp
                srcport = int(row[6]) if row[6]!='' else 0
                dstport = int(row[7]) if row[7]!='' else 0
            else:
                ecount += 1
                continue

            if (srcport == 0 or dstport == 0):
                ecount += 1
                continue

            if (row[1] == None or row[1] == ''):
                ecount += 1
                continue

            if (row[2] == None or row[2] == ''):
                ecount += 1
                continue

            srcip = row[1]
            dstip = row[2]

            # figure out the direction
            direction = None
            if (dstip == deviceip):
                direction = 'downlink'
                # swap, make 'src' always the local IP
                (tmpip,tmpp) = (dstip, dstport)
                dstip = srcip
                dstport = srcport
                srcip = tmpip
                srcport = tmpp
            else:
                direction = 'uplink'

            # flowid
            m = hashlib.sha224()
            m.update(srcip)
            m.update(dstip)
            m.update(str(proto))
            m.update(str(srcport))
            m.update(str(dstport))
            flowid = m.hexdigest()

            pcount += 1
            
            if (not flowid in data):
                sname = None
                try:
                    sname = subprocess.check_output([
                        "/bin/bash",
                        "/home/apietila/work/dataprojects/ucnstudy/src/sname.sh",
                        str(dstport),
                        ('tcp' if proto == 6 else 'udp')])
                    sname = sname.strip()

                except:
                    print 'sname.sh error',sys.exc_info()[0]
                    pass

                data[flowid] = DeviceAppTraffic(devid=d.id,
                                                ts=nextout,
                                                srcip=srcip,
                                                dstip=dstip,
                                                proto=proto,
                                                srcport=srcport,
                                                dstport=dstport,
                                                flowid=flowid,
                                                service=sname,
                                                packets_out=0,
                                                packets_in=0,
                                                bytes_out=0,
                                                bytes_in=0)

            if (direction == 'uplink'):
                data[flowid].packets_out += 1
                data[flowid].bytes_out += long(row[8])
            else:
                data[flowid].packets_in += 1
                data[flowid].bytes_in += long(row[8])

        # flush last reports
        for obj in data.values():
            dbs.add(obj)

        print 'processed',count+1,' seconds','ignored',ecount,'kept',pcount

    def process(dbs, d):
        for pcap in glob.glob(d.netdata+'/*pcap*'):
            if (os.path.getsize(pcap) == 0):
                continue
            process_pcap(dbs, d, pcap)
            dbs.commit()

    # main
    db = sys.argv[1]
    engine = create_engine(db)
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine) 
    dbs = Session()
    if (len(sys.argv)==3):
        print 'Add device %s to table "deviceapptraffic" in %s' % (sys.argv[2], db)
        d = dbs.query(Device).filter(Device.login==sys.argv[2]).one()
        # TODO: remove first any existing entries from the table ?
        print 'handle',str(d)
        process(dbs,d)
    else:
        print '(Re-)creating table "deviceapptraffic" in %s' % db
        DeviceAppTraffic.__table__.drop(engine, checkfirst=True) # drop if exists
        DeviceAppTraffic.__table__.create(engine)
        for d in dbs.query(Device).all():
            print 'handle',str(d)
            process(dbs,d)
    dbs.close()

