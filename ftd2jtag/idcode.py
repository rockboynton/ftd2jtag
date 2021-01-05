"""IDCODE JTAG support for ftd2jtag"""

from .mpsse_commands import *


def verify_idcode(device, idcode, idcode_opcode):
    """Verifies the read IDCODE matches the actual idcode

    Args:
        device (FTD2XX): FTDI device
        idcode (str): actual IDCODE
        idcode_opcode (str): opcode instruction to shift in to the chip's JTAG TAP

    Returns:
        bool: True if IDCODE matches else False
    """
    idcode_read = read_idcode_opcode(device, idcode_opcode)
    for i in range(len(idcode)):
        if idcode[i] == "X":
            continue  # ignore 'don't cares'
        elif idcode_read[i] != idcode[i]:
            print("IDCODE read does not match real IDCODE from BSDL file")
            print(f"\tidcode_read[{i}]: {idcode_read[i]}, idcode[{i}]: {idcode[i]}")
            return False

    return True


def read_idcode(device):
    """Reads IDCODE coming out of reset

    Args:
        device (FTD2XX): FTDI device

    Returns:
        str: IDCODE read from chip
    """
    data = bytearray()
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b11111))  # go to reset
    data.extend((WRITE_BITS_TMS_NVE, 3, 0b0010))  # go to shift-dr
    data.extend((READ_BYTES_NVE_LSB, 3, 0))  # read command
    device.write(bytes(data))  # send off MPSSE commands
    return device.read(4)[::-1].hex("_")  # return IDCODE


def read_idcode_opcode(device, idcode_opcode):
    """Reads IDCODE using the opcode

    See XILINX Programmer Qualification Specification Table 38

    Args:
        device (FTD2XX): FTDI device
        idcode_opcode (str): opcode instruction to shift in to the chip's JTAG TAP

    Returns:
        str: IDCODE read from chip
    """
    data = bytearray()
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b11111))  # go to reset
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00110))  # go to shift-ir
    data.extend((WRITE_BITS_NVE_LSB, 6, int(idcode_opcode)))  # shift in IDCODE opcode
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00111))  # go to shift-dr
    data.extend((READ_BYTES_NVE_LSB, 3, 0))  # read command
    device.write(bytes(data))  # send off MPSSE commands
    idcode = device.read(4)[::-1]
    return "".join(format(byte, "08b") for byte in idcode)


def get_idcode_opcode(bsdl_as_json):
    """Gets the IDCODE opcode using the BSDL file for the DUT

    Args:
        bsdl_as_json (dict): BSDL file parsed into JSON

    Returns:
        str: IDCODE opcode
    """
    instruction_registers = bsdl_as_json["instruction_register_description"]["instruction_opcodes"]
    idcode_instruction = next(
        reg for reg in instruction_registers if reg["instruction_name"] == "IDCODE"
    )
    idcode_opcode = idcode_instruction["opcode_list"][0]
    return idcode_opcode


def get_real_idcode(bsdl_as_json):
    """Gets the real IDCODE using the BSDL file of the DUT

    Args:
        bsdl_as_json (dict): BSDL file parsed into JSON

    Returns:
        str: real IDCODE
    """
    optional_registers = bsdl_as_json["optional_register_description"]
    idcode_attribute = next(reg for reg in optional_registers if reg["idcode_register"])
    idcode = idcode_attribute["idcode_register"]
    return idcode
