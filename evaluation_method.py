from collections import defaultdict
from matplotlib import dates

import datetime
import datautils
import scipy as sci
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from inter_event_time_analysis_activities import get_activities_inter_times

def comparison_evaluation_methods(blist_file, filtered_file, interval_file, not_filtered_file):
    """
    Compares performance of filtering methods on user absence times.
    Parameters:
    - blist_file(file): contains timestamps followed by True (if user facing) and False otherwise.
    - filtered_file(file): contains timestamps followed by True (if user facing) and False otherwise. 
    - interval_file(file): contains timestamps followed by True (if user facing) and False otherwise.
    - not_filtered_file(file): contains timestamps followed by True (if user facing) and False otherwise.
    """
    abs_beg, abs_end = get_activities_inter_times()
    blist_itv_pkts, total_blist = evaluation_method_absence(blist_file, abs_beg, abs_end)
    filt_itv_pkts, total_filt = evaluation_method_absence(filtered_file, abs_beg, abs_end)
    interval_itv_pkts, total_interval = evaluation_method_absence(interval_file, abs_beg, abs_end)
    nfilt_itv_pkts, total_nfilt = evaluation_method_absence(not_filtered_file, abs_beg, abs_end)

    print len(nfilt_itv_pkts)
    plot_cdf_absence(blist_itv_pkts, nfilt_itv_pkts, filt_itv_pkts, interval_itv_pkts)

def evaluation_method_absence(filt_file, abs_beg, abs_end):
    """
    Evaluates filters.
    Parameters:
    - filt_file(file): contains timestamps filtered (False) or not filtered (True)
    - abs_beg(dictionary): contains beginning of intervals of absence per user.
    - abs_end(dictionary): contains ending of intervals of absence per user.
    Returns:
    - filt_list(list): contains numebr of packets per interval.
    - total_filt(int): number of packets found on absent periods.
    """
    filt = get_data_from_file(filt_file)

    filt_list = []
    for user in abs_beg.keys():
        if user != 'bowen.laptop':
            continue
        print user
        per_filtered = get_packets_per_interval(abs_beg[user], abs_end[user], filt[user])
            
        total_filt = 0
        for cont in range(0, len(per_filtered)):
            total_filt += per_filtered[cont] 
            filt_list.append(per_filtered[cont])

    return filt_list, total_filt


def get_data_from_file(info_file):
    """
    Reads file and extract timestamps that are considered "True".
    Parameters:
    - info_file(file): file containing packets filtered.
    Returns:
    - packets(dictionary): contains timestamps per user.
    """
    content = info_file.read().splitlines()

    packets = defaultdict(list)

    for line in content:
        if line[0] != '2':
            user = line
            continue

        if 'False' in line:
            packet_status = False
            timst = line.rsplit(' False', 1)[0]
        else:
            packet_status = True
            timst = line.rsplit(' True', 1)[0]

        if len(timst) > 20:
            timst = datetime.datetime.strptime(timst, "%Y-%m-%d %H:%M:%S.%f")
        else:
            timst = datetime.datetime.strptime(timst, "%Y-%m-%d %H:%M:%S")

        if packet_status:
            packets[user].append(timst)

    return packets

def get_packets_per_interval(abs_beg, abs_end, packets):
    """
    """
    intervals = defaultdict(int)
    list_packets_per_interval = []
    for i in range(0, len(abs_beg)):
        intervals[i] = 0

    for timst in packets:
        cont = 0
        found = False
        while cont < len(abs_beg) and found == False:
            if timst >= abs_beg[cont] and timst <= abs_end[cont]:
                intervals[cont] += 1
                found = True
            cont += 1

    for itv, tot_pac in intervals.iteritems():
        #print tot_pac
        list_packets_per_interval.append(tot_pac)

    return list_packets_per_interval


