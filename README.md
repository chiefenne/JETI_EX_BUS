
# JETI Ex Bus protocol (MicroPython)
[![GitHub](https://img.shields.io/github/license/mashape/apistatus.svg)](https://en.wikipedia.org/wiki/MIT_License)


A [JETI](http://www.jetimodel.com/en/) [Ex Bus protocol](http://www.jetimodel.com/en/Telemetry-Protocol/) implementation in [MicroPython](https://micropython.org/).
This will allow to use boards like RaspberyPi, ESP3286 or similar to act as sensors for Jeti RC [receivers](http://www.jetimodel.com/en/katalog/Duplex-2-4-EX/Receivers-EX/) and transmit telemetry data from the board to the receiver and thus back to the transmitter (i.e. RC controls like this [DC24](http://www.jetimodel.com/en/katalog/Transmitters/@produkt/DC-24/)).

>
> NOTE: This is currently rather a proof of concept and NOT ready for use.
> I use this mainly to learn about serial communication between microcontrollers and/or RC devices.
>

## Features (planned)

 - Pure Python (MicroPython) impementation of the Jeti Ex Bus protocol
 - Runs on boards which are supported by MicroPython ([list of available architechtures](https://github.com/micropython/micropython/tree/master/ports))
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
