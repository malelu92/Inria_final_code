from collections import defaultdict
from IPython.display import display
from matplotlib import dates

from model.Base import Base
from model.User import User
from model.Device import Device
from model.HttpReq import HttpReq
from model.DnsReq import DnsReq
from model.user_devices import user_devices;

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from blacklist import create_blacklist_dict
from blacklist import is_in_blacklist
from theoretic_counts import get_interval_list, get_free_spikes_traces
from Traces import Trace

#import datautils
import datetime
import errno
import matplotlib.pyplot as plt
import os
import seaborn as sns

DB='postgresql+psycopg2:///ucnstudy'

engine = create_engine(DB, echo=False, poolclass=NullPool)
Base.metadata.bind = engine
Session = sessionmaker(bind=engine)

ses = Session()
users = ses.query(User)

def detection_algorithm(f_blacklist, f_seconds, f_spikes):
    """
    Filters out background activity and create files with remaining packets and a file with which packets
    is considered user generated (True) and background generated (False).
    Parameters:
    - f_blacklist (bool): indicates if packets will be filtered by blacklist.
    - f_seconds (bool): indicates if packets will be filtered by interval smaller than a second.
    - f_spikes (bool): indicates if packets will be filtered by periodic intervals.
    """
    blacklist = create_blacklist_dict()
    filtered_traces_user_dict = defaultdict(list)

    file_type = get_file_type(f_blacklist, f_seconds, f_spikes)

    inspection_interval = 60*5

    bucket_list = [1, 5, 10, 30, 60]
    traces_file_1 = open('final_files/user_packets_1_%s'%(file_type), 'w')
    traces_file_5 = open('final_files/user_packets_5_%s'%(file_type), 'w')
    traces_file_10 = open('final_files/user_packets_10_%s'%(file_type), 'w')
    traces_file_30 = open('final_files/user_packets_30_%s'%(file_type), 'w')
    traces_file_60 = open('final_files/user_packets_bucket_60_%s'%(file_type), 'w')
    packets_file = open('final_files/user_packets_true_false_%s'%(file_type), 'w') 

    for user in users:
        devids = []
        for d in user.devices:
            devids.append(str(d.id))

        devs = {}
        for d in user.devices:
            devs[d.id] = d.platform

        for elem_id in devids:
            sql_userid = """SELECT login FROM devices WHERE id =:d_id"""
            user_id = ses.execute(text(sql_userid).bindparams(d_id = elem_id)).fetchone()
            idt = user_id[0]

            print idt
            packets_file.write(str(idt)+'\n')

            if idt != 'bowen.laptop':
                continue

            #list contains Traces -> timestamp, url
            http_traces_list, dns_traces_list = get_test_data(elem_id)
            print len(http_traces_list)
            print len(dns_traces_list)

            cont = 0
            for packet in http_traces_list:
                print cont
                packets_list = get_packets_in_interval(packet, http_traces_list, inspection_interval)
                pkt_user_gen = filter_packet(packet, packets_list, blacklist, f_blacklist, f_seconds, f_spikes)
                packets_file.write(str(packet.timst) + ' ' + str(pkt_user_gen) + '\n')
                if pkt_user_gen:
                    filtered_traces_user_dict[idt].append(packet.timst)
                cont+=1

            for packet in dns_traces_list:
                packets_list = get_packets_in_interval(packet, dns_traces_list, inspection_interval)
                pkt_user_gen = filter_packet(packet, packets_list, blacklist, f_blacklist, f_seconds, f_spikes)
                packets_file.write(str(packet.timst) + ' ' + str(pkt_user_gen) + '\n')
                if pkt_user_gen:
                    filtered_traces_user_dict[idt].append(packet.timst)

            for bucket in bucket_list:
                print bucket
                traces_bucket = []
                traces_bucket = get_interval_list_predefined_gap(sorted(filtered_traces_user_dict[idt]), bucket)
                if bucket == 1:
                    traces_file_1.write(idt + '\n')
                elif bucket == 5:
                    traces_file_5.write(idt + '\n')
                elif bucket == 10:
                    traces_file_10.write(idt + '\n')
                elif bucket == 30:
                    traces_file_30.write(idt + '\n')
                elif bucket == 60:
                    traces_file_60.write(idt + '\n')

                print len(traces_bucket)
                for timst in traces_bucket:
                    if bucket == 1:
                        traces_file_1.write(str(timst) + '\n')
                    elif bucket == 5:
                        traces_file_5.write(str(timst) + '\n')
                    elif bucket == 10:
                        traces_file_10.write(str(timst) + '\n')
                    elif bucket == 30:
                        traces_file_30.write(str(timst) + '\n')
                    elif bucket == 60:
                        traces_file_60.write(str(timst) + '\n')

    traces_file_1.close()
    traces_file_5.close()
    traces_file_10.close()
    traces_file_30.close()
    traces_file_60.close()


def get_file_type(f_blacklist, f_seconds, f_spikes):
    """
    Defines the name for the type of filtering that will be done.
    - f_blacklist (bool): indicates if packets will be filtered by blacklist.
    - f_seconds (bool): indicates if packets will be filtered by interval smaller than a second.
    - f_spikes (bool): indicates if packets will be filtered by periodic intervals.
    Returns:
    - string containing filtering type.
    """
    if f_blacklist and f_seconds and f_spikes:
        return 'filtered'

    elif f_blacklist and not f_seconds and not f_spikes:
        return 'blist_filtered'

    elif not f_blacklist and f_seconds and f_spikes:
        return 'interval_filtered'

    elif not f_blacklist and not f_seconds and not f_spikes:
        return 'not_filtered'


