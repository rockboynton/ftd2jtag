"""EXTEST JTAG support for ftd2jtag"""

from .mpsse_commands import *
from time import sleep

def blink_leds(device, boundary_length, led_d1, led_d2, cycles=3, frequency=0.5):
    """Turns the LEDs on

    This code could be extended to blink more than 2 LEDs

    Args:
        device (FTD2XX): FTDI device
        boundary_length (int): boundary scan length
        led_d1 (int): boundary scan index of LED D1
        led_d2 (int): boundary scan index of LED D2
        cycles (int, optional): Number of cycles to run through. Defaults to 3.
        frequency (float, optional): Frequency to blink LEDs (alternating). Defaults to 0.5.
    """
    data = bytearray()
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b11111))  # go to reset
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00110))  # go to shift-ir
    data.extend((WRITE_BITS_NVE_LSB, 6, 0b0000_0000))  # shift in EXTEST opcode
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00111))  # go to shift-dr
    data.extend((READ_BYTES_NVE_LSB, boundary_length // 8 - 1, 0))  # get extest
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
        _write_boundary_scan(device, boundary_length, d2_on_d1_off)
        sleep(1 / (2 * frequency))

        _write_boundary_scan(device, boundary_length, d2_off_d1_on)
        sleep(1 / (2 * frequency))


def _write_boundary_scan(device, boundary_length, boundary_scan):
    """Writes the boundary scan to the DUT

    Args:
        device (FTD2XX): FTDI device
        boundary_scan (bytearray): boundary scan binary data
    """
    data = bytearray()
    data.extend((WRITE_BYTES_NVE_LSB, boundary_length // 8 - 1, 0, *(boundary_scan)))
    data.extend((WRITE_BITS_TMS_NVE, 4, 0b00111))  # go to shift-dr (update the tap controller)
    device.write(bytes(data))  # send off MPSSE commands


def get_boundary_length(bsdl_as_json):
    """Gets the length of the JTAG boundary scan

    Args:
        bsdl_as_json (dict): BSDL file parsed into JSON

    Returns:
        int: boundary length
    """
    boundary_length = bsdl_as_json["boundary_scan_register_description"]["fixed_boundary_stmts"][
        "boundary_length"
    ]
    return int(boundary_length)


def get_led_boundary_idx(bsdl_as_json, led_d1_pin, led_d2_pin):
    """Gets the boundary scan indices of the LEDs

    Uses the BSDL of the DUT

    Args:
        bsdl_as_json (dict): BSDL file parsed into JSON
        led_d1_pin (int): pin number of LED D1
        led_d2_pin (int): pin number of LED D2

    Returns:
        tuple: boundary indices (LED D1, LED D2)
    """
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

    led_d1_boundary_idx = _get_boundary_idx_from_port(boundary_register, led_d1_port)

    led_d2_boundary_idx = _get_boundary_idx_from_port(boundary_register, led_d2_port)

    return int(led_d1_boundary_idx), int(led_d2_boundary_idx)

def _get_boundary_idx_from_port(boundary_register, port):
    """Gets boundary scan index from output port

    Args:
        boundary_register (dict): boundary register from BSDL file as JSON
        port (str): port number

    Returns:
        str: boundary scan index of output port
    """
    cell = next(
        cell
        for cell in boundary_register
        if port in cell["cell_info"]["cell_spec"]["port_id"]
        and cell["cell_info"]["cell_spec"]["function"] == "OUTPUT3"
    )
    return cell["cell_number"]
