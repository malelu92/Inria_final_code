#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime
from Base import Base
from Device import Device
from User import User

class DeviceTraffic(Base):
    """
    Total IP traffic in/out from the device.
    """
    __tablename__ = 'devicetraffic'
    
    id = Column(Integer, primary_key=True)
    devid = Column(Integer, ForeignKey('devices.id'), nullable=False)

    # table will have an entry 1 / second
    ts = Column(DateTime, nullable=False, index=True)

    packets_in = Column(Integer)
    bytes_in = Column(Integer)
    packets_out = Column(Integer)
    bytes_out = Column(Integer)

    def __repr__(self):
        return '<DeviceTraffic (ts=%s, pkt_in=%s, pkt_out=%s)>' % (self.ts, self.packets_in, self.packets_out)

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
    import utils
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine    
    from sqlalchemy.orm import sessionmaker

    def process(dbs, d):
        for pcap in glob.glob(d.netdata+'/*pcap*'):
            # figure out IP (to do uplink/downlink correctly)
            deviceip = utils.localip(pcap, d.addresses)
            if (deviceip == None):
                print str(d),pcap,'could not figure out device IP'
                continue

            # read first pkt timestamp from the pcap
            cmd = ['tshark','-c','1',
                   '-T','fields',
                   '-e','frame.time_epoch',
                   '-r',pcap]
            
            try:
                out = subprocess.check_output(cmd)
            except:
                continue
            if (out == None or len(out) <= 0):
                continue

            starttime = datetime.fromtimestamp(float(out.strip()))
            starttime -= timedelta(microseconds=starttime.microsecond)
            print 'first pkt',starttime,deviceip
            
            # stats: pkts, bytes
            stats = []
            for agg in ['COUNT','SUM']:
                # uplink
                stats.append('%s(ip.len)ip.len and ip.src==%s'%(agg,deviceip))
                # downlink
                stats.append('%s(ip.len)ip.len and ip.dst==%s'%(agg,deviceip))

            cmd = ['tshark', '-q',
                   '-z', 'io,stat,1,'+','.join(stats),'-r',str(pcap)]

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            for line in iter(proc.stdout.readline, ''):
                if (line.find('<>')<0):
                    continue # header

                elems = [e.strip() for e in line.strip().split('|')][1:]

                if (int(elems[3])+int(elems[4]) == 0):
                    continue # no pkts

                m = re.match("(\d+).*\d+", elems[0])
                iv = int(m.group(1))
                s = DeviceTraffic(devid=d.id,
                                  ts=starttime+timedelta(seconds=iv),
                                  packets_out=int(elems[3]),
                                  packets_in=int(elems[4]),
                                  bytes_out=int(elems[5]),
                                  bytes_in=int(elems[6]))
                print str(s)
                dbs.add(s)
            dbs.commit() # per pcap

    db = sys.argv[1]
    engine = create_engine(db)
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine) 
    dbs = Session()
    if (len(sys.argv)==3):
        print 'Add device %s to table "devicetraffic" in %s' % (sys.argv[2], db)
        d = dbs.query(Device).filter(Device.login==sys.argv[2]).one()
        # TODO: remove first any existing entries from the table ?
        print 'handle',str(d)
        process(dbs,d)
    else:
        print '(Re)-creating table "devicetraffic" in %s' % db
        DeviceTraffic.__table__.drop(engine, checkfirst=True) # drop if exists
        DeviceTraffic.__table__.create(engine)
        for d in dbs.query(Device).all():
            print 'handle',str(d)
            process(dbs,d)
    dbs.close()