def get_interval_list_predefined_gap(traces_list, gap_interval):
    """
    Creates extra packets, based on the length of the sliding window.
    Parameters:
    - traces_list(list of timestamps): contains times of packets that were requested.
    - gap_interval(int): sliding window length.
    Returns:
    - interval_list(list of timestamps): list containing previous and new timestamps.
    """

    intv = 0
    interval_list = []
    pre_traces = []

    for timst in traces_list:
        timst = timst.replace(microsecond=0)
        pre_traces.append(timst)

    for i in range(0, len(pre_traces)-1):
        iat = (pre_traces[i+1]-pre_traces[i]).total_seconds()
        if iat <= gap_interval:
            current_trace = pre_traces[i]
            while current_trace < pre_traces[i+1]:
                interval_list.append(current_trace)
                current_trace = current_trace + datetime.timedelta(0,1)
        else:
            interval_list.append(pre_traces[i])

        if i == len(pre_traces)-2:
            interval_list.append(pre_traces[i+1])

    return interval_list

def get_packets_in_interval(packet, packets_list, inspection_interval):
    """
    Gets all the packets of the same url as the evaluated packet in an interval of time.
    Parameters:
    - packet(Trace): packet that will be evaluated by the algorithm.
    - packets_list(list of Traces): all packets in the network.
    - inspection_interval(int): interval of time which packets from the same url will be taken.
    Returns:
    - final_packets_list(list of Traces): packets of the same url as the evaluated packet in 
    the interval range.
    """
    packets_url_list = []
    final_packet_list = []

    for elem in packets_list:
        if elem.url_domain == packet.url_domain:
            packets_url_list.append(elem)

    for i in range(0, len(packets_url_list)):
        elem = packets_url_list[i]
        if elem.timst == packet.timst:
            pos = i
            break

    for i in range(pos, 0, -1):
        elem = packets_url_list[i]
        if (packet.timst - elem.timst).total_seconds() <= inspection_interval:
            final_packet_list.append(elem)

        elif (packet.timst - elem.timst).total_seconds() > inspection_interval:
            break

    return final_packet_list

def get_test_data(device_id):
    """
    Gets dns and http requests packets from the database.
    Parameters:
    - device_id(int): unique device identifier.
    Returns:
    - http_traces_list (list of Traces): contains http request packets for a device.
    - dns_traces_list (list of Traces): contains dns request packets for a device.
    """

    sql_http = """SELECT req_url_host, ts, lag(ts) OVER (ORDER BY ts) FROM httpreqs2 \
        WHERE devid =:d_id AND matches_urlblacklist = 'f' and source = 'hostview'"""

    sql_dns = """SELECT query, ts, lag(ts) OVER (ORDER BY ts) FROM dnsreqs \
        WHERE devid =:d_id AND matches_blacklist = 'f'"""

    http_traces_list = []
    for row in ses.execute(text(sql_http).bindparams(d_id = device_id)):
        elem = Trace(row[0], row[1])
        http_traces_list.append(elem)

    dns_traces_list = []
    for row in ses.execute(text(sql_dns).bindparams(d_id = device_id)):
        elem = Trace(row[0], row[1])
        dns_traces_list.append(elem)

    return http_traces_list, dns_traces_list


def filter_packet(packet, packets_list, blacklist, f_blacklist, f_seconds, f_spikes):
    """
    Defines if given packet is user or background generated.
    Parameters:
    - packet(Trace): packet to be analysed. Contains url and timestamp.
    - packets_list(list of Traces): list containing packets of the same url in an interval of five minutes.
    - blacklist(dictionary of strings): contains list of blacklists to be filtered.
    - f_blacklist (bool): indicates if packets will be filtered by blacklist.
    - f_seconds (bool): indicates if packets will be filtered by interval smaller than a second.
    - f_spikes (bool): indicates if packets will be filtered by periodic intervals.
    Returns:
    - True if packet is user generated.
    - False if packet is background generated.
    """

    url_domain = packet.url_domain
    timst_list = []

    #takes off noisy packets -> no url
    if not packet.url_domain:
        return False

    #checks if packet is in blacklist
    if f_blacklist and is_in_blacklist(packet.url_domain, blacklist):
        return False

    #checks if packet is less than a second from previous one
    if f_seconds and len(packets_list) >= 2:
        previous_packet = packets_list[len(packets_list)-2]
        iat = (previous_packet.timst - packet.timst).total_seconds()
        if iat < 1:
            return False

    #checks if packet is part of a periodic interval
    if f_spikes:
        for elem in packets_list:
            timst_list.append(elem.timst)
        timst_list = filter_spikes(timst_list)
        if packet.timst in timst_list:
            return True
        else:
            return False

    return True

def filter_spikes(packets_list, url_domain):
    """
    Eliminates periodic intervals.
    Parameters:
    - packets_list(list of Traces): packets with same url that will be filtered.
    Returns:
    -packets_list(list of Traces): list of user facing packets. 
    """
    pre_filtered_list = []
    cont = 0

    while pre_filtered_list != packets_list and len(packets_list) > 1:
        pre_filtered_list = packets_list
        interval_list = get_interval_list(packets_list)
        packets_list = get_free_spikes_traces(interval_list)
        cont +=1

    return packets_list


if __name__ == '__main__':
    detection_algorithm(True, False, False)
