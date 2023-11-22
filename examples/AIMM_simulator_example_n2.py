# Keith Briggs 2022-11-14
# 1-cell, 4-UE, example with logger and scenario
from sys import path
path = ["/home/davygx/Documents/haps_dev_ge/AIMM-simulator/src/AIMM_simulator"] + path
from AIMM_simulator import Sim,Logger,MME,Scenario
from numpy.random import standard_normal

class MyScenario(Scenario):
  def loop(self,interval=0.1):
    while True:
      for ue in self.sim.UEs: ue.xyz[:2]+=standard_normal(2)
      yield self.sim.wait(interval)

def example_n2():
  sim=Sim()
  cell=sim.make_cell()
  for i in range(4): sim.make_UE().attach(cell)
  sim.add_logger(Logger(sim,logging_interval=10))
  sim.add_scenario(MyScenario(sim))
  sim.add_MME(MME(sim,interval=10.0))
  sim.run(until=500)

example_n2()
