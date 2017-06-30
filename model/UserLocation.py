#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from Base import Base
from Device import Device
from User import User
from Location import Location

class UserLocation(Base):
    __tablename__ = 'userlocations'
    
    id = Column(Integer, primary_key=True)

    uid = Column(Integer, ForeignKey('users.id'), nullable=False)

    entertime = Column(DateTime, nullable=False)
    exittime = Column(DateTime, nullable=False)

    # common name
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
    
    def __repr__(self):
        return '<UserLocation(name=%s, enter=%s, exit=%s)>' % (self.name.encode('ascii', 'ignore'), self.entertime, self.exittime)    

if __name__ == "__main__":
    """
    Create (or recreate if exists).
    """
    import sys
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    db = sys.argv[1]
    engine = create_engine(db)

    print 'Creating table "userlocations" in %s' % db

    UserLocation.__table__.drop(engine, checkfirst=True) # drop if exists
    UserLocation.__table__.create(engine)

    Session = sessionmaker(bind=engine)    
    dbs = Session()    

    for u in dbs.query(User).all():
        # personal devices
        devs = [d.id for d in u.devices if not d.shared]

        # locations for these devices
        locs = dbs.query(Location).filter(Location.devid.in_(devs)).order_by(Location.entertime, Location.exittime).all()

        startloc = None # earliest start time of overlapping
        endloc = None   # latest endtime
        movesloc = None # moves loc within the overlapping (priority ?)
        netloc = None   # netloc

        while len(locs)>0:
            l = locs.pop(0)

            if (startloc == None):
                startloc = l

            if (endloc == None or l.exittime >= endloc.exittime):
                endloc = l            

            if (l.source == 'moves'):
                if (movesloc != None and movesloc.loc_id != l.loc_id):
                    # make a gap, moves indicates change of loc
                    ul = UserLocation(uid=u.id,
                                      entertime=startloc.entertime,
                                      exittime=movesloc.exittime)

                    ul.name = movesloc.name
                    ul.loc_id = movesloc.loc_id
                    ul.loc_name = movesloc.loc_name
                    ul.lat = movesloc.lat
                    ul.lon = movesloc.lon
                    ul.street = movesloc.street
                    ul.city = movesloc.city
                    ul.country = movesloc.country

                    if (netloc != None):
                        ul.net_public_ip = netloc.net_public_ip
                        ul.net_reverse_dns = netloc.net_reverse_dns
                        ul.net_asnumber = netloc.net_asnumber
                        ul.net_asname = netloc.net_asname

                    dbs.add(ul)
                    print ul

                    startloc = l
                    endloc = l
                    netloc = None

                movesloc = l
            else:
                # TODO: can we have continuous net locs ? should not ..
                netloc = l

            if ((len(locs)>0 and endloc.exittime < locs[0].entertime) or len(locs)==0):
                # there's a gap between loc reports or it's the last - record
                ul = UserLocation(uid=u.id,
                                  entertime=startloc.entertime,
                                  exittime=endloc.exittime)

                if (movesloc != None):
                    ul.name = movesloc.name
                    ul.loc_id = movesloc.loc_id
                    ul.loc_name = movesloc.loc_name
                    ul.lat = movesloc.lat
                    ul.lon = movesloc.lon
                    ul.street = movesloc.street
                    ul.city = movesloc.city
                    ul.country = movesloc.country

                    if (netloc != None):
                        ul.net_public_ip = netloc.net_public_ip
                        ul.net_reverse_dns = netloc.net_reverse_dns
                        ul.net_asnumber = netloc.net_asnumber
                        ul.net_asname = netloc.net_asname
                else:
                    ul.name = netloc.name
                    ul.loc_id = netloc.loc_id
                    ul.loc_name = netloc.loc_name
                    ul.lat = netloc.lat
                    ul.lon = netloc.lon
                    ul.street = netloc.street
                    ul.city = netloc.city
                    ul.country = netloc.country
                    ul.net_public_ip = netloc.net_public_ip
                    ul.net_reverse_dns = netloc.net_reverse_dns
                    ul.net_asnumber = netloc.net_asnumber
                    ul.net_asname = netloc.net_asname

                dbs.add(ul)
                print ul

                startloc = None
                endloc = None
                movesloc = None
                netloc = None

        dbs.commit()
    dbs.close()
