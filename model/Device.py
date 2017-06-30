#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from Base import Base
from user_devices import user_devices

class Device(Base):
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)

    # registration info
    name = Column(String(64), nullable=False)
    login = Column(String(64), nullable=False, index=True, unique=True)
    platform = Column(String(64), nullable=False)

    # phone | tablet | laptop | pc
    devtype = Column(String(64))

    # android | ios | darwin | windows 
    os = Column(String(64))

    # is this devices shared by multiple users ? 
    shared = Column(Boolean, nullable=False)

    # assigned VPN addresses
    addresses = Column(ARRAY(String(64)), nullable=False)

    # users using this device
    users = relationship('User',
                         secondary=user_devices,
                         back_populates='devices')

    # random android app id
    androidappid = Column(String(64), index=True, unique=True)

    # hostview data folder
    hostviewdata = Column(String(256), unique=True)

    # this dev pcaps
    netdata = Column(String(256), unique=True)

    def __repr__(self):
        return '<Device(type=%s, os=%s, login=%s)>' % (self.devtype, self.os, self.login)


if __name__ == "__main__":
    """
    Create and add registered devices to the database.
    FIXME!!!
    """
    import os
    import sys
    from pymongo import MongoClient
    from sqlalchemy import create_engine    
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    testusers = ['apietila',
                 'ptolmie',
                 'e.tolmie',
                 'rcruztei',
                 'grosca',
                 'tlodge',
                 'admin',
                 'murray',
                 'deployment',
                 'dominic.price']

    mongodb = sys.argv[1]
    db = sys.argv[2]
    cc = sys.argv[3]

    basedatadir = '/home/ucndata/'
    if (cc == 'fr'):
        basedatadir += 'ucnexp'
    else:
        basedatadir += 'ucnexp_uk'

    mdatabase = 'ucnexp'
    if (cc == 'uk'):
        mdatabase = 'ucnexp_uk'

    print '%s users from "%s" to "%s" [%s]'%(('Update' if update else 'Export'), mongodb,db,basedatadir)

    mdb = MongoClient(mongodb)[mdatabase]

    engine = create_engine(db, poolclass=NullPool, echo=True)
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine) 

    # (re-)create
#    Device.__table__.drop(engine, checkfirst=True) # drop if exists
#    Device.__table__.create(engine)

    # transaction
    dbs = Session()
    for dev in mdb.devices.find():
        if (dev[u'username'].lower() in testusers):
            continue

        d = Device(login=dev[u'login'].lower()
                   # TODO: original script was lost by accident
                   # should fix this ...
                   )
        dbs.add(d)
#    dbs.commit()
    dbs.rollback()
