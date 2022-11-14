# Keith Briggs 2022-11-14 add Q-learning
# python3 AIMM_simulator_example_n9.py | cut -f 1,5 | p
# until=20000; python3 AIMM_simulator_example_n9.py "${until}" | ./realtime_plotter.py -np=6 -tm="${until}" -ylims='{0: (-0.5,1.5), 1: (-50,-40), 2: (-50,-40), 3: (-0.5,1.5), 4: (-0.5,1.5), 5: (0,40)}' -ylabels='{0: "serving cell",  1: "rsrp0", 2: "rsrp1", 3: "cell-edge", 4: "split", 5: "throughput",}' -fnb='img/AIMM_simulator_example_n9' -fst=2 -lw=2

from sys import stderr,argv
from itertools import combinations
import numpy as np
from random import seed
from AIMM_simulator import Sim,Logger,MME,Scenario,RIC,np_array_to_str
from Q_learning_generalized_01 import Q_learner

class MyScenario(Scenario):
  def loop(self,interval=0.1,speed=2.0):
    a=speed/1.414
    more_UEs=False
    while True:
      if not more_UEs and self.sim.env.now>15000.0:
        for i in range(2):
          ue=self.sim.make_UE(xyz=(450.0+20*i,550.0+20*i,2.0),verbosity=1)
          ue.attach_to_strongest_cell_simple_pathloss_model()
          print(f'ue[{i}]=',ue,file=stderr)
          # FIXME the next two steps should be automatic when new UEs are added!
          #self.sim.env.process(ue.run_rsrp_reports())
          #self.sim.env.process(ue.run_subband_cqi_report())
        more_UEs=True
      # a random walk, but UE[0] staying near (500,500)... 
      for ue in self.sim.UEs: #[:1]:
        dx=a*np.random.standard_normal(1)
        dy=a*np.random.standard_normal(1)
        if   ue.xyz[0]>520.0: ue.xyz[0]-=abs(dx)
        elif ue.xyz[0]<480.0: ue.xyz[0]+=abs(dx)
        else:                 ue.xyz[0]+=dx
        if   ue.xyz[1]>520.0: ue.xyz[1]-=abs(dy)
        elif ue.xyz[1]<480.0: ue.xyz[1]+=abs(dy)
        else:                 ue.xyz[1]+=dy
      for ue in self.sim.UEs[1:]: # don't confine other UEs
        ue.xyz[:2]+=a*np.random.standard_normal(2)
      yield self.sim.wait(interval)

class ThroughputLogger(Logger):
  def loop(self):
    #self.f.write('#time\tcell\tUE\tx\ty\tthroughput\n')
    alpha=0.02; beta=1.0-alpha # smoothing parameters
    ric_celledge=self.sim.ric.celledge # set in RIC
    tp_smoothed=0.0
    while True:
      rsrp=[cell.get_RSRP_reports_dict() for cell in self.sim.cells]
      for cell in self.sim.cells:
        for ue_i in cell.reports['cqi']:
          # next not needed as will never be true
          #if cell.i!=self.sim.UEs[ue_i].get_serving_cell().i: continue
          if ue_i>0: continue # only log UE[0]
          celledge=1 if ue_i in ric_celledge else 0
          xy=self.sim.get_UE_position(ue_i)[:2]
          #print(rsrp)
          tp=cell.get_UE_throughput(ue_i)
          tp_smoothed=alpha*tp+beta*tp_smoothed
          mask=cell.get_subband_mask()
          split=1 if mask[0]!=mask[1] else 0 
          self.f.write(f'{self.sim.env.now:.1f}\t{cell.i}\t{rsrp[cell.i][ue_i]:.2f}\t{rsrp[cell.i][ue_i]:.2f}\t{celledge}\t{split}\t{tp_smoothed:.2f}\n') # no x,y
      yield self.sim.wait(self.logging_interval)

class RSRPLogger(Logger):
  def loop(self):
    while True:
      rep=[cell.get_RSRP_reports() for cell in self.sim.cells]
      print(self.sim.env.now,rep)
      yield self.sim.wait(self.logging_interval)

class MyRIC(RIC):
  ql=Q_learner(reward=None)
  celledge=set()
  def loop(self,interval=10):
    def reward(x):
      return throughputs_smoothed[0]
    n_ues=self.sim.get_nues()
    celledge_rsrp_threshold=2.0 # hyperparameter
    alpha=0.1
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
    yield self.sim.wait(5000.0) # wait before switching on Q-learner
    while True:
      rsrp=[cell.get_RSRP_reports_dict() for cell in cells]
      while True: # wait for a throughput report
        throughputs=np.array([cells[ue.serving_cell.i].get_UE_throughput(ue.i) for ue in self.sim.UEs])
        if not np.any(np.isneginf(throughputs)): break
        yield self.sim.wait(1.0) 
      throughputs/=n_ues # average throughput per UE
      if np.all(throughputs>0.0):
        throughputs_smoothed=alpha*throughputs+beta*throughputs_smoothed
      #print(rsrp,throughputs,throughputs_smoothed)
      # look for cell-edge UEs...
      # FIXME do we need an min rsrp threshold?
      # The condition should really be that the serving cell and exactly 
      # one other cell have nearly equal rsrp
      for ue_k in range(1): #n_ues):
        serving_cell_i=self.sim.get_serving_cell_i(ue_k)
        for cell_i,cell_j in combinations(range(n_cells),2):
          #if self.sim.env.now>14000: print('celledge:',self.sim.env.now,ue_k,rsrp[cell_i][ue_k],rsrp[cell_j][ue_k],file=stderr)
          if serving_cell_i not in (cell_i,cell_j): continue
          if abs(rsrp[cell_i][ue_k]-rsrp[cell_j][ue_k])<celledge_rsrp_threshold:
            MyRIC.celledge.add(ue_k)
            state=(cell_i,cell_j,True) # set state
            state=MyRIC.ql.episode(state)
            if state[2]: # ql is telling us to split the band
              cells[state[0]].set_subband_mask((1.0,0.0))
              cells[state[1]].set_subband_mask((0.0,1.0))
            else: # ql is telling us to unsplit the band
              cells[state[0]].set_subband_mask((1.0,1.0))
              cells[state[1]].set_subband_mask((1.0,1.0))
            yield self.sim.wait(5) # let throughputs adjust
            MyRIC.ql.update_Q(state,reward=throughputs_smoothed[0])
          else: # not cell-edge
            if ue_k in MyRIC.celledge: MyRIC.celledge.remove(ue_k)
            state=(cell_i,cell_j,False) # set state
            state=MyRIC.ql.episode(state)
            MyRIC.ql.update_Q(state,reward=throughputs_smoothed[0])
      yield self.sim.wait(interval)
  def finalize(self):
    MyRIC.ql.show_Q(f=stderr)

def example_n9(until=1000):
  sim=Sim()
  for i in range(2):
    sim.make_cell(xyz=(500.0+100*(i-0.5),500.0,10.0),n_subbands=2)
  for i in range(1):
    sim.make_UE(xyz=(500.0,500.0,2.0),verbosity=1).attach_to_nearest_cell()
  sim.add_loggers([
    ThroughputLogger(sim,logging_interval=5.0),
  ])
  sim.add_scenario(MyScenario(sim))
  sim.add_MME(MME(sim,interval=10.0,verbosity=0))
  sim.add_ric(MyRIC(sim,interval=1.0))
  sim.run(until=until)

if __name__ == '__main__':
  np.random.seed(1)
  seed(1)
  until=20000
  argc=len(argv)
  if argc>1: until=float(argv[1])
  example_n9(until)
