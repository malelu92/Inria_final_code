#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from Base import Base
from Device import Device
from User import User
from HttpReq import HttpReq
from DnsReq import DnsReq

class UrlCategory(Base):
    """
    Map domain names to categories using AlchemyAPI.
    """
    __tablename__ = 'urlcategories'

    id = Column(Integer, primary_key=True)

    # domain (from dns reqs or http reqs)
    domain = Column(String(512), index=True, nullable=False)

    # requested url (what we sent to alchemy)
    url = Column(String(2048), nullable=False)

    # json file
    rawoutfile = Column(String(512))

    # the category with highest score (with confidence)
    main_category = Column(String(512))
    main_score = Column(Float)

    # all categories
    category = Column(ARRAY(String(512)))
    score = Column(ARRAY(Float))
    confident = Column(ARRAY(Boolean))
    
    def __repr__(self):
        return '<UrlCategory(domain=%s, category=%s, score=%f)>' % (self.domain, self.main_category, self.main_score)

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
    import json
    import datetime
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    sys.path.append("/home/apietila/work/dataprojects/ucnstudy/src/alchemyapi")
    from alchemyapi import AlchemyAPI

    cnt = 0
    alchemyapi = AlchemyAPI()

    def getCat(domain):
        global cnt

        # get the json (file cache or from the API)
        outfile = '/home/apietila/work/dataprojects/ucnstudy/data/alchemy/%s.json'%(domain.replace('http://','').replace('https://',''))

        res = None
        if (os.path.exists(outfile)):
            print 'read',outfile
            f = open(outfile, 'r')
            res = json.load(f)
            f.close()

        elif (cnt < 29500):
            # check these urls
            trylist = []
            if (domain.startswith('http')):
                trylist.append(domain)
            else:
                trylist.append("https://"+domain)
                trylist.append("http://"+domain)

                if (not domain.startswith('www')): 
                    trylist.append("https://www."+domain)
                    trylist.append("http://www."+domain)

            for url in trylist:
                print cnt,'fetch',url
                res = alchemyapi.taxonomy('url', url)
                cnt += 1

                # store raw output to file
                f = open(outfile, 'w')
                json.dump(res, f)
                f.close()

                if (res['status'] == 'OK'):
                    break

        urlcat = None
        if (res != None and res['status'] == 'OK'):
            urlcat = UrlCategory(domain=domain,
                                 url=res['url'],
                                 rawoutfile=outfile,
                                 main_category=None,
                                 main_score=0.0,
                                 category=[],
                                 score=[],
                                 confident=[])

            for t in res['taxonomy']:
                urlcat.category.append(t['label'])
                urlcat.score.append(float(t['score']))

                confident = True
                if ('confident' in t):
                    confident = (t['confident'] == u'yes')
                urlcat.confident.append(confident)

                # highest scoring category
                if (float(t['score']) > urlcat.main_score):
                    urlcat.main_score = float(t['score'])
                    urlcat.main_category = t['label']

            if (urlcat.main_category == None):
                urlcat = None
            else:
                print urlcat
        return urlcat

    db = sys.argv[1]
                
    engine = create_engine(db, poolclass=NullPool, echo=False)
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine)    
    dbs = Session()   

#    print '(Re-)creating table "urlcategories" in %s' % db
#    UrlCategory.__table__.drop(engine, checkfirst=True) # drop if exists
#    UrlCategory.__table__.create(engine)

    q = """SELECT distinct(query_domain) FROM dnsreqs WHERE NOT query_domain IS NULL"""
    for r in dbs.execute(text(q)):
        o = getCat(r[0])
        if (not o == None):
            dbs.add(o)
    dbs.commit()

    q = """SELECT distinct(req_url_domain) FROM httpreqs WHERE NOT req_url_domain IS NULL"""
    for r in dbs.execute(text(q)):
        o = getCat(r[0])
        if (o!=None):
            dbs.add(o)
    dbs.commit()
    dbs.close()
