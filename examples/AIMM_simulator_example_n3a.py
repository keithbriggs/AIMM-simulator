# Keith Briggs 2022-11-14
from sys import path
path = ["/home/davygx/Documents/haps_dev_ge/AIMM-simulator/src/AIMM_simulator"] + path
from AIMM_simulator import Sim,Logger,MME,Scenario,np_array_to_str
from numpy.random import standard_normal,seed

def scenario_func(sim):
  for ue in sim.UEs: ue.xyz[:2]+=standard_normal(2)

def example_n3a():
  def logger_func(f):
    for cell in sim.cells:
      for ue_i in cell.reports['cqi']:
        xy=sim.get_UE_position(ue_i)[:2]
        tp=np_array_to_str(cell.get_UE_throughput(ue_i))
        f.write(f'{sim.env.now:.1f}\t{cell.i}\t{ue_i}\t{xy[0]:.0f}\t{xy[1]:.0f}\t{tp}\n')
  sim=Sim()
  for i in range(4): sim.make_cell()
  for i in range(8): sim.make_UE().attach_to_nearest_cell()
  sim.add_logger(Logger(sim,func=logger_func,header='#time\tcell\tUE\tx\ty\tthroughput Mb/s\n',logging_interval=1))
  sim.add_scenario(Scenario(sim,func=scenario_func))
  sim.add_MME(MME(sim,interval=10.0))
  sim.run(until=10)

seed(1)
example_n3a()
