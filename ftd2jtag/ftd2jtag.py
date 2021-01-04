import ftd2xx as ftd
from time import sleep
from bsdl_parser.bsdl import bsdlParser
from bsdl_parser.bsdl2json import BsdlSemantics

# Serial number of the FTDI C232HM-DDHSL-0 USB dongle
FTDI_CABLE = b"FTXQNTSO"

# MPSSE mode value (FTDI D2XX Programmer's guide §5.3)
MPSSE_MODE = 0x2

# FTDI C232HM-DDHSL-0 USB dongle JTAG pins (FTDI AN-108 §2.1)
TCK = 0x01
TDI = 0x02
TDO = 0x04
TMS = 0x08

# LED boundary scan output indices
# Pinout from http://dangerousprototypes.com/docs/CoolRunner-II_CPLD_breakout_board#Pinout_table
# Boundary register index from xc2c64a_vq44.bsd
LED_D2 = 190  # Pin 38 - IO_0 - boundary scan 190
LED_D1 = 94  # Pin 39 - IO_16 - boundary scan 94

# MPSSE commands (FTDI AN-108)
WRITE_BYTES_NVE_LSB = 0x19
WRITE_BITS_TMS_NVE = 0x4B
READ_BYTES_NVE_LSB = 0x2C
WRITE_BITS_NVE_LSB = 0x1B
SET_BITS_LOW = 0x80
SET_TCK_DIVISOR = 0x86


def main():
    bsdl_as_json = bsdl2json("tests/bsdl/xc2c64a_vq44.bsd")

    real_idcode = get_real_idcode(bsdl_as_json)
    idcode_opcode = get_idcode_opcode(bsdl_as_json)
    led_d1, led_d2 = get_led_boundary_idx(bsdl_as_json, 39, 38)

    device = setup_device(FTDI_CABLE)

    verify_idcode(device, real_idcode, idcode_opcode)

    blink_leds(device, led_d1, led_d2, 6)

    device.close()


def verify_idcode(device, idcode, idcode_opcode):
    idcode_read = read_idcode_manual(device, idcode_opcode)
    for i in range(len(idcode)):
        if idcode[i] == "X":
            continue  # ignore 'don't cares'
        elif idcode_read[i] != idcode[i]:
            print("IDCODE read does not match real IDCODE from BSDL file")
            print(f"\tidcode_read[{i}]: {idcode_read[i]}, idcode[{i}]: {idcode[i]}")
            exit(-1)

    print("IDCODE read matches real IDCODE from BSDL file! ")


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


def read_idcode(device):
    """Reads IDCODE coming out of reset"""
    data = bytearray()
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b11111))  # go to reset
    data.extend((WRITE_BITS_TMS_NVE, 3, 0b0010))  # go to shift-dr
    data.extend((READ_BYTES_NVE_LSB, 3, 0))  # read command
    device.write(bytes(data))  # send off MPSSE commands
    return device.read(4)[::-1].hex("_")  # return IDCODE


def read_idcode_manual(device, idcode_opcode):
    """Reads IDCODE using the opcode"""
    data = bytearray()
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b11111))  # go to reset
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00110))  # go to shift-ir
    data.extend((WRITE_BITS_NVE_LSB, 6, int(idcode_opcode)))  # shift in IDCODE opcode
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00111))  # go to shift-dr
    data.extend((READ_BYTES_NVE_LSB, 3, 0))  # read command
    device.write(bytes(data))  # send off MPSSE commands
    idcode = device.read(4)[::-1]
    return "".join(format(byte, "08b") for byte in idcode)


