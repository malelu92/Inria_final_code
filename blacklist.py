from collections import defaultdict


def main():
    blacklist = create_blacklist_dict()
    url = 'wpad.ad.nottingham.ac.uk'
    #url = 'su.ff.avast.com'
    if is_in_blacklist(url, blacklist):
        print 'yes'
    else:
        print 'no'

def is_in_blacklist(url, blacklist):
    if url in blacklist[url[0]]:
        return True
    return False

def create_blacklist_dict():
    blacklist =defaultdict(list)
    file = open('blacklist.txt', 'r')
    for line in file:
        if line[0] == '|':
            url = line.rsplit('|')[-1]
            url = url.rsplit('^')[0]
            blacklist[url[0]].append(url)

    return blacklist

        


if __name__ == '__main__':
    main()
