import datetime

class Packet(object):
    srcip = ""
    dstip = ""
    srcport = ""
    dstport = ""

    # The class "constructor" - It's actually an initializer
    def __init__(self, srcip, dstip, srcport, dstport):
        self.srcip = srcip
        self.dstip = dstip
        self.srcport = srcport
        self.dstport = dstport

def make_packet(srcip, dstip, srcport, dstport):
    packet = Packet(srcip, dstip, srcport, dstport)
    return packet
