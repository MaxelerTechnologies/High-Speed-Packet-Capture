from scapy.utils import RawPcapReader, PcapReader
from scapy.data import MTU
from scapy.error import Scapy_Exception
from scapy.config import conf
import struct
import os

'''
hackish nano second pcap support
modifed from http://bb.secdev.org/scapy/src/24c165c032aad070c08eedcf96f030a939781c3f/scapy/utils.py
'''

class NSRawPcapReader(RawPcapReader):
    def __init__(self, filename):
    	try:
        	RawPcapReader.__init__(self, filename)
        except Scapy_Exception as e:
        	if 'Not a pcap capture file (bad magic)' == str(e):
        		# try parsing as ns pcap
        		self.f.seek(0)
        		magic = self.f.read(4)
        		
        		if magic == '\xa1\xb2\x3c\x4d': # big endian
        			self.endian = '>'
        		elif magic == '\x4d\x3c\xb2\xa1': # little endian
        			self.endian = '<'
        		else:
        			raise Scapy_Exception("Not a pcap capture file (bad magic)")

        		hdr = self.f.read(20)
        		if len(hdr) < 20:
        			raise Scapy_Exception("Invalid pcap file (too short)")

        		vermaj, vermin, tz, sig, snaplen, linktype = struct.unpack((self.endian + "HHIIII"), hdr)
        		self.linktype = linktype
        	else:
        		raise e

class NSPcapReader(NSRawPcapReader):
    def __init__(self, filename):
        NSRawPcapReader.__init__(self, filename)
        try:
            self.LLcls = conf.l2types[self.linktype]
        except KeyError:
            warning("PcapReader: unknown LL type [%i]/[%#x]. Using Raw packets" % (self.linktype,self.linktype))
            self.LLcls = conf.raw_layer
    def read_packet(self, size=MTU):
        rp = NSRawPcapReader.read_packet(self,size)
        if rp is None:
            return None
        s,(sec,usec,wirelen) = rp
        
        try:
            p = self.LLcls(s)
        except KeyboardInterrupt:
            raise
        except:
            if conf.debug_dissector:
                raise
            p = conf.raw_layer(s)
        p.time = sec+0.000001*usec
        return p
    def read_all(self,count=-1):
        res = NSRawPcapReader.read_all(self, count)
        from scapy import plist
        return plist.PacketList(res,name = os.path.basename(self.filename))
    def recv(self, size=MTU):
        return self.read_packet(size)

def rdpcap(filename, count=-1):
    return NSPcapReader(filename).read_all(count=count)