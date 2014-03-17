#!/usr/bin/python
# 
# Basic hacking on reading/setting cp2105/cp210x settings
# via pyusb.  Information from silabs drivers, customization utilities
# and originally some wireshark usb reverse engineering
# Very rough, and be careful, cp2105 is OTP! not eeprom!

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

    def set_device_mode(self, eci, sci):
        """Pretty sure this is an OTP write to change gpio/modem modes"""
        x = struct.pack("<BBBB", eci, sci, 0, 0)
        n = self.dev.ctrl_transfer(REQTYPE_HOST_TO_DEVICE, 0xff, 0x3711, 0, x)
        log.debug("Wrote %d bytes to set device_mode", n)

    def get_dual_port_config(self):
        data = self.dev.ctrl_transfer(REQTYPE_DEVICE_TO_HOST, 0xff, 0x370c, 0, 15)
        ss = ''.join(["%#x " % x for x in data])
        log.debug("received: %s", ss)
        
        DualPortConfig = namedtuple("DualPortConfig", "mode reset_latch suspend_latch sci eci device")
        dpc = DualPortConfig._make(struct.unpack(">HxxHxxxxHBBB", data))
        log.info("dpc = %r", dpc)
        return dpc

    def set_dual_port_config(self, mode, reset_latch, suspend_latch, sci, eci, device):
        """
        Fully expect this to be an OTP write!
        """
        # I know everything else is little endian, but this is what the silabs code does...
        x = struct.pack(">HHHHHHBBB", mode, 0, reset_latch, mode, 0, suspend_latch, sci, eci, device)
        n = self.dev.ctrl_transfer(REQTYPE_HOST_TO_DEVICE, 0xff, 0x370c, 0, x)
        log.info("wrote %d bytes %s to reconfigure dual port", n, x)
        

    def get_pins(self, port=0):
        data = self.dev.ctrl_transfer(REQTYPE_INTERFACE_TO_HOST, 0xff, 0x00c2, port, 1)
        log.debug("get_pins(%d) were %s", port, data)
        return data[0]

    def set_pins(self, port, pins, mask=0xff):
        """
        having a separate mask parameter means you don't have to read first
        """
        x = struct.pack("<H", pins << 8 | mask)
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0xff, 0x37e1, port, x)

    def set_pins_raw(self, port, pins):
        x = struct.pack("<H", pins)
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0xff, 0x37e1, port, x)

    def set_mhs(self, **kwargs):
        mhs = 0
        # This doesn't work properly for clearing things...
        if kwargs.get("rts", False):
            mhs |= 0x0002 | 0x0200
        if kwargs.get("dtr", False):
            mhs |= 0x0001 | 0x0100
            
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0x07, mhs, 0, None)

    def get_mhs(self):
        data = self.dev.ctrl_transfer(REQTYPE_INTERFACE_TO_HOST, 0x08, 0, 0, 1)
        log.debug("mhs (mdmsts) = %s, %#x", data, data[0]) 

    def set_rts(self):
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0x07, 0x202, 0, None)

    def clear_rts(self):
        data = self.dev.ctrl_transfer(REQTYPE_HOST_TO_INTERFACE, 0x07, 0x200, 0, None)

        

def kmain():
    dd = CP2105()
    dd.get_device_mode()
    dd.get_pins(0)
    dd.get_pins(1)
    for i in range(8):
        dd.set_pins(0, i)
        dd.set_pins(1, i)
        time.sleep(0.3)
    dd.get_pins(0)
    dd.get_pins(1)
    dd.get_dual_port_config()
    # here goes nothing
    #DualPortConfig(mode=4433, reset_latch=65278, suspend_latch=65278, sci=16, eci=16, device=48)
    # rx/tx leds for SCI, and txled/rs485 for ECI
    #dd.set_dual_port_config(4433, 65278, 65278, 0x13, 0x15, 48)
    #dd.get_dual_port_config()
    

if __name__ == "__main__":
    kmain()
