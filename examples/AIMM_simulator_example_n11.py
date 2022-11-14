# Keith Briggs 2022-11-14
# Keith Briggs 2021-06-02 like n10, but better organized
# Keith Briggs 2021-05-12 add Q-learning
# until=200000; python3 AIMM_simulator_example_n11.py "${until}" | ./realtime_plotter_03.py -np=6 -tm="${until}" -ylims='{0: (0,6.5), 1: (-120,-50), 2: (-0.2,1.2), 3: (0,6), 4: (0,50), 5: (0,50)}' -ylabels='{0: "serving cell",  1: "rsrp[1]", 2: "cell-edge", 3: "split", 4: "throughput", 5: "average throughput"}' -fnb='img/AIMM_simulator_example_n11' -fst=2 -lw=1
# until=200000; python3 AIMM_simulator_example_n11.py "${until}" | ./realtime_plotter_03.py -np=6 -tm="${until}" -ylims='{0: (0,6.5), 1: (-120,-50), 2: (-0.2,1.2), 3: (0,6), 4: (0,50), 5: (0,50)}' -ylabels='{0: "serving cell",  1: "rsrp[1]", 2: "cell-edge", 3: "split", 4: "throughput", 5: "average throughput"}' -fnb='img/AIMM_simulator_example_n11' -fst=2 -lw=1

from sys import stderr,argv
from math import pi
from itertools import combinations
import numpy as np
from random import seed
from AIMM_simulator import Sim,Logger,MME,Scenario,RIC,np_array_to_str
from Q_learning_generalized_02 import Q_learner

def plot_scenario(sim,fn='examples/img/AIMM_simulator_example_n11_scenario'):
  import matplotlib.pyplot as plt
  from matplotlib.patches import Circle
  from matplotlib import cm
  from fig_timestamp import fig_timestamp
  cmap=plt.get_cmap('Pastel1')
  colors=cmap(np.linspace(0,1,8))
  colors=('r','g','b','c','m','y','k','w')
  fig=plt.figure(figsize=(10,8))
  ax=fig.add_subplot(1,1,1)
  ax.set_aspect('equal')
  ax.set_xlim(-8000.0,8000.0)
  ax.set_ylim(-7100.0,7100.0)
  ax.grid(linewidth=1,color='gray',alpha=0.25)
  for i,cell in enumerate(sim.cells):
    ax.add_patch(Circle(cell.xyz[:2],2700.0,color=colors[cell.i],alpha=0.5))
    ax.annotate('cell[%d]'%cell.i,1.3*cell.xyz[:2])
  na=30
  a=0.5e3
  ue_circle_radius=sim.params['ue_circle_radius']
  for i in range(na):
    c,s=np.cos(2*pi*i/na),np.sin(2*pi*i/na)
    ax.arrow(ue_circle_radius*c,ue_circle_radius*s,dx=-a*s,dy=a*c,width=50,color='k')
  ax.annotate('UE path',(2000,4000),fontsize=20)
  fig_timestamp(fig)
  fig.savefig(fn+'.pdf')
  fig.savefig(fn+'.png')
  print(f'e {fn}.pdf &',file=stderr)
  print(f'eog {fn}.png &',file=stderr)

class MyScenario(Scenario): # circle
  def loop(self):
    ue_circle_radius=self.sim.params['ue_circle_radius']
    while True:
      for ue in self.sim.UEs:
        tm=1e-2*self.sim.env.now/(2.0*pi)
        ue.xyz[0]=ue_circle_radius*np.cos(tm)
        ue.xyz[1]=ue_circle_radius*np.sin(tm)
      yield self.sim.wait(self.interval)

