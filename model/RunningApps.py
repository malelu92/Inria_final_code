#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime, Boolean
from Base import Base
from Device import Device
from User import User

class RunningApps(Base):
    """
    Running applications (from Android logger or HostView).
    """
    __tablename__ = 'runningapps'

    id = Column(Integer, primary_key=True)

    devid = Column(Integer, ForeignKey('devices.id'), nullable=False)

    ts = Column(DateTime, nullable=False, index=True)

    appname = Column(String(512), nullable=False)

    description = Column(String(512))

    pid = Column(Integer)

    memory = Column(Integer)

    cpu = Column(Float)

    is_foreground = Column(Boolean)

    has_io = Column(Boolean)

    is_fullscreen = Column(Boolean)

    def __repr__(self):
        return '<RunningApps (ts=%s, appname=%s, desc=%s, fg=%s, io=%s)>' % (self.ts, self.appname, self.description, self.is_foreground, self.has_io)

if __name__ == "__main__":
    """
    Create (or recreate if exists).
    """
    import os
    import sys
    import sqlite3
    import csv
    import glob
    import subprocess
    import re
    import datetime
    from sqlalchemy import create_engine    
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    def process(dbs,d):
        """Process a single device."""
        if (d.hostviewdata==None):
            return

        isfr = (d.users[0].country == 'fr')

        # appname -> description
        dcache = {}

        for db in glob.glob(d.hostviewdata+'/*/stats*.db.zip'):
            tmpfile = '/tmp/' + os.path.basename(db).replace('.zip','')
            if (os.path.exists(tmpfile)):
                os.unlink(tmpfile)

            subprocess.call(["7z","e","-o/tmp",db])

            print 'process',tmpfile
            conn = sqlite3.connect(tmpfile)

            c = conn.cursor()
            c.execute("SELECT timestamp, pid, name, memory, cpu FROM procs")
            if (c.rowcount == 0): # empty stats db
                conn.close()
                os.unlink(tmpfile)
                continue

            pidcache = {}

            for row in c.fetchall():
                (ts,pid,appname,memory,cpu) = row
                ts = int(ts)
                pid = int(pid)
                memory = long(memory)
                cpu = float(cpu)

                description = None
                if (appname in dcache):
                    description = dcache[appname]
                elif (not isfr):
                    descrow = c.execute("SELECT description from activity where name=\"%s\" LIMIT 1"%(appname)).fetchone()
                    if (descrow != None):
                        description = str(descrow[0])
                        dcache[appname] = description

                if (appname == None):
                    appname = "unknown"
                appname = appname.lower()

                is_fullscreen = False
                is_foreground = False

                before = c.execute("SELECT pid,name,fullscreen,idle FROM activity WHERE timestamp<=%d ORDER BY timestamp DESC LIMIT 1"%(ts)).fetchone()
                if (before!=None and int(before[0])==pid and int(before[3])==0):
                    # the app went non-idle(1) just before this proc line
                    is_foreground = True
                    is_fullscreen = (int(before[2]) == 1)

                has_io = False
                if (pid in pidcache and not isfr):
                    has_io = (c.execute("SELECT * FROM io WHERE pid=%d AND timestamp>=%d AND timestamp<%d"%(pid,pidcache[pid],ts)).rowcount > 0)

                r = RunningApps(devid=d.id,
                                ts=datetime.datetime.fromtimestamp(float(ts)/1000.0),
                                appname=appname,
                                description=description,
                                pid=pid,
                                cpu=cpu,
                                memory=memory,
                                is_foreground=is_foreground,
                                is_fullscreen=is_fullscreen,
                                has_io=has_io)

                print str(r)
                dbs.add(r)

                pidcache[pid] = ts
                                
            dbs.commit()
            conn.close()
            os.unlink(tmpfile)

    db = sys.argv[1]
    engine = create_engine(db, poolclass=NullPool)
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine) 

    dbs = Session()
    print '(Re-)creating table "runningapps" in %s' % db
    RunningApps.__table__.drop(engine, checkfirst=True) # drop if exists
    RunningApps.__table__.create(engine)
    for d in dbs.query(Device).all():
        print 'handle',str(d)
        process(dbs,d)
    dbs.close()
