# Keith Briggs 2022-11-11
# Just test that the imports work, and the simulation runs.

from AIMM_simulator import Sim,Cell,UE,MME,Logger,InH_pathloss

if __name__=='__main__':
  sim=Sim()
  sim.make_cell()
  ue=sim.make_UE(pathloss_model=InH_pathloss())
  ue.attach_to_nearest_cell()
  sim.add_logger(Logger(sim,logging_interval=10))
  sim.run(until=100)
  print(f'ue.get_SINR_dB={ue.get_SINR_dB()}')
