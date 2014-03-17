#!/usr/bin/python
# Attempt to reset the serial number of a CP2102 device.
# Made by reverse engineering the usb transfers.
# SiLabs actually provides a quite usable linux/windows/mac gui tool that
# does this, you don't need to use this at all, but it's an example of how to
# do this from a usb packet trace.  (I plan on doing some other stuff later)
# TODO - make it a nice class thing, with more usb decoding done.

import sys
import binascii
import struct
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("MixedCygnals")

import usb.core
import usb.util

dev = usb.core.find(idVendor=0x10c4, idProduct=0xea60)
if dev is None:
	raise ValueError("No CP2102 device found")

serial = sys.argv[1]
data = serial.encode("utf_16_le")
sformat = "bb%ds" % len(data)
# Plus 2 for string length, and magic for string descriptors
uu = struct.pack(sformat, len(data)+2, 3, data)
log.debug("Attempting to send %s", [x for x in uu]) 

# This came from the wireshark packet trace, frames 13-16
# needs to be 1 for second port on multi interface devices...
# http://community.silabs.com/t5/Interface-Products/CP2105-driver-questions/td-p/89191
# and https://lkml.org/lkml/2012/2/23/415
bInterfaceNumber = 0
assert dev.ctrl_transfer(0x40, 0xff, 0x3704, bInterfaceNumber, uu) == len(uu)
ret = dev.ctrl_transfer(0xc0, 0xff, 0x370b, bInterfaceNumber, 1)
sret = ''.join([chr(x) for x in ret])
if sret == '\x02':
	log.info("Serial successfully changed to %s", serial)
else:
	log.warn("Something went wrong? replied with %s", sret)
