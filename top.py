#!/usr/bin/env python3
from migen import *
from migen.build.platforms import icestick
from migen.genlib.cdc import MultiReg
#from enum import Enum


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

class UartState():
# One set of states for both ends of the UART. This feels hacky here.     #
#        STATE = VALUE  SETBY : DESCRIPTION                               #
    RECV_WAIT = 0b000 # Mux  : Receive byte via RecvUartByte
    SEND_WAIT = 0b001 # Mux  : Send byte via SendUartByte
    IDLE_WAIT = 0b010 # Mux  : Line not ready, wait via UartDetect
    RECV_DONE = 0b011 # Func : Tell UartMux we are finished receiving
    SEND_DONE = 0b100 # Func : Tell UartMux we are finished sending
    IDLE_DONE = 0b101 # Func : Tell UartMux line is detected and ready
    PROC_RECV = 0b110 # Mux  : Tell Parent we have a byte ready to process
    PROC_SEND = 0b111 # Mux  : Tell Parent we have finished sending a byte


class UartFSM(Module):
    def __init__(self, state, clk):
        self.sync += \
            If(clk.tick,
                If(state == UartState.RECV_DONE,
                    state.eq(UartState.PROC_RECV),
                ).Elif(state == UartState.SEND_DONE,
                    state.eq(UartState.PROC_SEND),
                ).Elif(state == UartState.IDLE_DONE,
                    state.eq(UartState.RECV_WAIT),
                )
            )

class UartMux(Module):
    def __init__(self, txpair, rxpair, byte, state, clk):
        assert(len(txpair) == len(rxpair))

        for pair in rxpair:
            self.submodules += UartFSM(state[i], clk)
            self.submodules += UartSendByte(txpair[i], byte[i], state[i], clk)
            self.submodules += UartRecvByte(rxpair[i], byte[i], state[i], clk)
            self.submodules += UartDetect(rxpair[i], txpair[i], state[i], clk)

class UartSendByte(Module):
    def __init__(self, tx, byte, state, clk):
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
                If(state == UartState.RECV_WAIT,
                    tx.eq((data >> ctr) & 0b1),
                    If(ctr < (data.nbits - 1),
                        ctr.eq(ctr + 1)
                    ).Else (
                        state.eq(UartState.RECV_DONE),
                        ctr.eq(0)
                    )
                )
            )

class SendUartData(Module):
    def __init__(self, tx, clk, data):
        ctr = Signal(max=1 + len(data))
        state = Signal(max=0b111, reset=UartState.RECV_WAIT)

        self.submodules += UartSendByte(tx, data[ctr], state, clk)

        self.sync += \
            If(clk.tick,
                If((state == UartState.RECV_DONE) & (ctr < (len(data)-1)),
                    ctr.eq(ctr + 1),
                    state.eq(UartState.RECV_WAIT),
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
