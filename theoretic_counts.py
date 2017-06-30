from collections import defaultdict

def calculate_gap_interval(packets_list):
    """
    Gets the gap to unite sessions.
    Parameters:
    - packets_list(list of timestamps): list containing packet times.
    Returns:
    - iats[pos](int): gap time.
    """

    iat_list = []
    for i in range(0, len(packets_list)-1):
        iat = (packets_list[i+1]-packets_list[i]).total_seconds()
        iat = get_approximation(iat)
        iat_list.append(iat)

    (iats,cumulative_perc) = datautils.aecdf(iat_list)

    cont = 0
    for elem in cumulative_perc:
        if elem > 0.9:
            return iats[cont] 
        cont += 1

    return iats[cont-1]


def get_interval_list(packets_list):
    """
    Gets packet times divided into sessions.
    Parameters:
    - packets_list(list of timsteamps): contains stream of timestamps to be divided into sessions.
    Returns:
    interval_dict(dictionary): dict containing the timestamps per interval.
    """
    intv = 0
    interval_dict = defaultdict(list)
    gap_interval = calculate_gap_interval(traces_list)

    interval_dict[intv].append(packets_list[0])
    for i in range(0, len(packets_list)-1):
        iat = (packets_list[i+1]-packets_list[i]).total_seconds()
        if iat > gap_interval:
            intv += 1
        interval_dict[intv].append(packets_list[i+1])

    return interval_dict


def get_free_spikes_traces(interval_dict):
    """
    Eliminates periodic events.
    Parameters:
    - interval_dict(dictionary): dict containing the timestamps per interval.
    Returns:
    - filtered_packets(list of timestamps): contains the timestamps that were not eliminated
    b the periodic filter. 
    """
    #calculate theoretic periodicity per interval
    theoretic_count = []
    real_count = []
    filtered_packets = []
    eliminate_url = False

    #key = each interval
    for key in interval_dict.keys():
        distrib_dict = get_interval_distribution(interval_dict[key])
        filtered_interval_list = interval_dict[key]

        for iat_total in distrib_dict.keys():
            #if potential spike

            #agressive strategy
            #if iat_total != 'total' and distrib_dict[iat_total] >= 5:
                #eliminate_url = True

            if iat_total != 'total' and \
               ((distrib_dict['total'] > 1 and distrib_dict['total'] <= 5 and \
               (distrib_dict[iat_total]/float(distrib_dict['total'])) > 0.50) or \
                (distrib_dict['total'] > 5 and \
                 (distrib_dict[iat_total]/float(distrib_dict['total'])) > 0.30)):#0.40:
                if iat_total != 0:
                    timsts = interval_dict[key]
                    beg_block = timsts[0]
                    end_block = timsts[len(timsts)-1]

                    block_time = (end_block - beg_block).total_seconds()
                    theo_count = round(block_time/iat_total)
                    re_count = distrib_dict[iat_total]
                    theoretic_count.append(theo_count)
                    real_count.append(re_count)

                    #agressive strategy
                    #eliminate_url = True

                    #if number of intervals is close enough to theoretical number of intervals, eliminate traces
                    if theo_count <= 10:
                        error_margin = 0.2
                    elif theo_count > 10 and theo_count <= 100:
                        error_margin = 0.15
                    else:
                        error_margin = 0.1

                    #take whole interval off
                    if re_count >= (theo_count - theo_count*error_margin):
                        filtered_interval_list = []
                        break
                    #take only spike off
                    else:
                        filtered_interval_list = eliminate_spikes(filtered_interval_list, iat_total)

        filtered_packets.append(filtered_interval_list)        

    if eliminate_url:
        filtered_traces = []
    else:
        filtered_traces = list(itertools.chain(*filtered_traces))

    return filtered_packets


def get_interval_distribution(interval_list):
    """
    Gets the quantity of times each inter events time appears.
    Parameters:
    - interval_list(list of timestamps): timestamps present on certain interval.
    Returns:
    - interval_dist(dictionary): contains the distribution of inter event times in
    the interval.
    """
    interval_dist = defaultdict(int)
    interval_dist['total'] = 0
    timsts = interval_list

    if len(timsts) > 1:
        for i in range (0, len(timsts)-1):
            iat = (timsts[i+1]-timsts[i]).total_seconds()
            iat = get_approximation(iat)

            if iat not in interval_dist.keys():
                interval_dist[iat] = 1
            else:
                interval_dist[iat] += 1

            interval_dist['total'] +=1

    return interval_dist
                    

def get_approximation(value):
    """
    Returns a approximation for a given second.
    """
    if value <= 5:
        return round(value)
    #10 seconds gap
    elif value > 5 and value <= 15:
        return 10
    elif value > 15 and value <= 25:
        return 20
    elif value >25 and value <= 35:
        return 30
    elif value > 35 and value <= 45:
        return 40
    #30 seconds gap
    elif value > 45 and value <= 75:
        return 60
    elif value > 75 and value <= 105:
        return 90
    elif value > 105 and value <=135:
        return 120
    elif value > 135 and value <= 165:
        return 150
    elif value > 165 and value <= 195:
        return 180
    elif value > 195 and value <= 225:
        return 210
    elif value > 225 and value <= 270:
        return 240
    #60 seconds gap
    elif value > 270 and value <= 330:
        return 300
    elif value > 330 and value <= 390:
        return 360
    elif value > 390 and value <= 450:
        return 420
    elif value > 450 and value <= 510:
        return 480
    elif value > 510 and value <= 570:
        return 540
    elif value > 570 and value <= 675:
        return 600
    #150 seconds gaps -> 2.5 min
    elif value > 675 and value <= 825:
        return 750
    elif value > 825 and value <= 975:
        return 900
    elif value > 975 and value <= 1125:
        return 1050
    elif value > 1125 and value <= 1350:
        return 1200 #20 min
    #300 seconds gaps -> 5 min
    elif value > 1350 and value <= 1650:
        return 1500
    elif value > 1650 and value <= 1950:
        return 1800
    elif value > 1950 and value <= 2250:
        return 2100
    elif value > 2250 and value <= 2550:
        return 2400 # 40 min
    elif value > 2550 and value <= 2850:
        return 2700
    elif value > 2850 and value <= 3150:
        return 3000
    #900 seconds gaps -> 15 min gaps
    elif value > 3150 and value <= 4050:
        return 3600 # 1 hr
    elif value > 4050 and value <= 4950:
        return 4500
    elif value > 4950 and value <= 5850:
        return 5400
    elif value > 5850 and value <= 6750:
        return 6300
    elif value > 6750 and value <= 8100:
        return 7200 #2 hrs
    #1800 seconds gaps -> 30 min
    elif value > 8100 and value <= 9900:
        return 9000
    elif value > 9900 and value <= 11700:
        return 10800 #3 hrs
    elif value > 11700 and value <= 13500:
        return 12600
    elif value > 13500 and value <= 15300:
        return 14400 #4 hrs
    elif value > 15300 and value <= 17100:
        return 16200
    elif value > 17100 and value <= 18900:
        return 18000 #5 hrs
    #3600 seconds intervals
    elif value > 18900 and value <= 22500:
        return 21600
    elif value > 22500 and value <= 26100:
        return 25200
    elif value > 26100 and value <= 29700:
        return 28800
    elif value > 29700 and value <= 33300:
        return 32400
    elif value > 33300 and value <= 36900:
        return 36000 #10 hrs
    else:
        return 43200 #12 hrs
