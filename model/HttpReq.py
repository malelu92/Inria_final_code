#!/usr/bin/python
from sqlalchemy import Column, ForeignKey, Float, Integer, BigInteger, String, DateTime, UniqueConstraint, Index, Boolean
from Base import Base
from Device import Device
from User import User

class HttpReq(Base):
    __tablename__ = 'httpreqs'
    
    id = Column(Integer, primary_key=True)
    devid = Column(Integer, ForeignKey('devices.id'), nullable=False)

    # squid|hostview
    source = Column(String(64), nullable=False)

    ts = Column(DateTime, nullable=False, index=True)
    
    # get|post
    req_method = Column(String(8), nullable=False)

    # http/x.x
    req_version = Column(String(32))

    # the full URL
    req_url = Column(String(8192), nullable=False)

    # parse URL into its components
    req_url_scheme = Column(String(8))
    req_url_port = Column(Integer)
    req_url_host = Column(String(256), index=True)
    req_url_domain = Column(String(256))
    req_url_tld = Column(String(8))
    req_url_origin = Column(String(512)) # scheme://host:port
    req_url_path = Column(String(8192))

    # user agent
    req_ua = Column(String(1024))

    # referer
    req_referer = Column(String(8192))

    # reply info
    res_status_code = Column(Integer)
    res_size = Column(BigInteger)
    res_mimetype = Column(String(512))

    # flow five-tuple (if known)
    srcip = Column(String(128)) # device IP (vpn or hostview)
    dstip = Column(String(128)) # domain host IP
    proto = Column(Integer)     # 6 (tcp)
    srcport = Column(Integer)   # device local port
    dstport = Column(Integer)   # 80 (or 8080 with hostview)

    # SHA hash of the 5-tuple for easier flow based indexing
    flowid = Column(String(64), index=True)

    # Filtering: url found on easylist (AdBlock)
    matches_easylist = Column(Boolean)

    # Filtering: url found on easyprivacy (AdBlock trackers etc)
    matches_easyprivacy = Column(Boolean)

    # Filtering: non-html content most likely
    matches_ctypefilter = Column(Boolean)

    # Filtering: some manually identified noisy service URLs (e.g. apple
    # update, Windows update etc)
    matches_urlblacklist = Column(Boolean)

    # matches_* == False
    user_url = Column(Boolean)

    # Make sure we do not insert duplicates
    UniqueConstraint('devid', 'ts', 'req_url', name='uix_3')

    def __repr__(self):
        return '<HttpReq (ts=%s, method=%s, url=%s)>' % (self.ts, self.req_method, self.req_url)

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
    import urllib
    import hashlib

    from urlparse import urlparse
    from sqlalchemy import create_engine    
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool
    from adblockparser import AdblockRules

    def spliturl(url):
        """Split URL to component tuple."""
        u = urlparse(url)
        netloc = u.netloc.split(':')
        host = netloc[0]
        port = None
        if (len(netloc)==2):
            port = int(netloc[1])
        elif (u.scheme == 'http'):
            port = 80
        elif (u.scheme == 'https'):
            port = 443
        return (u.scheme, host, port, u.path)

    # Source: http://stackoverflow.com/questions/2532053/validate-a-hostname-string
    def is_valid_hostname(hostname):        
        if (hostname == None or len(hostname)<=0 or len(hostname) > 254):
            return False

        if hostname[-1] == ".":
            # strip exactly one dot from the right, if present
            hostname = hostname[:-1]

        # must be not all-numeric, so that it can't be confused with an ip-address
        if re.match(r"[\d.]+$", hostname):
            return False

        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        return all(allowed.match(x) for x in hostname.split("."))


    ctypefilters = [
        re.compile('^.*\.js$'),
        re.compile('^.*\.js\?'),
        re.compile('^.*\.css$'),
        re.compile('^.*\.less$'),
        re.compile('^.*\.swf$'),
        re.compile('^.*\.jpg$'),
        re.compile('^.*\.jpeg$'),
        re.compile('^.*\.gif$'),
        re.compile('^.*\.bmp$'),
        re.compile('^.*\.png$'),
        re.compile('^.*\.jpt$'),
        re.compile('^.*\.ogg$'),
        re.compile('^.*\.mp3$'),
        re.compile('^.*\.mp4$'),
        re.compile('^.*\.mpg$'),
        re.compile('^.*\.mpeg$')
    ]

    easylist = []
    with open('/home/apietila/work/dataprojects/ucnstudy/data/easylist/easylist.txt') as f:
        for line in f:
            line = line.strip()
            if (line.startswith('!')):
                continue
            easylist.append(line)
    with open('/home/apietila/work/dataprojects/ucnstudy/data/easylist/liste_fr.txt') as f:
        for line in f:
            line = line.strip()
            if (line.startswith('!')):
                continue
            easylist.append(line)
    easylist_rules = AdblockRules(easylist, use_re2=True, 
                                  max_mem=512*1024*1024)

    easyprivacy = []
    with open('/home/apietila/work/dataprojects/ucnstudy/data/easylist/easyprivacy.txt') as f:
        for line in f:
            line = line.strip()
            if (line.startswith('!')):
                continue
            easyprivacy.append(line)
    easyprivacy_rules = AdblockRules(easyprivacy, use_re2=True, 
                                     max_mem=512*1024*1024)

    # bunch of noisy http domains ..
    blacklist = [
        re.compile('.*gsp1\.apple\.com.*'),
        re.compile('.*init-p01st\.push\.apple\.com.*'),
        re.compile('.*\.doubleclick\.net.*'),
        re.compile('.*\.smartadserver\.com.*'),
        re.compile('.*pixel\.quantserve\.com.*'),
        re.compile('.*static\.ess\.apple\.com/connectivity\.txt.*'),
        re.compile('.*go\.microsoft.com/fwlink.*'),
        re.compile('.*dmd\.metaservices\.microsoft\.com.*'),
        re.compile('.*\.windowsupdate\.com.*')
    ]

    def matchurl(url):
        matches_ctypefilter = False
        matches_easylist = False
        matches_easyprivacy = False
        matches_urlblacklist = False

        for rexp in ctypefilters:
            matches_ctypefilter = (rexp.match(url) is not None)
            if (matches_ctypefilter):
                break

        if (not matches_ctypefilter):
            matches_easylist = easylist_rules.should_block(url)
            matches_easyprivacy = easyprivacy_rules.should_block(url)

            for rexp in blacklist:
                matches_urlblacklist = (rexp.match(url) is not None)
                if (matches_urlblacklist):
                    break

        return (matches_ctypefilter, matches_easylist, matches_easyprivacy, matches_urlblacklist)

    def process_squid(dbs, d, httplogs):
        print 'import from squidlog',httplogs        

        with open(httplogs, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')

            for row in reader:
                (ts,status,size,method,url,protocol,mimetype,referer,useragent,srcip) = row
                if (url == '' or url == 'error:invalid-request'):
                    continue # squid error

                url = urllib.unquote(url)
                referer = urllib.unquote(referer)
                (scheme, host, port, path) = spliturl(url)

                origin = scheme+'://'+host
                if (port != None or port != ''):
                    origin += ':'+str(port)

                (matches_ctypefilter, matches_easylist, matches_easyprivacy, matches_urlblacklist) = matchurl(url)
                user_url = not (matches_ctypefilter or matches_easylist or matches_easyprivacy or matches_urlblacklist)

                # epoch timestamp
                ts = datetime.datetime.fromtimestamp(float(ts))

                # avoid adding garbage
                m = re.search("([\w-]+/[\w-]+)", mimetype)
                mimetype = (m.group(1) if (m!=None) else None)

                r = HttpReq(devid=d.id,
                            source="squid",
                            ts=ts,
                            srcip=srcip,
                            dstport=80,
                            req_method=method,
                            req_version=protocol,
                            req_url=url,
                            req_url_scheme=scheme,
                            req_url_host=host,
                            req_url_port=port,
                            req_url_origin=origin,
                            req_url_path=path,
                            req_ua=useragent,
                            req_referer=referer,
                            res_status_code=int(status),
                            res_size=long(size),
                            res_mimetype=mimetype,
                            matches_ctypefilter=matches_ctypefilter,
                            matches_urlblacklist=matches_urlblacklist,
                            matches_easylist=matches_easylist,
                            matches_easyprivacy=matches_easyprivacy,
                            user_url=user_url)
                
                print str(r)
                dbs.add(r)
                                
            dbs.commit()

    def process_hostview(dbs, d):
        print 'import hostview http logs'

        for db in glob.glob(d.hostviewdata+'/*/stats*.db.zip'):
            tmpfile = '/tmp/' + os.path.basename(db).replace('.zip','')
            if (os.path.exists(tmpfile)):
                os.unlink(tmpfile)

            subprocess.call(["7z","e","-o/tmp",db])
            print 'process',tmpfile

            conn = sqlite3.connect(tmpfile)
            c = conn.cursor()
            c.execute("SELECT timestamp,httpverb,httpverbparam,httphost,httpstatuscode,referer,contentlength,contenttype,srcip,destip,protocol,srcport,destport FROM http")
            if (c.rowcount == 0): # empty stats db
                conn.close()
                os.unlink(tmpfile)
                continue

            for row in c.fetchall():
                (ts,method,path,host,status,referer,size,ct,srcip,dstip,proto,srcport,dstport) = row
                    
                if (srcport == None or srcport == ''):
                    srcport = 80
                else:
                    srcport = int(srcport)

                if (dstport == None or dstport == ''):
                    dstport = 0
                else:
                    dstport = int(dstport)

                if (proto == None or proto == ''):
                    proto = 6 # tcp
                else:
                    proto = int(proto)

                if (size == None or size == ''):
                    size = None
                else:
                    size = long(size)

                if (status == ''):
                    status = None
                else:
                    status = int(status)

                # we want the dst to be the http server (req flow direction)
                if (srcport == 80 or srcport == 8080):
                    tmp = dstport
                    dstport = srcport
                    srcport = tmp
                    tmp = dstip
                    dstip = srcip
                    srcip = dstip

                # flowid
                flowid = hashlib.sha224()
                flowid.update(srcip)
                flowid.update(dstip)
                flowid.update(str(proto))
                flowid.update(str(srcport))
                flowid.update(str(dstport))

                # there were parsing bugs in HostView, fix
                # content type and validate hostname ...
                m = re.search("([\w-]+/[\w-]+)", ct)
                mimetype = (m.group(1) if (m!=None) else None)

                if (not is_valid_hostname(host)):
                    host = dstip
                    
                url = "http://%s%s"%(host,path)
                (matches_ctypefilter, matches_easylist, matches_easyprivacy, matches_urlblacklist) = matchurl(url)
                user_url = not (matches_ctypefilter or matches_easylist or matches_easyprivacy or matches_urlblacklist)

                r = HttpReq(devid=d.id,
                            source="hostview",
                            ts=datetime.datetime.fromtimestamp(float(ts)/1000.0),
                            req_method=method,
                            req_url=url,
                            req_url_scheme='http',
                            req_url_port=None,
                            req_url_host=host,
                            req_url_path=path,
                            req_url_origin='http://'+host+':'+str(dstport),
                            req_referer=referer,
                            res_status_code=status,
                            res_size=size,
                            res_mimetype=mimetype,
                            flowid=flowid.hexdigest(),
                            srcip=srcip,
                            dstip=dstip,
                            proto=proto,
                            srcport=srcport,
                            dstport=dstport,
                            matches_ctypefilter=matches_ctypefilter,
                            matches_urlblacklist=matches_urlblacklist,
                            matches_easylist=matches_easylist,
                            matches_easyprivacy=matches_easyprivacy,
                            user_url=user_url)

                print str(r)
                dbs.add(r)
                                
            dbs.commit()
            conn.close()
            os.unlink(tmpfile)

    def process(dbs, d):
        httplogs = d.netdata+'/squidlog.csv'
        if (os.path.exists(httplogs) and os.path.getsize(httplogs)>0):
            process_squid(dbs, d, httplogs)

        # don't do for french version of hostview (did not record traffic)
        if (d.hostviewdata != None and d.users[0].country=='uk'):
            process_hostview(dbs,d)

            
    # main
    db = sys.argv[1]
    engine = create_engine(db, poolclass=NullPool)
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine) 

    dbs = Session()
    if (len(sys.argv)==3):
        print 'Add device %s to table "httpreqs" in %s' % (sys.argv[2], db)
        d = dbs.query(Device).filter(Device.login==sys.argv[2]).one()

        # TODO: remove first any existing entries from the table ?
        HttpReq.__table__.create(engine, checkfirst=True)
        print 'handle',str(d)
        process(dbs,d)

    else:
        print '(Re-)creating table "httpreqs" in %s' % db
#        HttpReq.__table__.drop(engine, checkfirst=True) # drop if exists
#        HttpReq.__table__.create(engine)
        skip = True
        for d in dbs.query(Device).all():
            if  (d.login == 'clifford.mainlaptop'):
                skip = False
            if (skip):
                continue
            print 'handle',str(d)
            process(dbs,d)

    dbs.close()
