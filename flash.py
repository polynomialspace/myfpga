#!/usr/bin/env python3

from migen import *
from migen.build.platforms import icestick
plat = icestick.Platform()


#plat.create_programmer().load_bitstream("build/top.bin")
plat.create_programmer().flash(0,"build/top.bin")
