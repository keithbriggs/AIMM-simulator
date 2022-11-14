# Keith Briggs 2020-10-13
# Keith Briggs 2020-09-21
# map rsrp to reported value: 5G in Bullets p389 Table 237
# map SINR to CQI: https://uk.mathworks.com/help/5g/ug/5g-nr-cqi-reporting.html

from sys import exit
from bisect import bisect
from math import floor,ceil,log2
from functools import lru_cache
from dataclasses import dataclass
import numpy as np

SINR90pc=np.array([-float('inf'),-1.89,-0.82,0.95,2.95,4.90,7.39,8.89,11.02,13.32,14.68,16.62,18.91,21.58,24.88,29.32,float('inf'),])

# TS_38_214.pdf page 43 Table 5.2.2.1-2: 4-bit CQI Table for reporting CQI based on QPSK
# The CQI indices and their interpretations are given in Table 5.2.2.1-2 or Table 5.2.2.1-4 for reporting CQI based on QPSK, 16QAM and 64QAM. The CQI indices and their interpretations are given in Table 5.2.2.1-3 for reporting CQI based on QPSK, 16QAM, 64QAM and 256QAM.
_CQI_to_efficiency_QPSK=np.array([
[ 0,  float('inf'),float('inf')],
[ 1,   78,  0.1523],
[ 2,  120,  0.2344],
[ 3,  193,  0.3770],
[ 4,  308,  0.6016],
[ 5,  449,  0.8770],
[ 6,  602,  1.1758],
[ 7,  378,  1.4766],
[ 8,  490,  1.9141],
[ 9,  616,  2.4063],
[10,  466,  2.7305],
[11,  567,  3.3223],
[12,  666,  3.9023],
[13,  772,  4.5234],
[14,  873,  5.1152],
[15,  948,  5.5547],
])

# 38.214 Table 5.1.3.2-2
# http://www.techplayon.com/5g-nr-modulation-and-coding-scheme-modulation-and-code-rate/
# MCS Index: & Modulation Order Qm & Target code Rate x1024 R & Spectral efficiency\\
MCS_to_Qm_table_64QAM={
 0: ( 2,120,0.2344),
 1: ( 2,157,0.3066),
 2: ( 2,193,0.3770),
 3: ( 2,251,0.4902),
 4: ( 2,308,0.6016),
 5: ( 2,379,0.7402),
 6: ( 2,449,0.8770),
 7: ( 2,526,1.0273),
 8: ( 2,602,1.1758),
 9: ( 2,679,1.3262),
10: ( 4,340,1.3281),
11: ( 4,378,1.4766),
12: ( 4,434,1.6953),
13: ( 4,490,1.9141),
14: ( 4,553,2.1602),
15: ( 4,616,2.4063),
16: ( 4,658,2.5703),
17: ( 6,438,2.5664),
18: ( 6,466,2.7305),
19: ( 6,517,3.0293),
20: ( 6,567,3.3223),
21: ( 6,616,3.6094),
22: ( 6,666,3.9023),
23: ( 6,719,4.2129),
24: ( 6,772,4.5234),
25: ( 6,822,4.8164),
26: ( 6,873,5.1152),
27: ( 6,910,5.3320),
28: ( 6,948,5.5547),
29: ( 2,'reserved', 'reserved'),
30: ( 4,'reserved', 'reserved'),
31: ( 6,'reserved', 'reserved'),
}

def SINR_to_CQI(sinr_dB):
  return np.searchsorted(SINR90pc,sinr_dB)-1 # vectorized

# 2021-03-08...
#@lru_cache(maxsize=None)
#def SINR_to_CQI_cached(sinr_dB_int):
#  return np.searchsorted(SINR90pc,sinr_dB_int)-1 # vectorized

def CQI_to_efficiency_QPSK(cqi):
  # non-vectorized (TODO)
  if not 0<=cqi<=15: return float('nan')
  return _CQI_to_efficiency_QPSK[cqi,2]

