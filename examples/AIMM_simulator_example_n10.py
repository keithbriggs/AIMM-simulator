# Keith Briggs 2022-11-14 like n9, but more cells and UEs
# Keith Briggs 2021-05-12 add Q-learning
# until=100000; python3 AIMM_simulator_example_n10.py "${until}" | ./realtime_plotter_03.py -np=6 -tm="${until}" -ylims='{0: (-0.5,6.5), 1: (-80,-25), 2: (-80,-25), 3: (-0.5,1.5), 4: (-0.5,1.5), 5: (0,10)}' -ylabels='{0: "serving cell",  1: "rsrp0", 2: "rsrp1", 3: "cell-edge", 4: "split", 5: "throughput",}' -fnb='img/AIMM_simulator_example_n10' -fst=2 -lw=1

from sys import stderr,argv
from itertools import combinations
import numpy as np
from random import seed
from AIMM_simulator import Sim,Logger,MME,Scenario,RIC,np_array_to_str
from Q_learning_generalized_01 import Q_learner

class MyScenario_OLD(Scenario):
  def loop(self,interval=1.0,speed=2.0):
    a=speed/1.414
    more_UEs=False
    bot,top=300.0,700.0
    while True:
      # a random walk, but UE[0] staying near (500,500)... 
      for ue in self.sim.UEs:
        dx=a*np.random.standard_normal(1)
        dy=a*np.random.standard_normal(1)
        if   ue.xyz[0]>top: ue.xyz[0]-=abs(dx)
        elif ue.xyz[0]<bot: ue.xyz[0]+=abs(dx)
        else:               ue.xyz[0]+=dx
        if   ue.xyz[1]>top: ue.xyz[1]-=abs(dy)
        elif ue.xyz[1]<bot: ue.xyz[1]+=abs(dy)
        else:               ue.xyz[1]+=dy
      yield self.sim.wait(interval)

class MyScenario(Scenario): # circle
  def loop(self,interval=1.0,speed=2.0):
    while True:
      for ue in self.sim.UEs:
        ue.xyz[0]=500.0+150.0*np.cos(1e-3*self.sim.env.now)+10*np.random.standard_normal(1)
        ue.xyz[1]=500.0+150.0*np.sin(1e-3*self.sim.env.now)+10*np.random.standard_normal(1)
      yield self.sim.wait(interval)

class RSRPLogger(Logger):
  def loop(self):
    while True:
      rep=[cell.get_RSRP_reports() for cell in self.sim.cells]
      print(self.sim.env.now,rep)
      yield self.sim.wait(self.logging_interval)

class ThroughputLogger(Logger):
  def loop(self):
    alpha=0.01; beta=1.0-alpha # smoothing parameters
    ric_celledge=self.sim.ric.celledge # set in RIC
    tp_smoothed=0.0
    while True:
      rsrp=[cell.get_RSRP_reports_dict() for cell in self.sim.cells]
      for cell in self.sim.cells:
        for ue_i in cell.reports['cqi']:
          if cell.i!=self.sim.UEs[ue_i].get_serving_cell().i: continue
          if ue_i>0: continue # only log UE[0]
          celledge=1 if (ue_i,cell.i,) in ric_celledge else 0
          xy=self.sim.get_UE_position(ue_i)[:2]
          tp=cell.get_UE_throughput(ue_i)
          tp_smoothed=alpha*tp+beta*tp_smoothed
          mask=cell.get_subband_mask()
          split=1 if mask[0]!=mask[2] else 0 
          self.f.write(f'{self.sim.env.now:.1f}\t{cell.i}\t{rsrp[cell.i][ue_i]:.2f}\t{celledge}\t{split}\t{tp_smoothed:.2f}\n') # no x,y
      yield self.sim.wait(self.logging_interval)