"""def get_timst_from_act_file(data_file):

    content = data_file.read().splitlines()
    traces_true = []
    traces_false = []
    cont = 0
    user = None

    for line in content:
        if cont == 0 or cont == 1:
            cont += 1
            continue

        timst = line.rsplit(' |', 3)[0]
        timst = timst.rsplit('| ', 1)[1]

        if len(timst) > 20:
            timst = datetime.datetime.strptime(timst, "%Y-%m-%d %H:%M:%S.%f")
        else:
            timst = datetime.datetime.strptime(timst, "%Y-%m-%d %H:%M:%S")

        if 'True' in line:
            traces_true.append(timst)
        else:
            traces_false.append(timst)

    return traces_true, traces_false
"""

def get_timst_from_file(data_file):

    content = data_file.read().splitlines()
    traces = defaultdict(list)
    cont = 0
    user = None

    for line in content:
        if cont == 0:
            cont += 1
            continue

        if line == 'bowen.laptop' or line == 'bridgeman.laptop2' or line == 'bridgeman.stuartlaptop' or line == 'chrismaley\
.loungepc' or line == 'chrismaley.mainpc' or line == 'clifford.mainlaptop' or line == 'gluch.laptop' or line == 'kemianny.m\
ainlaptop' or line == 'neenagupta.workpc':
            user = line
        else:
            timst = datetime.datetime.strptime(line, "%Y-%m-%d %H:%M:%S")
            traces[user].append(timst)

    return traces

def plot_cdf_absence(blist, not_filtered, filtered, interval):
    """
    """
    sns.set_style('whitegrid')

    fig, (ax1) = plt.subplots(1, 1, figsize=(7, 5))
    (x_blist,y_blist) = datautils.aecdf(blist)
    (x_int,y_int) = datautils.aecdf(interval)
    #print 'blist'
    #x_blist, y_blist = get_data_for_cdf(blist)
    #print 'not filtered'
    #x_nfilt, y_nfilt = get_data_for_cdf(not_filtered)
    #print 'filtered'
    #x_filt, y_filt = get_data_for_cdf(filtered)
    (x_filt,y_filt) = datautils.aecdf(filtered)
    (x_nfilt,y_nfilt) = datautils.aecdf(not_filtered)
    plt.plot(x_nfilt,y_nfilt, '-k', lw=2, label = 'not filtered')
    plt.plot(x_blist,y_blist, '-b', lw=2, label = 'filtered by blacklist')
    plt.plot(x_int,y_int, '-r', lw=2, label = 'filtered by intervals')
    plt.plot(x_filt,y_filt, '-g', lw=2, label = 'all filters')

    plt.legend (loc=0, borderaxespad=0., fontsize = 20, frameon=True, fancybox = False, framealpha = 1)

    #for i in range(0, len(x_filt)):
        #print x_nfilt[i]
        #print y_nfilt[i]
        #print '====='

    #total = 0
    #for inte in blist.keys():
        #print str(inte) + ' blist ' + str(blist[inte]) +  ' filtered ' + str(filtered[inte]) +  ' not_filt ' + str(not_filtered[inte])# +  ' interval ' + str(per_interval[inte])

    plt.title('Cumulative Fraction of Intervals', fontsize = 20)
    plt.ylabel('CFI', fontsize = 20)
    plt.xscale('log')
    ax1.set_xlabel('number of packets', fontsize = 20)
    ax1.set_xticks([0,10,50,100,500,1000])
    ax1.set_xticklabels(['0','10','50','100','500','1000'])
    ax1.set_xlim(0,1000)
    ax1.set_ylim(0,1)
    plt.tick_params(labelsize=20)
    #plt.xlim(min(values_list),max(values_list))

    #plt.show()
    plt.tight_layout()
    fig.savefig('plots/absence_packets.png')
    plt.close(fig)

if __name__ == "__main__":
    blist_file = open('final_files/user_packets_true_false_blist_filtered')
    filtered_file = open('final_files/user_packets_true_false_filtered')
    interval_file = open('final_files/user_packets_true_false_interval_filtered')
    not_filtered_file = open('final_files/user_packets_true_false_not_filtered')
    comparison_evaluation_methods(blist_file, filtered_file, interval_file, not_filtered_file)