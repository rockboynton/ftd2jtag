"""This is a small software application that interacts with a Xilinx XC2C64A chip mounted on a
CoolRunner-II development board.

The program:

1. Reads back the unique IDCODE from the XC2C64A chip, and compares it to the IDCODE in the chip’s datasheet.
2. Blinks D1 and D2 (alternating) at 0.5Hz

Wiring:
C232HM  |  XC2C64A
------------------
Red     |  JTAG 3V3
Black   |  JTAG GND
Orange  |  JTAG TCK
Yellow  |  JTAG TDI
Green   |  JTAG TDO
Brown   |  JTAG TMS
"""
from ftd2jtag.ftd2jtag import bsdl2json, setup_device
from ftd2jtag.idcode import get_real_idcode, get_idcode_opcode, verify_idcode
from ftd2jtag.extest import get_led_boundary_idx, get_boundary_length, blink_leds

# Serial number of the FTDI C232HM-DDHSL-0 USB dongle
FTDI_CABLE = b"FTXQNTSO"

LED_D1_PIN = 39
LED_D2_PIN = 38


bsdl_as_json = bsdl2json("tests/bsdl/xc2c64a_vq44.bsd")

real_idcode = get_real_idcode(bsdl_as_json)

idcode_opcode = get_idcode_opcode(bsdl_as_json)

led_d1, led_d2 = get_led_boundary_idx(bsdl_as_json, LED_D1_PIN, LED_D2_PIN)

boundary_length = get_boundary_length(bsdl_as_json)

device = setup_device(FTDI_CABLE)

print("Verifying IDCODE...")
if verify_idcode(device, real_idcode, idcode_opcode):
    print("\tIDCODE read matches real IDCODE "
          f"0x{int(real_idcode.replace('X', '0'), 2):04x} "
          "from BSDL file! ")
else:
    exit(-1)

cycles = 3
frequency = 0.5
print(f"Blinking LEDs at {frequency} Hz for {cycles} cycles...")
blink_leds(device, boundary_length, led_d1, led_d2, cycles=cycles, frequency=frequency)
print("Done!")

device.close()
