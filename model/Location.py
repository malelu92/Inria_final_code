#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime, Boolean
from Base import Base
from Device import Device
from User import User

class Location(Base):
    __tablename__ = 'locations'
    
    id = Column(Integer, primary_key=True)
    devid = Column(Integer, ForeignKey('devices.id'), nullable=False)

    # moves | vpn | hostview
    source = Column(String(16), nullable=False)

    # moves enter | vpn connect | hostview interface up
    entertime = Column(DateTime, nullable=False)

    # moves enter | 
    # vpn disconnect (if missing, last packet since connect) |
    # hostview interface down (if missing, last packet since connect)
    exittime = Column(DateTime, nullable=False)

    # common name (pick the most specific one available):
    # loc_name, city || net_asname, city || street, city || city || country
    name = Column(String(512), nullable=False)

    # moves API
    loc_id = Column(BigInteger)
    loc_name = Column(String(256))

    # vpn | hostview (RIPE Stats API)
    net_public_ip = Column(String(128))
    net_reverse_dns = Column(String(1024)) 
    net_asnumber = Column(Integer) 
    net_asname = Column(String(256)) 

    # moves API | public IP geoloc (RIPE Stats API)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    # geocoded (Google Maps API)
    street = Column(String(256)) 
    city = Column(String(32))
    country = Column(String(32))
    
    # True if this location overlaps other info (now just flagging any vpn info overlapping moves)
    # TODO: check actual time ranges
    overlap = Column(Boolean())

    def __repr__(self):
        return '<Location(name=%s, enter=%s, exit=%s)>' % (self.name.encode('ascii', 'ignore'), self.entertime, self.exittime)
    

if __name__ == "__main__":
    """
    Create (or recreate if exists).
    """
    import sys
    from sqlalchemy import create_engine    

    db = sys.argv[1]
    engine = create_engine(db)

    print 'Creating table "locations" in %s' % db

    Location.__table__.drop(engine, checkfirst=True) # drop if exists
    Location.__table__.create(engine)
