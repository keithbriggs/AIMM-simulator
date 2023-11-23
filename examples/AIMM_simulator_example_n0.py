# Keith Briggs 2022-11-14
# basic 1-cell, 1-UE, do-nothing example
#from sys import path
#path = ["/home/davygx/Documents/haps_dev_ge/AIMM-simulator/src/AIMM_simulator"] + path
from AIMM_simulator import Sim

sim=Sim()
sim.make_cell()
sim.make_UE().attach_to_nearest_cell()
sim.run(until=100)
