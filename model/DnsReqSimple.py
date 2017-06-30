#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime, Boolean
from Base import Base
from Device import Device
from User import User
from DnsReq import DnsReq

class DnsReqSimple(Base):
    __tablename__ = 'dnsreqssimple'
    
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
    query_domain = Column(String(256), index=True)

    # Single answer to the above query, there can be multiple
    ans_type = Column(Integer)
    ans_addr = Column(String(128), index=True) # ip
    ans_name = Column(String(512))
    ans_ttl = Column(Integer)

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
        return '<DnsReqSimple(server=%s, query=%s, ans=%s, filter=%s)>' % (self.dstip, self.query, self.ans_addr, not self.user_req)

if __name__ == "__main__":
    """
    Create (or recreate if exists).
    """
    import os
    import sys
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    db = sys.argv[1]
                
    engine = create_engine(db, poolclass=NullPool, echo=False)
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine)    

    DnsReqSimple.__table__.drop(engine, checkfirst=True) # drop if exists
    DnsReqSimple.__table__.create(engine)

    dbs = Session()    

    for row in dbs.query(DnsReq).all():
        # just make a copy with each response in a single row
        for i in range(len(row.ans_addr)):
            r = DnsReqSimple(devid=row.devid,
                             ts=row.ts,
                             srcip=row.srcip,
                             dstip=row.dstip,
                             proto=row.proto,
                             srcport=row.srcport,
                             dstport=row.dstport,
                             flowid=row.flowid,
                             query=row.query,
                             query_type=row.query_type,
                             query_domain=row.query_domain,
                             query_tld=row.query_tld,
                             ans_type=(row.ans_type[i] if (len(row.ans_type)>i) else None),
                             ans_addr=row.ans_addr[i],
                             ans_name=(row.ans_name[i] if (len(row.ans_name)>i) else None),
                             ans_ttl=(row.ans_ttl[i] if (len(row.ans_ttl)>i) else None),
                             matches_easylist=row.matches_easylist,
                             matches_easyprivacy=row.matches_easyprivacy,
                             matches_blacklist=row.matches_blacklist,
                             user_req=row.user_req,
                             duplicate=row.duplicate)
            print str(r)
            dbs.add(r)
    dbs.commit()
    dbs.close()
