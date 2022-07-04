"""
Control Compulab fit-statUSB devices from python
https://fit-iot.com/web/product/fit-statusb/
"""

from enum import Enum
from io import BytesIO
import re
from serial import Serial
import serial.tools.list_ports as list_ports
import time

# Vendor and product ID for Compulab fit-statUSB with Texas Instruments chip
VENDOR_ID = 0x2047
PRODUCT_ID = 0x03df

class Colors(Enum):
    """Easy shortcuts for common colors"""
    RED =0xFF0000
    GREEN = 0x00FF00
    BLUE = 0x0000FF
    CYAN = BLUE + GREEN
    VIOLET = RED + BLUE
    WHITE = RED + GREEN + BLUE
    BLACK = 0

class StatUSB():
    """Wrapper for statUSB device"""

    def __init__(self, device=None, device_num=0):
        """
        Create a new StatUSB instance.

        by default the constructor will attempt to auto-discover a statUSB
        connected to your system. You may also pass an explicit device name, or
        for multiple devices you may pass the index of the device.

        Args:
            device (str): the full path to the device to use
            device_num (int): the zero-based index of the device to use, if
                there is more than one device connected
        """
        self.device = device
        if not self.device:
            found = None
            count = 0
            for port in list_ports.comports():
                if port.vid == VENDOR_ID and port.pid == PRODUCT_ID and device_num == count:
                    found = port
                    break
                count += 1
            if not found:
                raise FileNotFoundError("Could not find statUSB device")
            self.device = found.device

    def _translate_color(self, colorspec):
        """
        Translate a requested color specification into one that statUSB will
        correctly use, taking into account the peculiarites of the device.

        Args:
            colorspec (str): the 6 character color specification (RRGGBB)

        Returns:
            str: a modified colorspec with the closest color that the statUSB
                will accept
        """
        colors = re.findall("..", colorspec)
        for idx, clr in enumerate(colors):
            digit0 = int(clr[0], 16)
            digit1 = int(clr[1], 16)

            # If the first digit is 0-9 and even and the second digit is a-f, map a-c down and d-f up
            # eg 0x2a-0x2c => 0x29 and 0x2d-0x2f => 0x30
            if digit0 >= 0 and digit0 <= 9 and digit0 % 2 == 0:
                if digit1 >= 10 and digit1 <= 12:
                    digit1 = 9
                if digit1 >= 13 and digit1 <= 15:
                    digit0 += 1
                    digit1 = 0
            # If the first digit is 0-9 and odd and the second digit is f, map down one
            # eg 0x1f => 0x1e
            elif digit0 >= 1 and digit0 <= 9 and digit0 %2 == 1 and digit1 == 15:
                digit1 = 14
            # If the first digit is 10-14 and even and the second digit is f, map down one
            # eg 0x1f => 0x1e
            elif digit0 >= 10 and digit0 <= 14 and digit0 %2 == 0 and digit1 == 15:
                digit1 = 14
            # If the first digit is 10-14 and odd and the second digit is a-f, map a-c down and d-f up
            # eg 0x2a-0x2c => 0x29 and 0x2d-0x2f => 0x30
            elif digit0 >= 10 and digit0 <= 13 and digit0 % 2 == 1:
                if digit1 >= 10 and digit1 <= 12:
                    digit1 = 9
                if digit1 >= 13 and digit1 <= 16:
                    digit0 += 1
                    digit1 = 0
            # If the first digit is 14-15, map it back to 14, with the second digit no larger than e
            # eg 0xf1 => 0xe1 and 0xff => 0xee
            elif digit0 >= 14 and digit0 <= 15:
                digit0 = 14
                if digit1 >= 15:
                    digit1 = 14

            colors[idx] = "{:x}{:x}".format(digit0, digit1)

        return "".join(colors)

    def _write_message_get_response(self, message, initial_len, sentinel):
        """
        Write a message to the statUSB and read the response.

        This function will write a message to the statUSB serial interface, and
        then read the response back. The response up to and including the
        sentinel is returned to the caller, and any remaining data in the
        receive buffer is drained and discarded.

        Args:
            message (str): the message to send
            initial_len (int): the length of the expected response, as a hint
                for how much data to attempt to read back from the serial port
            sentinel (str): the string that marks the end of the response

        Returns:
            str: the response back from the statUSB device
        """
        stream = BytesIO()
        with Serial(self.device, baudrate=115200, timeout=1) as serport:
            # Write the message, then read back the echo (and discard)
            num = serport.write(message)
            serport.read(num)

            # Read the expected result length, then read until we hit the sentinel
            stream.write(serport.read(initial_len))
            while not stream.getvalue().decode().endswith(sentinel.decode()):
                stream.write(serport.read())
            # Drain anything else off the serial port buffer, discarding it
            while serport.in_waiting > 0:
                serport.read(serport.in_waiting)
            return stream.getvalue()

    def set_color_raw(self, color_spec):
        """
        Set the color of the device using a raw RGB string

        Args:
            color_spec (str): the color to set, in 6 character RGB (RRGGBB)
        """
        adjusted_spec = self._translate_color(color_spec)
        expected = b"\r\nSet Color, OK \r\n"
        result = self._write_message_get_response(b"#" + str.encode(adjusted_spec.strip()) + b"\n",
                                                  len(expected),
                                                  expected[-5:])
        if result.strip() != expected.strip():
            raise IOError("Could not set color: {} != {}".format(result, expected))

    def get_color(self):
        """
        Get the current color the device is displaying

        Returns:
            int: the RGB color of the device
        """
        message = b"G\n"
        initial_len = 9 # There will be at least 9 characters (0,0,0)\n\r
        sentinal = b")\n\r"
        result = self._write_message_get_response(message, initial_len, sentinal)
        # result should contain (x,y,z)
        m = re.search(rb"\(([a-f0-9]{1,2}),\s*([a-f0-9]{1,2}),\s*([a-f0-9]{1,2})\)", result)
        if m:
            red = int(m.group(1), 16)
            green = int(m.group(2), 16)
            blue = int(m.group(3), 16)
            return (red << (8 * 2)) + (green << (8 * 1)) + (blue << (8 * 0))

        raise ValueError("Could not parse result [{}]".format(result))

    def set_transition_time(self, time_ms):
        """
        Set the fade time used between color changes

        Args:
            time_ms (int): the fade time, in milliseconds
        """
        message = "F{:04}\n".format(time_ms).encode()
        expected = b"\r\nSet fading period, OK\r\n\r\n"
        result = self._write_message_get_response(message,
                                                  len(expected),
                                                  expected[-7:])
        if result.strip() != expected.strip():
            raise IOError("Could not set fade time: {} != {}".format(result, expected))

    def set_color_rgb(self, hexcolor):
        """
        Set the color of the device

        Args:
            hexcolor (int): the color to set, as an RGB integer
        """
        self.set_color_raw("{:06x}".format(hexcolor))

    def set_color(self, color, intensity_pct=100):
        """
        Set the color of the device using a sinple list of color shortcuts

        Args:
            color (Colors): the color to set from the Colors enum
            intensity_pct (int): the brightness to set, as a percentage
        """
        setpoint = (int((color.value >> (8 * 2) & 0xFF) * (intensity_pct/100.0)) << (8 * 2)) + \
                    (int((color.value >> (8 * 1) & 0xFF) * (intensity_pct/100.0)) << (8 * 1)) + \
                    (int((color.value >> (8 * 0) & 0xFF) * (intensity_pct/100.0)) << (8 * 0))
        
        self.set_color_raw("{:06x}".format(setpoint))

    def set_sequence(self, sequence_raw):
        """
        Set a color sequence to execute on the device.

        The statUSB supports sequences using the format #RRGGBB-tttt, repeated
        as many times as desired, where RRGGBB is the 6 character color and
        tttt is the time to display the color, in milliseconds. The sequence
        repeat until a new color command is sent. The transition time between
        the colors is controlled by thefade time.

        Example: B#FF0000-0100#00FFFF-0100#FFFFFF-1000#000000-0300
        This sets red for 0.1 sec, cyan for 0.1 sec, white for 1 sec, and off for 0.3 sec

        Args:
            sequence_raw (str): the sequence to set
        """
        message = b"B" + str.encode(sequence_raw) + b"\n"
        expected = b'\r\nSet sequence, OK \r\n'
        result = self._write_message_get_response(message,
                                                  len(expected),
                                                  expected[-6:])
        if result.strip() != expected.strip():
            raise IOError("Could not set sequence: {} != {}".format(result, expected))

if __name__ == "__main__":
    led = StatUSB()
    led.set_transition_time(100)

    while True:
        for cl in Colors:
            for pct in range(0, 101, 5):
                print("{} @ {}%".format(cl.name, pct))
                led.set_color(cl, pct)
                time.sleep(0.2)
