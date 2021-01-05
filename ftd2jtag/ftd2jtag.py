"""JTAG setup support and utility functions """

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
    """Parses a BSDL file into JSON

    Args:
        filename (str): BSDL file (.bsd)

    Returns:
        dict: BSDL file as JSON
    """
    with open(filename) as f:
        text = f.read()
        parser = bsdlParser()
        ast = parser.parse(text, "bsdl_description", semantics=BsdlSemantics(), parseinfo=False)
        return ast.asjson()


def set_jtag_clock(device, hz):
    """Set the JTAG clock divisor (AN 108 §3.8.2)

    Args:
        device (FTD2XX): FTDI device
        hz (float | int): desired frequency of the JTAG clock
    """
    div = int((12e6 / (hz * 2)) - 1)
    device.write(bytes((SET_TCK_DIVISOR, div % 256, div // 256)))


def setup_device(device_serial):
    """Sets up the device to control a DUT using JTAG

    Args:
        device_serial (bytes): bytes object representing the serial number of the FTDI device

    Returns:
        FTD2XX: FTDI device
    """
    device = ftd.openEx(device_serial)  # open FTDI cable by serial number
    device.resetDevice()  # reset device mode
    device.setBitMode(0, MPSSE_MODE)  # set MPSSE mode
    set_jtag_clock(device, 3e6)  # use a 3 MHz clock
    device.write(bytes((SET_BITS_LOW, TMS, TCK | TDI | TMS)))  # configure outputs
    return device


def get_opcode_length(bsdl_as_json):
    """Gets the OPCODE length

    Args:
        bsdl_as_json (dict): BSDL file parsed into JSON

    Returns:
        int: opcode length
    """
    opcode_length = bsdl_as_json["instruction_register_description"]["instruction_length"]
    return int(opcode_length)
