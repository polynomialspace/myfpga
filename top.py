#!/usr/bin/env python3
from migen import *
from migen.build.platforms import icestick
from migen.genlib.cdc import MultiReg


class Blink(Module):
    def __init__(self, sig, leds=[], led=0, speed=0):
        nbits = 26 - speed # 2**25 roughly ends up being 1s
        ctr = Signal(nbits)

        self.comb += leds[led].eq(ctr[nbits-1])
        self.sync += If(ctr > 0, ctr.eq(ctr - 1))
        self.sync += If(sig, ctr.eq(~(1<<nbits)))

class ClkDiv(Module):
    def __init__(self, freq):
        sys_clk = icestick.Platform.default_clk_period
        bit_cyc = round((1e9 / sys_clk) / freq)
        self.tick = Signal()
        timer = Signal(max = 1 + bit_cyc)

        self.sync += \
            If(timer == 0,
                timer.eq(bit_cyc)
            ).Else(
                timer.eq(timer - 1)
            )
        self.comb += self.tick.eq(timer == 0)

class SendUartByte(Module):
    def __init__(self, tx, byte, clk, stb, ack):
        data = Signal(10)
        ctr = Signal(max = data.nbits)

        #                       .            END BITS
        #                       |........    DATA
        #                       |||||||||.   START BIT
        #                       vvvvvvvvvv
        self.comb += data.eq((0b1000000000) |
                               (byte<<1))
        self.sync += \
            If(clk.tick,
                If(stb,
                    tx.eq((data >> ctr) & 0b1),
                    If(ctr < (data.nbits - 1),
                        ctr.eq(ctr + 1)
                    ).Else (
                        ack.eq(1),
                        stb.eq(0),
                        ctr.eq(0)
                    )
                )
            )

class SendUartData(Module):
    def __init__(self, tx, clk, data):
        ctr = Signal(max=1 + len(data))
        stb = Signal(reset=1)
        ack = Signal()

        self.submodules += SendUartByte(tx, data[ctr], clk, stb, ack)

        self.sync += \
            If(clk.tick,
                If(ack & (ctr < (len(data)-1)),
                    ack.eq(0),
                    stb.eq(1),
                    ctr.eq(ctr + 1)
                )
            )

class Top(Module):
    def __init__(self, plat):
        leds = []
        for i in range(5):
            leds.append(plat.request("user_led"))
        serial = plat.request("serial")

        rx = Signal()
        tx = serial.tx
        self.specials += MultiReg(serial.rx, rx, reset=1) # uarts always held high

        self.submodules += Blink(sig=~rx, leds=leds, led=4, speed=3)
        self.submodules += Blink(sig=~tx, leds=leds, led=3, speed=3)

        clk = self.submodules.ClkDiv = ClkDiv(115200)
        self.submodules += SendUartData(tx, clk, Array(b"henlo\r\n"))

if __name__ == "__main__":
    plat = icestick.Platform()
    plat.build(Top(plat))
