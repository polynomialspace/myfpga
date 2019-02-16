#!/usr/bin/env python3
from migen import *
from migen.build.platforms import icestick
from migen.genlib.cdc import MultiReg
from migen.genlib.fsm import FSM


class Blink(Module):
    def __init__(self, sig, led, clk_period, speed=0):
        sec = round(1e9/clk_period/speed)
        ctr = Signal(max=sec)

        self.comb += led.eq(ctr[ctr.nbits-1])
        self.sync += If(ctr > 0, ctr.eq(ctr - 1))
        self.sync += If(sig, ctr.eq(~(1<<ctr.nbits)))


class ClkDiv(Module):
    def __init__(self, freq, clk_period):
        bit_cyc = round((1e9 / clk_period) / freq)
        self.tick = Signal()
        timer = Signal(max = 1 + bit_cyc)

        self.sync += \
            If(timer == 0,
                timer.eq(bit_cyc)
            ).Else(
                timer.eq(timer - 1)
            )
        self.comb += self.tick.eq(timer == 0)


class UartSendByte(Module):
    def __init__(self, tx, byte, fsm, clk):
        data = Signal(10)
        ctr = Signal(max = data.nbits)
        #                       .            END BITS
        #                       |........    DATA
        #                       |||||||||.   START BIT
        #                       vvvvvvvvvv
        self.comb += data.eq((0b1000000000) |
                             (byte<<1))

        fsm.act("SEND_WAIT",
            If(clk.tick,
                NextValue(tx, (data >> ctr) & 0b1),
                If(ctr < (data.nbits - 1),
                    NextValue(ctr, ctr + 1),
                ).Else(
                    NextState("SEND_DONE"),
                    NextValue(ctr, 0),
                )
            )
        )


class SendUartData(Module):
    def __init__(self, tx, clk, data):
        ctr = Signal(max=1 + len(data))
        fsm = FSM(reset_state="SEND_WAIT")

        self.submodules += fsm
        self.submodules += UartSendByte(tx, data[ctr], fsm, clk)

        fsm.act("SEND_DONE",
            If(clk.tick,
                If(ctr < len(data),
                    NextValue(ctr, ctr + 1),
                    NextState("SEND_WAIT"),
                )
            )
        )


class Top(Module):
    def __init__(self, plat):
        clk_period = icestick.Platform.default_clk_period
        leds = []
        for i in range(5):
            leds.append(plat.request("user_led"))
        serial = plat.request("serial")

        rx = Signal()
        tx = serial.tx
        self.specials += MultiReg(serial.rx, rx, reset=1) # uarts always held high

        self.submodules += Blink(~rx, leds[4], clk_period, speed=3)
        self.submodules += Blink(~tx, leds[3], clk_period, speed=10)

        clk = self.submodules.ClkDiv = ClkDiv(115200, clk_period)
        self.submodules += SendUartData(tx, clk, Array(b"henlo\r\n"))


if __name__ == "__main__":
    plat = icestick.Platform()
    plat.build(Top(plat))
