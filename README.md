
# JETI Ex Bus protocol (MicroPython)
[![GitHub](https://img.shields.io/github/license/mashape/apistatus.svg)](https://en.wikipedia.org/wiki/MIT_License)


A [JETI](http://www.jetimodel.com/en/) [Ex Bus protocol](http://www.jetimodel.com/en/Telemetry-Protocol/) implementation in [MicroPython](https://micropython.org/).
This will allow to use boards like RaspberyPi, ESP3286 or similar to act as sensors for Jeti RC [receivers](http://www.jetimodel.com/en/katalog/Duplex-2-4-EX/Receivers-EX/) and transmit telemetry data from the board to the receiver and thus back to the transmitter (i.e. RC controls like this [DC24](http://www.jetimodel.com/en/katalog/Transmitters/@produkt/DC-24/)).


> NOTE: This is currently rather a proof of concept and NOT ready for use.
> I use this mainly to learn about serial communication between microcontrollers and/or RC devices.

> NOTE: My first tests will be done in a classical linear programming way (no asynchronous operations).
> I'll check how far I can come with this somewhat simpler approach.

> NOTE: Possibly I will be studying uasyncio which seems to be the proper way of implementing the Ex Bus protocol.
> For reference see [this example](https://github.com/peterhinch/micropython-async/blob/master/v3/as_demos/auart_hd.py).


## Features (planned)

 - Pure Python (MicroPython) impementation of the Jeti Ex Bus protocol
 - Runs on boards which are supported by MicroPython ([see code repository](https://github.com/micropython/micropython/tree/master/ports)) or [forum](https://forum.micropython.org/viewforum.php?f=10)
 - Simple firmware update via USB
 - Easy logging of sensor data on the board (SD card, etc.)

## Boards tested

 - [Pyboard](https://store.micropython.org/product/PYBv1.1) (this board is used for the development)
 - UPCOMING: [TINY2040](https://shop.pimoroni.com/products/tiny-2040)
 - UPCOMING: [ESP8266](https://en.wikipedia.org/wiki/ESP8266)

## Dependencies

 - [MicroPython](https://micropython.org/)



Andreas Ennemoser – andreas.ennemoser@aon.at

Distributed under the MIT license. See [LICENSE](https://raw.githubusercontent.com/chiefenne/PyAero/master/LICENSE) for more information.
