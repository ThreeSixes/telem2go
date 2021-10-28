"""
"""

from pprint import pprint

from lib import *

frames = [
    "A8001EBCAEE57730A80106DE1344",
    "8D4840D6202CC371C32CE0576098",
    "8D75804B580FF2CF7E9BA6F701D0",
    "8D75804B580FF6B283EB7A157117",
    "8D40621D58C382D690C8AC2863A7",
    "5D484FDEA248F5",
    "8D485020994409940838175B284F",
    "8DA05F219B06B6AF189400CBC33F"
]

for frame in frames:
    pprint(ADSBFrame(frame))

#icao_aa = "0xffeed0"
#icao_aa = bytearray([0xff, 0xee, 0xd0])
#icao_aa = 16772816
#print(int(IcaoAA(icao_aa)))
#print(str(IcaoAA(icao_aa)))

#ais_str_bytes = bytearray([0x2C, 0xC3, 0x71, 0xC3, 0x2C, 0xE0])
#print(str(AisStr(ais_str_bytes)))
#pprint(AdsbCrc.compute_crc_table())