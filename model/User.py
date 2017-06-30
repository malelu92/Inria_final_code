#!/usr/bin/python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from Base import Base
from user_devices import user_devices

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)

    # reg info
    username = Column(String(64), nullable=False, unique=True)
    familyname = Column(String(64), nullable=False)
    starttime = Column(DateTime, nullable=False)

    # uk|fr
    country = Column(String(4), nullable=False)

    # devices used by this user
    devices = relationship('Device',
                           secondary=user_devices,
                           back_populates='users')

    def __repr__(self):
        return '<User(user=%s, starttime=%s, cc=%s)>' % (self.username, self.starttime, self.country)

if __name__ == "__main__":
    """
    Create and add registered users to the database.
    
    Check the code before running, has some manual tweaks to fix
    the UK user records .. 
    """
    import os
    import sys
    from pymongo import MongoClient
    from sqlalchemy import create_engine    
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    # known test user accounts
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

    # android logger app collections in Mongo
    androidapp = ['app_data_usage',
                  'cell_location',
                  'data_conn_state',
                  'device_info',
                  'gsm_cell_location',
                  'llama_location',
                  'network_state',
                  'running_apps',
                  'sockets',
                  'system_state',
                  'user_location',
                  'wifi_neigh']

    mongodb = sys.argv[1]
    db = sys.argv[2]
    cc = sys.argv[3]

    # For adding the family name
    update = (len(sys.argv)>4)

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

    # (re-)create table
#    if (not update):
#        User.__table__.drop(engine, checkfirst=True) # drop if exists
#        User.__table__.create(engine)

    # transaction
    dbs = Session()
    for user in mdb.users.find():
        if (user[u'isadmin'] or user[u'username'].lower() in testusers):
            continue

        if (update):
            ormuser = dbs.query(User).filter(User.username==user[u'username'].lower()).first()
            if (cc == 'uk' and dbs.query(User).filter(User.familyname==user[u'familyname'].lower()).count() == 0):
                # TODO: repeat in add (if re-creating tables ..) !!
                # fix manually the UK users (username is infact household)
                username1 = user[u'username'].lower()
                username2 = None
                if (username1 == 'clifford'):
                    username1 = 'clifford.wife'
                    username2 = 'clifford.husband'
                elif (username1 == 'barnesldavid'):
                    username1 = 'barnesldavid.wife'
                    username2 = 'barnesldavid.husband'                    
                elif (username1 == 'bowen'):
                    username1 = 'bowen.wife'
                    username2 = 'bowen.husband'
                elif (username1 == 'bridgeman'):
                    username1 = 'bridgeman.wife'
                    username2 = 'bridgeman.husband'
                # else do nothing, just single user

                ormuser.familyname = user[u'familyname'].lower()

                if (username2 != None):
                    ormuser.username = username1

                    ormuser2 = User(username=username2,
                                    familyname=user[u'familyname'].lower(),
                                    starttime=user[u'created'],
                                    country=cc)
                    dbs.add(ormuser2)
            else:
                ormuser.familyname = user[u'familyname'].lower()
        else:
            ormuser = User(username=user[u'username'].lower(),
                           familyname=user[u'familyname'].lower(),
                           starttime=user[u'created'],
                           country=cc)
            dbs.add(ormuser)

    dbs.commit()