class ThroughputLogger(Logger):
  def loop(self):
    alpha0=0.2;  beta0=1.0-alpha0 # smoothing parameters
    alpha1=0.01; beta1=1.0-alpha1 # smoothing parameters
    ric_celledge=self.sim.ric.celledge # set in RIC
    tp_smoothed0=tp_smoothed1=0.0
    while True:
      for ue_i in range(1): # only log UE[0]
        rsrp=[cell.get_RSRP_reports_dict()[ue_i] for cell in self.sim.cells]
        serving_cell=self.sim.get_serving_cell(ue_i)
        serving_cell_i=serving_cell.i
        celledge=1 if (ue_i,serving_cell_i) in ric_celledge else 0
        xy=self.sim.get_UE_position(ue_i)[:2]
        tp=serving_cell.get_UE_throughput(ue_i)
        tp_smoothed0=alpha0*tp+beta0*tp_smoothed0
        tp_smoothed1=alpha1*tp+beta1*tp_smoothed1
        mask=serving_cell.get_subband_mask()
        split=serving_cell_i if mask[0]!=mask[-1] else 0
        self.f.write(f'{self.sim.env.now:.1f}\t{serving_cell_i}\t{rsrp[1]:.2f}\t{celledge}\t{split}\t{tp_smoothed0:.2f}\t{tp_smoothed1:.2f}\n')
      yield self.sim.wait(self.logging_interval)

class MyRIC(RIC):
  ql=Q_learner(reward=None,pick_max=False)
  celledge=set()
  def loop(self):
    n_ues=self.sim.get_nues()
    celledge_diff_threshold=15.0   # hyperparameter
    celledge_rsrp_threshold=-120.0 # hyperparameter
    alpha=0.5
    beta=1.0-alpha # smoothing parameters
    cells=self.sim.cells
    n_cells=len(cells)
    throughputs_smoothed=np.zeros(n_ues)
    split_ratio=self.sim.params['split_ratio']
    n_subbands=self.sim.params['n_subbands']
    ones =(1,)*n_subbands
    lower=[0,]*n_subbands
    upper=[1,]*n_subbands
    n_lower=int(split_ratio*n_subbands)
    for i in range(n_lower):
       lower[i]=1
       upper[i]=0
    lower,upper=tuple(lower),tuple(upper)
    print(f'lower mask={lower}, upper mask={upper}',file=stderr)
    # wait before switching on simple heuristic ...
    yield self.sim.wait(40000.0)
    # run simple heuristic...
    while self.sim.env.now<80000.0:
      rsrp=[cell.get_RSRP_reports_dict() for cell in cells]
      for ue_k in range(n_ues):
        serving_cell_i=self.sim.get_serving_cell_i(ue_k)
        for other_cell_i in range(n_cells):
          if other_cell_i==serving_cell_i: continue
          if rsrp[other_cell_i][ue_k]<celledge_rsrp_threshold: continue
          celledge=(rsrp[serving_cell_i][ue_k]-rsrp[other_cell_i][ue_k])<celledge_diff_threshold
          if celledge:
            cells[serving_cell_i].set_subband_mask(lower)
            cells[other_cell_i  ].set_subband_mask(upper)
            MyRIC.celledge.add((ue_k,serving_cell_i,))
            MyRIC.celledge.add((ue_k,other_cell_i,))
          else:
            cells[serving_cell_i].set_subband_mask(ones)
            cells[other_cell_i  ].set_subband_mask(ones)
            for x in ((ue_k,serving_cell_i),(ue_k,other_cell_i),):
              if x in MyRIC.celledge: MyRIC.celledge.remove(x)
      yield self.sim.wait(self.interval)
    # run Q-learning...
    state=(0,0,0) # initial state normal (no cell-edge UEs)
    MyRIC.ql.add_state(state,state)
    for i,j in combinations(range(n_cells),2):
      # state (i,j,l:bool) means that cells i and j have at least one
      # cell-edge UE, and that the spectrum is split (l)
      # actions will be to split spectrum (or not) between cells i and j
      actions=(False,True)
      MyRIC.ql.add_state((i,j,False),actions)
      MyRIC.ql.add_state((i,j,True), actions)
      MyRIC.ql.add_state((j,i,False),actions)
      MyRIC.ql.add_state((j,i,True), actions)
    while True:
      rsrp=[cell.get_RSRP_reports_dict() for cell in cells]
      for ue_k in range(n_ues):
        serving_cell_i=self.sim.get_serving_cell_i(ue_k)
        for other_cell_i in range(n_cells):
          if other_cell_i==serving_cell_i: continue
          if rsrp[other_cell_i][ue_k]<celledge_rsrp_threshold: continue
          celledge=(rsrp[serving_cell_i][ue_k]-rsrp[other_cell_i][ue_k])<celledge_diff_threshold
          if celledge:
            MyRIC.celledge.add((ue_k,serving_cell_i,))
            MyRIC.celledge.add((ue_k,other_cell_i,))
            action=MyRIC.ql.episode((serving_cell_i,other_cell_i,True,))
            if action: # ql is telling us to split the band
              cells[serving_cell_i].set_subband_mask(lower)
              cells[other_cell_i  ].set_subband_mask(upper)
              state=(serving_cell_i,other_cell_i,True)
            else: # ql is telling us to unsplit the band
              cells[serving_cell_i].set_subband_mask(ones)
              cells[other_cell_i  ].set_subband_mask(ones)
              state=(serving_cell_i,other_cell_i,False)
            while True: # wait for a throughput report
              yield self.sim.wait(1.0)
              tp=np.array([cells[serving_cell_i].get_UE_throughput(ue_k)[0] for ue in self.sim.UEs])
              if not np.any(np.isneginf(tp)): break
            MyRIC.ql.update_Q(state,reward=np.min(tp)**1)
          else: # not celledge
            for x in ((ue_k,serving_cell_i),(ue_k,other_cell_i),):
              if x in MyRIC.celledge: MyRIC.celledge.remove(x)
            state=(0,0,0) # set state
            cells[serving_cell_i].set_subband_mask(ones)
            cells[other_cell_i  ].set_subband_mask(ones)
            #state=(serving_cell_i,other_cell_i,False) # set state
            #state=MyRIC.ql.episode(state)
            #if state[2]: # ql is telling us to split the band
            #  cells[serving_cell_i].set_subband_mask(lower)
            #  cells[other_cell_i  ].set_subband_mask(upper)
            #else: # ql is telling us to unsplit the band
            #  cells[serving_cell_i].set_subband_mask(ones)
            #  cells[other_cell_i  ].set_subband_mask(ones)
            #while True: # wait for a throughput report
            #  yield self.sim.wait(10.0)
            #  tp=np.array([cells[serving_cell_i].get_UE_throughput(ue_k)[0] for ue in self.sim.UEs])
            #  if not np.any(np.isneginf(tp)): break
            #MyRIC.ql.update_Q(state,reward=np.min(tp)**1)
      yield self.sim.wait(self.interval)
  def finalize(self):
    MyRIC.ql.show_Q(f=stderr)

