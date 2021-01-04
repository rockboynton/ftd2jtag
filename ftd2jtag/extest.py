from .mpsse_commands import *
from time import sleep

def blink_leds(device, led_d1, led_d2, cycles=3, frequency=0.5):
    """Turns the LEDs on

    This code could be extended to blink more than 2 LEDs

    """
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
    for _ in range(cycles):
        _write_boundary_scan(device, d2_on_d1_off)
        sleep(1 / (2 * frequency))

        _write_boundary_scan(device, d2_off_d1_on)
        sleep(1 / (2 * frequency))
        

def _write_boundary_scan(device, boundary_scan):
    data = bytearray()
    data.extend((WRITE_BYTES_NVE_LSB, 23, 0, *(boundary_scan)))  # shift in boundary scan
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00111))  # go to shift-dr (update the tap controller)
    device.write(bytes(data))  # send off MPSSE commands


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
