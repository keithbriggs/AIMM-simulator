# Keith Briggs 2022-11-14 macros, with UE mobility and CQI logging.
# time python3 AIMM_simulator_example_n8.py && e example_n8.pdf &
from sys import path
path = "/home/davygx/Documents/haps_dev_ge/AIMM-simulator/src/AIMM_simulator" + path
from math import cos,sin,pi
import numpy as np
from numpy.random import seed,standard_normal
from AIMM_simulator import Sim,Logger,Scenario,MME

class MyScenario(Scenario):
  def loop(self,interval=1,radius=100.0,T=100.0,circle=False):
    while True: 
      for i,ue in enumerate(self.sim.UEs):
        if circle and i==0: # walk UE[0] around a circle
          t=self.sim.env.now
          ue.xyz[:2]=500+radius*cos(2*pi*t/T),500+radius*sin(2*pi*t/T)
        else: # random walk, mean speed=1
          ue.xyz[:2]+=standard_normal(2)/1.414
      yield self.sim.wait(interval)

class Histogram_Logger(Logger):
  # CQI histogram for UE[0]
  h_cqi0=np.zeros(16)
  h_cqi1=np.zeros(16)
  def loop(self):
    ue0=self.sim.UEs[0]
    while self.sim.env.now<0.5*self.sim.until:
      sc=ue0.get_serving_cell()
      cqi=ue0.get_CQI()
      if cqi is not None: self.h_cqi0[cqi[0]]+=1
      yield self.sim.wait(self.logging_interval)
    # half-time break - boost MIMO gain of all cells
    for cell in self.sim.cells:
      cell.set_MIMO_gain(6.0)
    while True:
      sc=ue0.get_serving_cell()
      cqi=ue0.get_CQI()
      if cqi is not None: self.h_cqi1[cqi[0]]+=1
      yield self.sim.wait(self.logging_interval)
  def finalize(s):
    hs=(s.h_cqi0/np.sum(s.h_cqi0),s.h_cqi1/np.sum(s.h_cqi1))
    plot_histograms(hs)

def plot_histograms(hs,fn='examples/img/AIMM_simulator_example_n8'):
  import matplotlib.pyplot as plt
  from matplotlib.patches import Rectangle
  from matplotlib.collections import PatchCollection
  from fig_timestamp import fig_timestamp
  ymax=max(max(h) for h in hs)
  fig=plt.figure(figsize=(8,8))
  ax=fig.add_subplot(1,1,1)
  ax.grid(linewidth=1,color='gray',alpha=0.25)
  ax.set_xlabel('CQI for UE[0]'); ax.set_ylabel('relative frequency')
  ax.set_xlim(0,15); ax.set_ylim(0,1.1*ymax)
  for h,fc,x in zip(hs,('b','r'),(-0.1,0.1),):
    ax.add_collection(PatchCollection([Rectangle((i+x,0),0.2,hi) for i,hi in enumerate(h)],facecolor=fc,alpha=0.8))
  ax.annotate('blue: normal\nred: after 6dB MIMO gain boost',(7,0.97*ymax),color='k',fontsize=14,bbox=dict(facecolor='w',edgecolor='k',boxstyle='round,pad=1'))
  fig_timestamp(fig,author='Keith Briggs',fontsize=8)
  for h,fc in zip(hs,('b','r'),):
    mean=sum(i*hi for i,hi in enumerate(h))/np.sum(h)
    ax.text(mean,-0.04,'mean',ha='center',va='center',rotation=90,size=8,bbox=dict(boxstyle='rarrow,pad=0.1',fc=fc,ec=fc,lw=1))
  fig.savefig(fn+'.pdf')
  fig.savefig(fn+'.png')

def example_n8():
  sim=Sim()
  for i in range(9):  # cells
    sim.make_cell(xyz=(300+200.0*(i//3),300+200.0*(i%3),10.0),power_dBm=10.0)
  for i in range(9): # UEs
    sim.make_UE(verbosity=1).attach_to_strongest_cell_simple_pathloss_model()
  sim.UEs[0].set_xyz([503.0,507.0,2.0])
  sim.UEs[0].attach_to_strongest_cell_simple_pathloss_model()
  logger=Histogram_Logger(sim,logging_interval=1.0)
  sim.add_logger(logger)
  sim.add_scenario(MyScenario(sim))
  sim.add_MME(MME(sim,verbosity=0,interval=20.0))
  sim.run(until=2*5000)

if __name__=='__main__':
  seed(1)
  example_n8()
