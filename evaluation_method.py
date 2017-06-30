from collections import defaultdict

import datetime
import datautils
import scipy as sci
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
    Gets number of packets that were not filterd per interval.
    Parameters:
    - abs_beg(list): contains beginning of absence intervals.
    - abs_end(list): contains end of absence intervals.
    - packets(list of timestamp): packets to be checked.
    Returns:
    - list_packets_per_interval(list of int):  contains number of packets per interval. 
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
        list_packets_per_interval.append(tot_pac)

    return list_packets_per_interval


def plot_cdf_absence(blist, not_filtered, filtered, interval):
    """
    Plots CDF of user absence comparing the filtering methods.
    Parameters:
    - blist (list of int): number of packets per interval.
    - not_filtered (list of int): number of packets per interval.
    - filtered (list of int): number of packets per interval.
    - interval (list of int): number of packets per interval.
    """
    sns.set_style('whitegrid')

    fig, (ax1) = plt.subplots(1, 1, figsize=(7, 5))
    (x_blist,y_blist) = datautils.aecdf(blist)
    (x_int,y_int) = datautils.aecdf(interval)
    (x_filt,y_filt) = datautils.aecdf(filtered)
    (x_nfilt,y_nfilt) = datautils.aecdf(not_filtered)
    plt.plot(x_nfilt,y_nfilt, '-k', lw=2, label = 'not filtered')
    plt.plot(x_blist,y_blist, '-b', lw=2, label = 'filtered by blacklist')
    plt.plot(x_int,y_int, '-r', lw=2, label = 'filtered by intervals')
    plt.plot(x_filt,y_filt, '-g', lw=2, label = 'all filters')

    plt.legend (loc=0, borderaxespad=0., fontsize = 20, frameon=True, fancybox = False, framealpha = 1)
    plt.title('Cumulative Fraction of Intervals', fontsize = 20)
    plt.ylabel('CFI', fontsize = 20)
    plt.xscale('log')
    ax1.set_xlabel('number of packets', fontsize = 20)
    ax1.set_xticks([0,10,50,100,500,1000])
    ax1.set_xticklabels(['0','10','50','100','500','1000'])
    ax1.set_xlim(0,1000)
    ax1.set_ylim(0,1)
    plt.tick_params(labelsize=20)

    plt.tight_layout()
    fig.savefig('plots/absence_packets.png')
    plt.close(fig)

if __name__ == "__main__":
    blist_file = open('final_files/user_packets_true_false_blist_filtered')
    filtered_file = open('final_files/user_packets_true_false_filtered')
    interval_file = open('final_files/user_packets_true_false_interval_filtered')
    not_filtered_file = open('final_files/user_packets_true_false_not_filtered')
    comparison_evaluation_methods(blist_file, filtered_file, interval_file, not_filtered_file)
