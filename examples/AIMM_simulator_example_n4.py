# Keith Briggs 2022-11-14

from AIMM_simulator import Sim,Logger,MME,Scenario,RIC,np_array_to_str
from numpy.random import standard_normal,seed

class MyScenario(Scenario):
  def loop(self,interval=0.1):
    while True:
      for ue in self.sim.UEs: ue.xyz[:2]+=standard_normal(2)
      yield self.sim.wait(interval)

class MyLogger(Logger):
  def loop(self):
    self.f.write('#time\tcell\tUE\tx\ty\tthroughput\n')
    while True:
      for cell in self.sim.cells:
        for ue_i in cell.reports['cqi']:
          xy=self.sim.get_UE_position(ue_i)[:2]
          tp=np_array_to_str(cell.get_UE_throughput(ue_i))
          self.f.write(f't={self.sim.env.now:.1f}\tcell={cell.i}\tUE={ue_i}\tx={xy[0]:.0f}\ty={xy[1]:.0f}\ttp={tp}Mb/s\n')
      yield self.sim.wait(self.logging_interval)

class MyRIC(RIC):
  def loop(self,interval=10):
    while True:
      throughputs=[(self.sim.cells[ue.serving_cell.i].get_UE_throughput(ue.i),ue.i,) for ue in self.sim.UEs]
      throughputs.sort()
      mask=self.sim.UEs[throughputs[0][1]].serving_cell.subband_mask
      for i,bit in enumerate(mask):
        if bit==0:
          mask[i]=1
          break
      yield self.sim.wait(interval)

def example_n4():
  sim=Sim()
  for i in range(4): sim.make_cell()
  for i in range(8): sim.make_UE().attach_to_nearest_cell()
  sim.add_logger(MyLogger(sim,logging_interval=1))
  sim.add_scenario(MyScenario(sim))
  sim.add_MME(MME(sim,interval=10.0))
  sim.add_ric(MyRIC(sim,interval=10.0))
  sim.run(until=10)

seed(1)
example_n4()
