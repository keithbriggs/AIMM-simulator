# Keith Briggs 2022-11-14
# Example with antenna pattern
# python3 AIMM_simulator_example_n5.py | cut -f1,4 | p
# python3 AIMM_simulator_example_n5.py | ./realtime_plotter_03.py -np=3 -tm=500 -ylims='{0: (-100,100), 1: (-100,100), 2: (0,45)}' -ylabels='{0: "UE[0] $x$", 1: "UE[0] $y$", 2: "UE[0] throughput"}' -fnb='img/AIMM_simulator_example_n5'
from sys import path
path = ["/home/davygx/Documents/haps_dev_ge/AIMM-simulator/src/AIMM_simulator"] + path
from math import cos,sin,pi
from numpy.random import seed
from AIMM_simulator import Sim,Scenario,Logger,to_dB

class MyScenario(Scenario):
  # move the UE around a circle of specified radius, period T seconds
  def loop(self,interval=1.0,radius=100.0,T=100.0):
    while True:
      t=self.sim.env.now
      for ue in self.sim.UEs:
        ue.xyz[:2]=radius*cos(2*pi*t/T),radius*sin(2*pi*t/T)
      yield self.sim.wait(interval)

class MyLogger(Logger):
  def loop(self,ue_i=0):
    ' log for UE[ue_i] only, from reports sent to Cell[0]. '
    cell=self.sim.cells[0]
    UE=self.sim.UEs[ue_i]
    while True:
      tm=self.sim.env.now              # current time
      xy=UE.get_xyz()[:2]              # current UE position
      tp=cell.get_UE_throughput(ue_i)  # current UE throughput
      self.f.write(f'{tm:.1f}\t{xy[0]:.0f}\t{xy[1]:.0f}\t{tp}\n')
      yield self.sim.wait(self.logging_interval)

def example_n5():
  sim=Sim()
  pattern=lambda angle: 10.0+to_dB(abs(cos(0.5*angle*pi/180.0)))
  cell0=sim.make_cell(xyz=[  0.0,0.0,20.0],pattern=pattern)
  cell1=sim.make_cell(xyz=[200.0,0.0,20.0])
  ue=sim.make_UE(xyz=[100.0,0.0,2.0])
  ue.attach(cell0)
  sim.add_logger(MyLogger(sim,logging_interval=5))
  sim.add_scenario(MyScenario(sim))
  sim.run(until=500)

seed(1)
example_n5()
