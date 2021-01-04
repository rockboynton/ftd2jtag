import ftd2xx as ftd
from bsdl_parser.bsdl import bsdlParser
from bsdl_parser.bsdl2json import BsdlSemantics
from .mpsse_commands import *

# MPSSE mode value (FTDI D2XX Programmer's guide §5.3)
MPSSE_MODE = 0x2

# FTDI C232HM-DDHSL-0 USB dongle JTAG pins (FTDI AN-108 §2.1)
TCK = 0x01
TDI = 0x02
TDO = 0x04
TMS = 0x08


def bsdl2json(filename):
    with open(filename) as f:
        text = f.read()
        parser = bsdlParser()
        ast = parser.parse(text, "bsdl_description", semantics=BsdlSemantics(), parseinfo=False)
        return ast.asjson()


def set_jtag_clock(d, hz):
    """Set the JTAG clock divisor (AN 108 §3.8.2)"""
    div = int((12e6 / (hz * 2)) - 1)
    d.write(bytes((SET_TCK_DIVISOR, div % 256, div // 256)))


def setup_device(device_serial):
    device = ftd.openEx(device_serial)  # open FTDI cable by serial number
    device.resetDevice()  # reset device mode
    device.setBitMode(0, MPSSE_MODE)  # set MPSSE mode
    set_jtag_clock(device, 3e6)  # use a 3 MHz clock
    device.write(bytes((SET_BITS_LOW, TMS, TCK | TDI | TMS)))  # configure outputs
    return device
