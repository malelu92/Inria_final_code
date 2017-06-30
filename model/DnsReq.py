#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from Base import Base
from Device import Device
from User import User

class DnsReq(Base):
    __tablename__ = 'dnsreqs'
    
    id = Column(Integer, primary_key=True)
    devid = Column(Integer, ForeignKey('devices.id'), nullable=False)

    ts = Column(DateTime, nullable=False, index=True)
    
    # 5-tuple (as in the corresponding DNS response packet, 
    # hence, src is the DNS server and dst is the device)
    srcip = Column(String(128), nullable=False)
    dstip = Column(String(128), nullable=False)
    proto = Column(Integer, nullable=False) # basically almost uniquely 17 (udp)
    srcport = Column(Integer, nullable=False) # basically always 53
    dstport = Column(Integer, nullable=False)

    # SHA hash of the 5-tuple for easier flow based indexing
    flowid = Column(String(64), nullable=False, index=True)

    # DNS query
    query = Column(String(512))
    query_type = Column(Integer)

    query_tld = Column(String(8))
    query_domain = Column(String(256))

    # each response can contain multiple answers to the query
    ans_type = Column(ARRAY(Integer))
    ans_addr = Column(ARRAY(String(128))) # ip
    ans_name = Column(ARRAY(String(512)))
    ans_ttl = Column(ARRAY(Integer))

    # Filtering: query domain found on easylist (AdBlock)
    matches_easylist = Column(Boolean)

    # Filtering: query domain found on easyprivacy (AdBlock trackers etc)
    matches_easyprivacy = Column(Boolean)

    # Filtering: some manually identified noisy service URLs (e.g. apple
    # update, Windows update etc)
    matches_blacklist = Column(Boolean)

    # matches_* == False
    user_req = Column(Boolean)

    # there's a http req that follows this DNS req in less than 1 minute
    duplicate = Column(Boolean)    
    
    def __repr__(self):
        return '<DnsReq(server=%s, query=%s, ans=%s, filter=%s)>' % (self.dstip, self.query, ",".join(self.ans_addr), not self.user_req)

if __name__ == "__main__":
    """
    Create (or recreate if exists).
    """
    import os
    import sys
    import csv
    import datetime
    import hashlib
    import subprocess
    import glob
    
    from sqlalchemy import create_engine    
    from sqlalchemy.orm import sessionmaker

    def process(dbs, d):
        """Process single device."""
        for pcap in glob.glob(d.netdata+'/*pcap*'):  
            print 'process',pcap
            
            # extract all DNS responses
            cmd = ['tshark','-q','-2','-T','fields',
                   '-e','frame.time_epoch',
                   '-e','ip.src',
                   '-e','ip.dst',
                   '-e','ip.proto',
                   '-e','udp.srcport',
                   '-e','udp.dstport',
                   '-e','tcp.srcport',
                   '-e','tcp.dstport',
                   '-e','dns.qry.name',
                   '-e','dns.qry.type',
                   '-e','dns.resp.type',
                   '-e','dns.resp.addr',
                   '-e','dns.resp.name',
                   '-e','dns.resp.ttl',
                   '-E','separator=;',
                   '-R',"dns.flags.response eq 1",
                   '-r',str(pcap)]

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            for line in iter(proc.stdout.readline, ''):                
                row = line.strip().split(';')
                
                ts = datetime.datetime.fromtimestamp(float(row[0]))
                proto = None
                srcport = 0
                dstport = 0
                if (row[3] != ''):
                    proto = int(row[3].split(',')[0])

                if (proto == 17): # udp
                    srcport = int(row[4].split(',')[0]) if (row[4]!='') else 0
                    dstport = int(row[5].split(',')[0]) if (row[5]!='') else 0
                elif (proto == 6): # tcp
                    srcport = int(row[6].split(',')[0]) if (row[6]!='') else 0
                    dstport = int(row[7].split(',')[0]) if (row[7]!='') else 0
                else:
                    continue
                if (srcport == 0 or dstport == 0):
                    continue
                if (row[1] == None or row[1] == '' or row[2] == None or row[2] == ''):
                    continue

                # flowid
                m = hashlib.sha224()
                m.update(row[1])
                m.update(row[2])
                m.update(str(proto))
                m.update(str(srcport))
                m.update(str(dstport))

                r = DnsReq(devid=d.id,
                           ts=ts,
                           srcip=row[1],
                           dstip=row[2],
                           proto=proto,
                           srcport=srcport,
                           dstport=dstport,
                           flowid=m.hexdigest(),
                           query=row[8],
                           query_type=int(row[9],16) if not row[9] == '' else None,
                           ans_type=[int(s,16) for s in row[10].split(',') if s!=''],
                           ans_addr=row[11].split(','),
                           ans_name=row[12].split(','),
                           ans_ttl=[int(s) for s in row[13].split(',') if s!=''])
                print str(r)
                dbs.add(r)
            dbs.commit()                           

    db = sys.argv[1]

    engine = create_engine(db, echo=False)
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine) 
    dbs = Session()
    if (len(sys.argv)==3):
        print 'Add device %s to table "dnsreqs" in %s' % (sys.argv[2], db)
        
        d = dbs.query(Device).filter(Device.login==sys.argv[2]).one()
        print 'handle',str(d)
        process(dbs,d)
    else:
        print 'Creating table "dnsreqs" in %s' % db

        # make sure the table is empty
        DnsReq.__table__.drop(engine, checkfirst=True) # drop if exists
        DnsReq.__table__.create(engine)

        for d in dbs.query(Device).filter(login=login):                        
            print 'handle',str(d)
            process(dbs,d)
    dbs.close()

        
        
    