def RSRP_report(rsrp_dBm):
  '''
    Convert RSRP report from dBm to standard range.

    Parameters
    ----------
    rsrp_dBm : float
        RSRP report in dBm 

    Returns
    -------
    int
        RSRP report in standard range.
  '''
  if rsrp_dBm==float('inf'): return 127
  if rsrp_dBm<-156.0: return 0
  if rsrp_dBm>=-31.0: return 126
  return int(rsrp_dBm+156.0)
 
@dataclass
class Radio_state:
  NofSlotsPerRadioFrame: int=20
  NofRadioFramePerSec: int  =100
  NRB_sc: int               =12
  Nsh_symb: int             =13
  NPRB_oh: int              =0
  nPRB: int                 =273
  Qm: int                   =8      # Modulation order
  v: int                    =4      # Number of Layers
  R: float                  =0.948
  MCS: int                  =20

def max_5G_throughput_64QAM(radio_state):
  # https://www.sharetechnote.com/html/5G/5G_MCS_TBS_CodeRate.html
  # converted from octave/matlab Keith Briggs 2020-10-09
  Qm,R,Spectral_efficiency=MCS_to_Qm_table_64QAM[radio_state.MCS]
  R/=1024.0 # MCS_to_Qm_table has 1024*R
  NPRB_DMRS=_DMRS_RE('type1','A',1,0)
  NREprime=radio_state.NRB_sc*radio_state.Nsh_symb-NPRB_DMRS-radio_state.NPRB_oh
  NREbar=min(156,NREprime)
  NRE=NREbar*radio_state.nPRB
  Ninfo=NRE*R*Qm*radio_state.v
  if Ninfo>3824:
    n=int(log2(Ninfo-24))-5
    Ninfo_prime=2**n*round((Ninfo-24)/(2**n))
    if R>0.25:
      C=ceil((Ninfo_prime+24)/8424) if Ninfo_prime>=8424 else 1.0
    else: # R<=1/4
      C=ceil((Ninfo_prime+24)/3816)
    TBS_bits=8*C*ceil((Ninfo_prime+24)/(8*C))-24
  else: # Ninfo<=3824
    Ninfo=max(24,2**n*int(Ninfo/2**n))
    print('Ninfo<=3824 not yet implemented - need 38.214 Table 5.1.3.2-2')
    exit(1)
  TP_bps=TBS_bits*radio_state.NofSlotsPerRadioFrame*radio_state.NofRadioFramePerSec
  return TP_bps/1024/1024

def _DMRS_RE(typ,mapping,length,addPos):
  # https://www.sharetechnote.com/html/5G/5G_MCS_TBS_CodeRate.html#PDSCH_TBS
  # converted from octave/matlab Keith Briggs 2020-10-09
  if typ=='type1':
    DMRSType='type1'
    if mapping=='A':  
      PDSCH_MappingType='A'
      if   addPos==0: dmrsRE=  6*length
      elif addPos==1: dmrsRE=2*6*length
      elif addPos==2: dmrsRE=3*6*length
      elif addPos==3: dmrsRE=4*6*length
      AdditionalPos=addPos
    elif mapping=='B': dmrsRE=6*length
  else:
    DMRSType='type2'
    if mapping=='B':
      PDSCH_MappingType='A'
      if   addPos==0: dmrsRE=  4*length
      elif addPos==1: dmrsRE=2*4*length
      elif addPos==2: dmrsRE=3*4*length
      elif addPos==3: dmrsRE=4*4*length
      AdditionalPos=addPos
    elif mapping=='A': dmrsRE=4*length; # FIXME is 'A' right here?
  return dmrsRE

# plot functions - only for testing...

