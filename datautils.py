#!/usr/bin/python
import numpy as np
import scipy as sci
import pandas as pd
import pytz
import pycountry

from pandas.tseries.offsets import *
from datetime import datetime, timedelta
from dateutil import tz
from operator import itemgetter
from collections import Counter, defaultdict

def ecdf(s):
    """ECDF of pandas series."""
    x = sorted(s.values)
    y = np.arange(len(x))/float(len(x))
    return (x,y)

def aecdf(s):
    """ECDF of pandas series."""
    x = sorted(s)
    y = np.arange(len(x))/float(len(x))
    return (x,y)


def utctolocal(dt, tzoffset):
    """
    Simple (non timezone aware) conversion of utc datetime to 
    offset datetime.
    """
    return dt + timedelta(seconds=tzoffset*-60)

def utctotz(dt, tz):
    """
    Converts UTC timestamps (naive) to localized datetime (tz aware).
    """
    dt = pytz.utc.localize(dt)
    tzinfo = pytz.timezone(tz)
    return dt.astimezone(tzinfo)

def utctocc(dt, cc):
    """
    Converts UTC timestamps (naive) to localized datetime (tz aware).
    """
    dt = pytz.utc.localize(dt)
    if (cc == 'fr'):
        tzinfo = pytz.timezone('Europe/Paris')
    else:
        tzinfo = pytz.timezone('Europe/London')
    return dt.astimezone(tzinfo)