def example_n11(until=1000,n_ues=1,radius=5000.0,power_dBm=30.0,n_subbands=8):
  sim=Sim(params={'ue_circle_radius': 45*radius/50, 'n_subbands': n_subbands, 'split_ratio': 0.9})
  # 7 cells in a hexagonal arrangement
  # centre cell
  sim.make_cell(xyz=(0.0,0.0,10.0),n_subbands=n_subbands,power_dBm=power_dBm)
  # ring of six...
  for i in range(6):
    theta=2*pi*i/6
    x=radius*np.cos(theta)
    y=radius*np.sin(theta)
    sim.make_cell(xyz=(x,y,10.0),n_subbands=n_subbands,power_dBm=power_dBm)
  for i in range(n_ues):
    sim.make_UE(xyz=(10*i,10*i,2.0),reporting_interval=2.0,verbosity=1).attach_to_nearest_cell()
  sim.add_loggers([
    ThroughputLogger(sim,logging_interval=50.0),
  ])
  sim.add_scenario(MyScenario(sim,interval=1.0))
  sim.add_MME(MME(sim,interval=10.0,verbosity=0))
  sim.add_ric(MyRIC(sim,interval=10.0))
  plot_scenario(sim)
  sim.run(until=until)

if __name__ == '__main__':
  np.random.seed(1)
  seed(1)
  until=1000
  argc=len(argv)
  if argc>1: until=float(argv[1])
  example_n11(until)