def plot_SINR_to_CQI(fn='img/plot_SINR_to_CQI'):
  n,bot,top=1000,-10.0,35.0
  x=np.linspace(bot,top,n)
  y=[SINR_to_CQI(x[i]) for i in range(n)]
  # write table to tab-separated file...
  f=open('SINR_to_CQI_table.tsv','w')
  for xy in zip(x,y): f.write('%.3f\t%.3f\n'%xy)
  f.close()
  fig=plt.figure()
  ax=fig.add_subplot(1,1,1)
  ax.set_xlim(bot,top)
  ax.set_ylim(0,15)
  ax.grid(linewidth=1,color='gray',alpha=0.25)
  ax.scatter(x,y,marker='.',s=1,label='exact SINR to CQI mapping',color='red')
  ax.plot([-5,29],[0,15],':',color='blue',alpha=0.7,label='linear approximation')
  ax.set_xlabel('SINR (dB)')
  ax.set_ylabel('CQI')
  ax.legend(loc='lower right')
  fig.tight_layout()
  fig_timestamp(fig,author='Keith Briggs',rotation=90)
  fig.savefig('%s.png'%fn)
  fig.savefig('%s.pdf'%fn)
  print('eog %s.png &'%fn)
  print('evince %s.pdf &'%fn)

def plot_CQI_to_efficiency_QPSK(fn='img/plot_CQI_to_efficiency_QPSK'):
  bot,top=0,15
  x=range(bot,1+top)
  y=[CQI_to_efficiency_QPSK(xi) for xi in x]
  fig=plt.figure()
  ax=fig.add_subplot(1,1,1)
  ax.set_xlim(1+bot,top)
  ax.set_ylim(0,6)
  ax.grid(linewidth=1,color='gray',alpha=0.25)
  ax.scatter(x,y,marker='o',s=2,label='CQI to efficiency (QPSK)',color='red')
  ax.plot(x,y,':',color='gray',alpha=0.5)
  ax.set_xlabel('CQI')
  ax.set_ylabel('spectral efficiency')
  ax.legend(loc='lower right')
  fig.tight_layout()
  fig_timestamp(fig,author='Keith Briggs',rotation=90)
  fig.savefig('%s.png'%fn)
  fig.savefig('%s.pdf'%fn)
  print('eog %s.png &'%fn)
  print('evince %s.pdf &'%fn)

#def CQI_to_64QAM_efficiency(cqi):
#  # FIXME better version of this... vectorize
#  CQI_to_MCS=lambda cqi: max(0,min(28,int(28*cqi/15.0)))
#  return MCS_to_Qm_table_64QAM[CQI_to_MCS(cqi)][2]

# better 2021-03-08 (cannot easily vectorize)...
@lru_cache(maxsize=None)
def CQI_to_64QAM_efficiency(cqi):
  CQI_to_MCS=max(0,min(28,int(28*cqi/15.0)))
  return MCS_to_Qm_table_64QAM[CQI_to_MCS][2]

def plot_CQI_to_efficiency(fn='img/plot_CQI_to_efficiency'):
  # TODO 256QAM
  bot,top=0,15
  cqi=range(bot,1+top)
  y=[CQI_to_64QAM_efficiency(x) for x in cqi]
  fig=plt.figure()
  ax=fig.add_subplot(1,1,1)
  ax.set_xlim(bot,top)
  ax.set_ylim(ymin=0,ymax=6)
  ax.grid(linewidth=0.5,color='gray',alpha=0.25)
  ax.plot(cqi,y,':',color='gray',ms=0.5,alpha=0.7)
  ax.scatter(cqi,y,marker='o',s=9,label='efficiency (64 QAM)',color='red')
  ax.set_xlabel('CQI')
  ax.set_ylabel('spectral efficiency')
  ax.legend(loc='lower right')
  fig.tight_layout()
  fig_timestamp(fig,author='Keith Briggs',rotation=90)
  fig.savefig('%s.png'%fn)
  fig.savefig('%s.pdf'%fn)
  print('eog %s.png &'%fn)
  print('evince %s.pdf &'%fn)

if __name__=='__main__':
  from sys import exit
  from fig_timestamp_00 import fig_timestamp
  import matplotlib.pyplot as plt
  plt.rcParams.update({'font.size': 8, 'figure.autolayout': True})
  radio_state=Radio_state()
  print(max_5G_throughput_64QAM(radio_state))
  plot_SINR_to_CQI()
  plot_CQI_to_efficiency_QPSK()
  plot_CQI_to_efficiency()
  exit()
  for rsrp_dBm in range(-160,0):
    print(rsrp_dBm,RSRP_report(rsrp_dBm)) # python3 NR_5G_standard_functions_00.py | p
