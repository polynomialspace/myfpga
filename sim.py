from migen import *
from migen.build.platforms import icestick
from top import Top

def testbench():
    for _ in range(8192):
        yield

def RunSimulation(plat):
    run_simulation(Top(plat), testbench(),
                   clocks={"sys":plat.default_clk_period},
                   vcd_name="top.vcd")

if __name__ == "__main__":
    plat = icestick.Platform()
    RunSimulation(plat)