class MyRIC(RIC):
  ql=Q_learner(reward=None)
  celledge=set()
  def loop(self,interval=10):
    #def reward(x):
    #  return throughputs_smoothed[0]
    n_ues=self.sim.get_nues()
    celledge_diff_threshold=2.0   # hyperparameter
    celledge_rsrp_threshold=-70.0 # hyperparameter
    alpha=0.5
    beta=1.0-alpha # smoothing parameters
    cells=self.sim.cells
    n_cells=len(cells)
    state=0 # initial state normal (no cell-edge UEs)
    throughputs_smoothed=np.zeros(n_ues)
    MyRIC.ql.add_state(state,[0,])
    for i,j in combinations(range(n_cells),2):
      # state (i,j,l:bool) means that cells i and j have at least one 
      # cell-edge UE, and that the spectrum is split (l)
      # actions will be to split spectrum (or not) between cells i and j
      actions=((i,j,False),(i,j,True))
      MyRIC.ql.add_state((i,j,False),actions)
      MyRIC.ql.add_state((i,j,True), actions)
    MyRIC.ql.show_Q(f=stderr)
    yield self.sim.wait(10000.0) # wait before switching on Q-learner
    while True:
      rsrp=[cell.get_RSRP_reports_dict() for cell in cells]
      while True: # wait for a throughput report
        throughputs=np.array([cells[ue.serving_cell.i].get_UE_throughput(ue.i)[0] for ue in self.sim.UEs])
        if not np.any(np.isneginf(throughputs)): break
        yield self.sim.wait(1.0) 
      throughputs/=n_ues # average throughput per UE
      if np.all(throughputs>0.0):
        throughputs_smoothed=alpha*throughputs+beta*throughputs_smoothed
      #print(rsrp,throughputs,throughputs_smoothed)
      # look for cell-edge UEs...
      # The condition should really be that the serving cell and exactly 
      # one other cell have nearly equal rsrp
      for ue_k in range(1): # Assumes 1 UE!
        serving_cell_i=self.sim.get_serving_cell_i(ue_k)
        for cell_i,cell_j in combinations(range(n_cells),2):
          if serving_cell_i not in (cell_i,cell_j): continue
          if rsrp[cell_i][ue_k]<celledge_rsrp_threshold: continue
          if rsrp[cell_j][ue_k]<celledge_rsrp_threshold: continue
          if abs(rsrp[cell_i][ue_k]-rsrp[cell_j][ue_k])<celledge_diff_threshold:
            MyRIC.celledge.add((ue_k,cell_i,))
            MyRIC.celledge.add((ue_k,cell_j,))
            state=(cell_i,cell_j,True) # set state
            state=MyRIC.ql.episode(state)
            if state[2]: # ql is telling us to split the band
              if serving_cell_i==cell_i:
                cells[cell_i].set_subband_mask((1,1,0))
                cells[cell_j].set_subband_mask((0,0,1))
              else: # serving_cell_i==cell_j
                cells[cell_j].set_subband_mask((1,1,0))
                cells[cell_i].set_subband_mask((0,0,1))
            else: # ql is telling us to unsplit the band
              cells[cell_i].set_subband_mask((1,1,1))
              cells[cell_j].set_subband_mask((1,1,1))
            while True: # wait for a throughput report
              yield self.sim.wait(1.0) 
              tp=np.array([cells[serving_cell_i].get_UE_throughput(ue_k)[0] for ue in self.sim.UEs])
              if not np.any(np.isneginf(tp)): break
              yield self.sim.wait(1.0) 
            MyRIC.ql.update_Q(state,reward=np.min(tp))
            #yield self.sim.wait(5) # let throughputs adjust
            #MyRIC.ql.update_Q(state,reward=throughputs_smoothed[0])
          else: # not cell-edge
            if (ue_k,cell_i,) in MyRIC.celledge: MyRIC.celledge.remove((ue_k,cell_i,))
            if (ue_k,cell_j,) in MyRIC.celledge: MyRIC.celledge.remove((ue_k,cell_j,))
            state=(cell_i,cell_j,False) # set state
            #print(f'state={state}',file=stderr)
            state=MyRIC.ql.episode(state)
            while True: # wait for a throughput report
              yield self.sim.wait(1.0) 
              tp=np.array([cells[serving_cell_i].get_UE_throughput(ue_k)[0] for ue in self.sim.UEs])
              if not np.any(np.isneginf(tp)): break
              yield self.sim.wait(1.0) 
            MyRIC.ql.update_Q(state,reward=np.min(tp))
      yield self.sim.wait(interval)
  def finalize(self):
    MyRIC.ql.show_Q(f=stderr)

def example_n10(until=1000):
  sim=Sim()
  # 7 cells in a hexagonal arrangement
  for i in range(2): # top row
    sim.make_cell(xyz=(500.0+200*(i-0.5),500.0+200.0*0.866,10.0),n_subbands=3)
  for i in range(3): # middle row
    sim.make_cell(xyz=(500.0+200*(i-1.0),500.0,10.0),n_subbands=3)
  for i in range(2): # bottom row
    sim.make_cell(xyz=(500.0+200*(i-0.5),500.0-200.0*0.866,10.0),n_subbands=3)
  for i in range(4):
    sim.make_UE(xyz=(500.0+10*i,500.0+10*i,2.0),verbosity=1).attach_to_nearest_cell()
  sim.add_loggers([
    ThroughputLogger(sim,logging_interval=20.0),
    #RSRPLogger(sim,logging_interval=10.0),
  ])
  sim.add_scenario(MyScenario(sim))
  sim.add_MME(MME(sim,interval=10.0,verbosity=0))
  sim.add_ric(MyRIC(sim,interval=100.0))
  sim.run(until=until)

if __name__ == '__main__':
  np.random.seed(1)
  seed(1)
  until=1000
  argc=len(argv)
  if argc>1: until=float(argv[1])
  example_n10(until)
