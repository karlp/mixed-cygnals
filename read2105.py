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
import time
from collections import namedtuple

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("MixedCygnals")

import usb.core
import usb.util

# See also http://lxr.free-electrons.com/source/include/uapi/linux/usb/ch9.h
# 0x41 = DIR_OUT | TYPE_VENDOR | RECIP_INTERFACE
REQTYPE_HOST_TO_INTERFACE = 0x41
REQTYPE_INTERFACE_TO_HOST = 0xc1
REQTYPE_HOST_TO_DEVICE = 0x40
REQTYPE_DEVICE_TO_HOST = 0xc0

class CP210x():
    def __init__(self, idVendor, idProduct):
        self.dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        if self.dev is None:
	    raise ValueError("CP210x device (%x:%x) found" % (idVendor, idProduct))

    def get_partnum(self):
        data = self.dev.ctrl_transfer(REQTYPE_DEVICE_TO_HOST, 0xff, 0x370b, 0, 1)
        self.bPartNumber = data[0]
        log.debug("partnumber = %#x", self.bPartNumber)
        

class CP2105(CP210x):
    def __init__(self):
        CP210x.__init__(self, 0x10c4, 0xea70)

    def get_device_mode(self):
        data = self.dev.ctrl_transfer(REQTYPE_DEVICE_TO_HOST, 0xff, 0x3711, 0, 2)
        log.info("Device mode ECI = %#x, SCI =%#x", data[0], data[1])

    def get_dual_port_config(self):
        data = self.dev.ctrl_transfer(REQTYPE_DEVICE_TO_HOST, 0xff, 0x370c, 0, 15)
        ss = ''.join(["%#x " % x for x in data])
        log.debug("received: %s", ss)
        
        DualPortConfig = namedtuple("DualPortConfig", "mode reset_latch suspend_latch sci eci device")
        dpc = DualPortConfig._make(struct.unpack(">HxxHxxxxHBBB", data))
        print(dpc)
        log.info("dpc = %r", dpc)
        return dpc

    def get_pins(self, port=0):
        data = self.dev.ctrl_transfer(REQTYPE_INTERFACE_TO_HOST, 0xff, 0x00c2, port, 1)
        log.debug("get_pins(%d) were %s", port, data)
        return data[0]

    # No clue what's going on here...
    def set_pins(self, port, pins):
        x = struct.pack("<H", pins & 0xff)
        log.debug("attempting to send %r", x)
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0xff, 0x37e1, port, x)
        log.debug("set pins(%d) write %d bytes", port, data)

    def set_pins_raw(self, port, pins):
        x = struct.pack("<H", pins)
        log.debug("attempting to send %r", x)
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0xff, 0x37e1, port, x)
        log.debug("set pins(%d) write %d bytes", port, data)

    def clear_pins(self, port, pins):
        x = struct.pack("<H", ((pins << 8) | 0x00ff))
        log.debug("attempting to send %r", x)
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0xff, 0x37e1, port, x)
        log.debug("set pins(%d) write %d bytes", port, data)

    def set_mhs(self, **kwargs):
        mhs = 0
        # This doesn't work properly for clearing things...
        if kwargs.get("rts", False):
            mhs |= 0x0002 | 0x0200
        if kwargs.get("dtr", False):
            mhs |= 0x0001 | 0x0100
            
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0x07, mhs, 0, None)

    def set_rts(self):
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0x07, 0x202, 0, None)

    def clear_rts(self):
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0x07, 0x200, 0, None)

    def get_mhs(self):
        data = self.dev.ctrl_transfer(REQTYPE_INTERFACE_TO_HOST, 0x08, 0, 0, 1)
        log.debug("mhs (mdmsts) = %s, %#x", data, data[0]) 

        

def kmain():
    dd = CP2105()
    dd.get_pins(0)
    dd.get_pins(1)
    """
    for i in range(5):
        dd.set_pins(0, i)
        dd.set_pins(1, i)
        time.sleep(0.5)
    dd.get_pins(0)
    dd.get_pins(1)

    print("turning off again")
    time.sleep(0.5)

    for i in range(5):
        dd.clear_pins(0, i)
        dd.clear_pins(1, i)
        time.sleep(0.5)
    dd.get_pins(0)
    dd.get_pins(1)
    """
    dd.set_pins_raw(0, 3<<8 | 0xff)
    print("should be off now!")
    time.sleep(2.5)
    
    dd.set_pins_raw(0, 1)
    time.sleep(0.5)
    dd.set_pins_raw(0, 2)
    time.sleep(0.5)
    dd.set_pins_raw(0, 3)
    time.sleep(0.5)
    dd.set_pins_raw(0, 3<<8 | 0xff)
    time.sleep(0.5)
    dd.set_pins_raw(0, 2<<8 | 0xff)
    time.sleep(0.5)
    dd.set_pins_raw(0, 1<<8 | 0xff)
    time.sleep(0.5)
    dd.set_pins_raw(0, 0<<8 | 0xff)
    time.sleep(0.5)

    dd.get_dual_port_config()
    
    

if __name__ == "__main__":
    kmain()
