# pystatusb
Control a fit-statUSB from python

The statUSB is a tiny, USB LED that can be set display various colors and sequences. This library allows easy control of it from python.

Use one of the simple helpers to set a color or sequence. After sending the configuration, the device will keep it without the python program running, and persist until a different color command is sent or the device is unplugged.

```python
from pystatusb import StatUSB, Colors

led = StatUSB()                  # Auto-detect the device
led.set_transistion_time(200)    # Set the fade time to 200ms between each color
led.set_color_rgb(0xff0000)      # 100% bright red
led.set_color(Colors.VIOLET, 20) # 20% bright violet
led.set_sequence("#0000FF-0500#00FFFF-0250#0000-0250") # Blue for 0.5 sec, cyan for 0.25 sec, off for 0.25 sec
```