def blink_leds(device, led_d1, led_d2, seconds):
    """Turns the LEDs on"""
    data = bytearray()
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b11111))  # go to reset
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00110))  # go to shift-ir
    data.extend((WRITE_BITS_NVE_LSB, 6, 0b0000_0000))  # shift in EXTEST opcode
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00111))  # go to shift-dr
    data.extend((READ_BYTES_NVE_LSB, 23, 0))  # get extest
    device.write(bytes(data))  # send off MPSSE commands
    scan = device.read(24)
    data.clear()

    d2_on_d1_off = bytearray(scan)
    d2_off_d1_on = bytearray(scan)

    d2_on_d1_off[led_d2 // 8] |= 1 << (led_d2 % 8)  # D2 on
    d2_on_d1_off[led_d1 // 8] &= ~(1 << (led_d1 % 8))  # D1 off

    d2_off_d1_on[led_d2 // 8] &= ~(1 << (led_d2 % 8))  # D2 off
    d2_off_d1_on[led_d1 // 8] |= 1 << (led_d1 % 8)  # D1 on

    # blink leds at 0.5 Hz
    print(f"Blinking LEDS at 0.5Hz for {seconds} seconds")
    for _ in range(seconds // 2):
        data.clear()
        data.extend((WRITE_BYTES_NVE_LSB, 23, 0, *(d2_on_d1_off)))  # shift in boundary scan
        data.extend((WRITE_BITS_TMS_NVE, 4, 0b00111))  # go to shift-dr (update the tap controller)
        device.write(bytes(data))  # send off MPSSE commands
        sleep(1)

        data.clear()
        data.extend((WRITE_BYTES_NVE_LSB, 23, 0, *(d2_off_d1_on)))  # shift in boundary scan
        data.extend((WRITE_BITS_TMS_NVE, 4, 0b00111))  # go to shift-dr (update the tap controller)
        device.write(bytes(data))  # send off MPSSE commands
        sleep(1)


def get_led_boundary_idx(bsdl_as_json, led_d1_pin, led_d2_pin):
    pin_map = bsdl_as_json["device_package_pin_mappings"]
    pin_list = next(reg for reg in pin_map if reg["pin_map"])
    pin_map = pin_list["pin_map"]
    led_d1 = next(reg for reg in pin_map if str(led_d1_pin) in reg["pin_list"])
    led_d2 = next(reg for reg in pin_map if str(led_d2_pin) in reg["pin_list"])
    led_d1_port = led_d1["port_name"]
    led_d2_port = led_d2["port_name"]

    boundary_register = bsdl_as_json["boundary_scan_register_description"]["fixed_boundary_stmts"][
        "boundary_register"
    ]
    led_d1 = next(
        reg
        for reg in boundary_register
        if led_d1_port in reg["cell_info"]["cell_spec"]["port_id"]
        and reg["cell_info"]["cell_spec"]["function"] == "OUTPUT3"
    )
    led_d1_boundary_idx = led_d1["cell_number"]
    led_d2 = next(
        reg
        for reg in boundary_register
        if led_d2_port in reg["cell_info"]["cell_spec"]["port_id"]
        and reg["cell_info"]["cell_spec"]["function"] == "OUTPUT3"
    )
    led_d2_boundary_idx = led_d2["cell_number"]

    return int(led_d1_boundary_idx), int(led_d2_boundary_idx)


def get_idcode_opcode(bsdl_as_json):
    instruction_registers = bsdl_as_json["instruction_register_description"]["instruction_opcodes"]
    idcode_instruction = next(
        reg for reg in instruction_registers if reg["instruction_name"] == "IDCODE"
    )
    idcode_opcode = idcode_instruction["opcode_list"][0]
    return idcode_opcode


def get_real_idcode(bsdl_as_json):
    optional_registers = bsdl_as_json["optional_register_description"]
    idcode_attribute = next(reg for reg in optional_registers if reg["idcode_register"])
    idcode = idcode_attribute["idcode_register"]
    return idcode


def setup_device(device_serial):
    device = ftd.openEx(device_serial)  # open FTDI cable by serial number
    device.resetDevice()  # reset device mode
    device.setBitMode(0, MPSSE_MODE)  # set MPSSE mode
    set_jtag_clock(device, 3e6)  # use a 3 MHz clock
    device.write(bytes((SET_BITS_LOW, TMS, TCK | TDI | TMS)))  # configure outputs
    return device


if __name__ == "__main__":
    main()
