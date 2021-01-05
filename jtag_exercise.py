from ftd2jtag.ftd2jtag import bsdl2json, setup_device
from ftd2jtag.idcode import get_real_idcode, get_idcode_opcode, verify_idcode
from ftd2jtag.extest import get_led_boundary_idx, blink_leds

# Serial number of the FTDI C232HM-DDHSL-0 USB dongle
FTDI_CABLE = b"FTXQNTSO"


bsdl_as_json = bsdl2json("tests/bsdl/xc2c64a_vq44.bsd")

real_idcode = get_real_idcode(bsdl_as_json)

idcode_opcode = get_idcode_opcode(bsdl_as_json)

led_d1, led_d2 = get_led_boundary_idx(bsdl_as_json, 39, 38)

device = setup_device(FTDI_CABLE)

print("Verifying IDCODE...")
if verify_idcode(device, real_idcode, idcode_opcode):
    print(f"\tIDCODE read matches real IDCODE 0x{int(real_idcode.replace('X', '0'), 2):04x} from BSDL file! ")
else:
    exit(-1)

cycles = 3
frequency = 0.5
print(f"Blinking LEDs at {frequency} Hz for {cycles} cycles...")
blink_leds(device, led_d1, led_d2, cycles=cycles, frequency=frequency)

print("Done!")

device.close()