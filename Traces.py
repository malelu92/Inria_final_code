import datetime

class Trace(object):
    url_domain = ""
    timst = datetime.datetime(2015, 01, 1, 0, 0)

    # The class "constructor" - It's actually an initializer 
    def __init__(self, url_domain, timst):
        self.url_domain = url_domain
        self.timst = timst

def make_trace(url_domain, timst):
    trace = Trace(url_domain, timst)
    return trace
