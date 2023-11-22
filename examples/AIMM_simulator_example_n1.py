# Keith Briggs 2022-11-14
# 1-cell, 4-UE, example with logger
from sys import path
path = ["/home/davygx/Documents/haps_dev_ge/AIMM-simulator/src/AIMM_simulator"] + path
from AIMM_simulator import Sim,Logger

sim=Sim()
cell=sim.make_cell()
ues=[sim.make_UE().attach(cell) for i in range(4)]
sim.add_logger(Logger(sim,logging_interval=10))
sim.run(until=100)
