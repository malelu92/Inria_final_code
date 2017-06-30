#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime
from Base import Base
from Device import Device
from User import User

class FlowTraffic(Base):
    __tablename__ = 'flowtraffic'
    
    id = Column(Integer, primary_key=True)
    devid = Column(Integer, ForeignKey('devices.id'), nullable=False)

    # table will have an entry for each unique 5 tuple / second
    ts = Column(DateTime, nullable=False)
    srcip = Column(String(128))
    dstip = Column(String(128))
    proto = Column(Integer)
    srcport = Column(Integer)
    dstport = Column(Integer)

    packets = Column(Integer)
    bytes = Column(Integer)

    packet_size_min = Column(Integer)

- ts (1/s)
- 5-tuple
- pkts, bytes
- min/max/mean/stddev/median pkt size
- min/max/mean/stddev/median pkt iv
