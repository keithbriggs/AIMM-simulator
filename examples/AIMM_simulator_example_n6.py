# Keith Briggs 2022-11-14 hetnet example, no UE mobility.
# python3 AIMM_simulator_example_n6.py | ./realtime_plotter.py -np=1 -tm=100 -ylims='(0,0.25)' -ylabels='{0: "average downlink throughput over all UEs"}' -fnb='img/AIMM_simulator_example_n6'
from sys import path
path = "/home/davygx/Documents/haps_dev_ge/AIMM-simulator/src/AIMM_simulator" + path
from sys import stderr
from numpy.random import seed
from AIMM_simulator import Sim,Logger,Scenario

class MyScenario(Scenario):
  def loop(self):
    yield self.sim.wait(20) # wait 20 seconds
    for i in range(20): self.sim.make_cell(power_dBm=10.0,n_subbands=4)
    print(f'small cells added at t={self.sim.env.now:.2f}',file=stderr)
    yield self.sim.wait(20) # wait 20 seconds
    for UE in self.sim.UEs: UE.attach_to_strongest_cell_simple_pathloss_model()
    print(f'UEs reattached at t={self.sim.env.now:.2f}',file=stderr)
    yield self.sim.wait(20) # wait 20 seconds
    for i in range(9):      # set subband mask for macro cells
      self.sim.cells[i].set_subband_mask([1,0,0,0])
    for i in range(9,29):   # set subband mask for small cells
      self.sim.cells[i].set_subband_mask([0,1,1,1])
    print(f'cells masked at t={self.sim.env.now:.2f}',file=stderr)

class MyLogger(Logger):
  def loop(self):
    while True: # log average throughput over all UEs
      ave=self.sim.get_average_throughput()
      self.f.write(f'{self.sim.env.now:.2f}\t{ave:.4}\n')
      yield self.sim.wait(self.logging_interval)

def hetnet():
  sim=Sim()
  for i in range(9):
    sim.make_cell(xyz=(1000.0*(i//3),1000.0*(i%3),20.0),power_dBm=30.0,n_subbands=4)
  for i in range(50):
    sim.make_UE().attach_to_strongest_cell_simple_pathloss_model()
  sim.add_logger(MyLogger(sim,logging_interval=1.0e-1))
  sim.add_scenario(MyScenario(sim))
  sim.run(until=100)

seed(3)
hetnet()
