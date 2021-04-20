
# JETI Ex Bus protocol (Python)
[![GitHub](https://img.shields.io/github/license/mashape/apistatus.svg)](https://en.wikipedia.org/wiki/MIT_License)


A [JETI](http://www.jetimodel.com/en/) [Ex Bus protocol](http://www.jetimodel.com/en/Telemetry-Protocol/) implementation in Python or more specifically in [MicroPython](https://micropython.org/).
This will allow to use boards like RaspberyPi, ESP3286 or similar to act as a sensor hub for Jeti RC [receivers](http://www.jetimodel.com/en/katalog/Duplex-2-4-EX/Receivers-EX/) and transmit telemetry data from the board to the receiver and thus back to the transmitter (i.e. RC controls like this [DC24](http://www.jetimodel.com/en/katalog/Transmitters/@produkt/DC-24/)).


> NOTE: This is currently rather a proof of concept and NOT ready for use.
> I use this mainly to learn about serial communication between microcontrollers and/or RC devices.

> NOTE: My first tests will be done in a classical linear programming way (no asynchronous operations).
> I'll check how far I can come with this somewhat simpler approach.

> NOTE: Possibly I will be studying uasyncio which seems to be the proper way of implementing the Ex Bus protocol.
> For reference see [this example](https://github.com/peterhinch/micropython-async/blob/master/v3/as_demos/auart_hd.py).


## Features (planned)

 - Pure Python (MicroPython) impementation of the Jeti Ex Bus protocol
 - Runs on boards which are supported by MicroPython (see [forum](https://forum.micropython.org/viewforum.php?f=10) or [code repository](https://github.com/micropython/micropython/tree/master/ports))
 - Simple firmware update via USB
 - Easy logging of sensor data on the board (SD card, etc.)

## Boards tested

 - [Pyboard](https://store.micropython.org/product/PYBv1.1) 
   - This board is used for the development
   - STM32F405RG microcontroller
   - 168 MHz Cortex M4 CPU
 - Planned: [TINY2040](https://shop.pimoroni.com/products/tiny-2040)
 - Planned: [ESP8266](https://en.wikipedia.org/wiki/ESP8266)

## Dependencies

 - [MicroPython](https://micropython.org/)

## Test setup

The following image shows the components and connections as used during the development.

<!-- HTML syntax for image display allows to change the image size -->
<img src="docs/images/setup_Pyboard_JetiRex6.png" width="600" />

The Pyboard is in a small housing and a Jeti REX6 receiver is attached. The yellow wire (channel 6) splits into two wires (one with a 2.4kOhm resistor as per the Jeti specification) which are connected to TX(Y9) and RX(Y10) on UART(3) on the Pyboard. The black wire establishes a common ground. The receiver is powered by a 4S NiMH accumulator via channel 1. Channel 6 of the receiver was set to "Ex Bus" (see image below) in the device manager of the Jeti transmitter.

<br><br>
<img src="docs/images/EX_Bus_connection_cable.png" width="600" />

Connection cable for the EX Bus. A standard RC servo cable has 3 wires (signal, vcc, gnd). When connecting to an EX Bus channel on the receiver, one needs one wire (yellow here) which splits into two wires (yellow, green). One of them gets a resistor (2.4k<h<sub>&Omega;</sub>>) soldered in line (this one goes into GPIO Y9 (TX) on the Pyboard). The figure describes the setup for the referenced Pyboard setup. The yellow wire is the one that needs to be connected to the signal pin on the receiver. The black wire (as described above) establishes a common ground between receiver and Pyboard. Since the Pyboard is powered via USB here, we do not need to connect the vcc (red plus wire). This is obvioously only meaningful, while in a development phase on the computer. In normal operation, the Pyboard, when acting as a sensor or sensor hub, would need a proper voltage supply (which can come from the receiver).

<br><br>
<kbd> <!-- make a frame around the image -->
<img src="docs/images/EX_Bus_channel_6.png"/>
</kbd>

<br><br><br>
Andreas Ennemoser – andreas.ennemoser@aon.at

Distributed under the MIT license. See [LICENSE](https://raw.githubusercontent.com/chiefenne/PyAero/master/LICENSE) for more information.
