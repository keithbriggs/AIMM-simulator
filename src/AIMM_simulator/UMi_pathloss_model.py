# Henry Brice 2022-04-25

from math import log10,hypot
from numpy.linalg import norm

class UMi_streetcanyon_pathloss:
  '''
  Urban microcell dual-slope pathloss model, from 3GPP standard 36.873,
  Table 7.2-1.
  The model is defined in 36873-c70.doc from https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=2574.
  This code covers the cases 3D-UMi LOS and NLOS.
  3D-UMi = three-dimensional urban street canyon model.
  LOS    = line-of-sight.
  NLOS   = non-line-of-sight.
  '''

  def __init__(s,fc_GHz=3.5,h_UT=2.0,h_BS=10.0,LOS=True):
    '''
    Initialize a pathloss model instance.

    Parameters
    ----------
    fc_GHz : float
      Centre frequency in GigaHertz (default 3.5).
    h_UT : float
      Height of User Terminal (=UE) in metres  (default 2).
    h_BS : float
      Height of Base Station in metres (default 10 for UMi).
    LOS: bool
      Whether line-of-sight model is to be used (default True).
    '''
    s.fc=fc_GHz # GHz
    s.log10fc=log10(s.fc)
    s.h_UT=h_UT
    s.h_BS=h_BS
    s.LOS=LOS
    s.c=3e8
    # Adjustment for effective antenna height, 1.0 in LOS for UMa.
    # Same for UMi, assuming the effective antenna environment height is 1m.
    s.h_E=1.0
    # Note 1. This is the same for UMi and UMa.
    s.dBP=4.0*(s.h_BS-s.h_E)*(s.h_UT-s.h_E)*s.fc*1e9/s.c
    # This is used in the LOS models for both UMI and UMa...
    # next line is a better way s.a=9.0*log10(s.dBP**2+(s.h_BS-s.h_UT)**2)
    s.a=18.0*log10(hypot(s.dBP,s.h_BS-s.h_UT))
    # pre-compute constants to speed up calls...
    # LOS Model same for UMi and NLOS...
    s.const_close=28.0+20.0*s.log10fc
    s.const_far  =28.0+20.0*s.log10fc-s.a

  def __call__(s,xyz_cell,xyz_UE):
    '''
    Return the pathloss between 3-dimensional positions xyz_cell and
    xyz_UE (in metres).
    Note that the distances, building heights, etc. are not checked
    to ensure that this pathloss model is actually applicable.
    '''
    # TODO: could we usefully vectorize this, so that xyz_cell,xyz_UE have shape (n,3) to compute n pathlosses at once?
    d3D_m=norm(xyz_cell-xyz_UE)
    if d3D_m<s.dBP:
      PL3D_UMi_LOS=s.const_close+22.0*log10(d3D_m) # Same as for UMa
    else:
      PL3D_UMi_LOS=s.const_far  +40.0*log10(d3D_m)
    if s.LOS:
      return PL3D_UMi_LOS
    PL3D_UMi_NLOS=36.7*log10(d3D_m)+22.7+26*log10(s.fc)-0.3*(s.h_UT-1.5)
    return max(PL3D_UMi_NLOS,PL3D_UMi_LOS)

def plot():
  ' Plot the pathloss model predictions, as a self-test. '
  import numpy as np
  import matplotlib.pyplot as plt
  from fig_timestamp_00 import fig_timestamp
  fig=plt.figure(figsize=(8,6))
  ax=fig.add_subplot()
  ax.grid(color='gray',alpha=0.7,lw=0.5)
  d=np.linspace(1,5000,100)
  PL=UMi_streetcanyon_pathloss(fc_GHz=1.8,h_UT=1.5,h_BS=17.5,LOS=False)
  NLOS=np.array([PL(0,di) for di in d])
  ax.plot(d,NLOS,lw=2,label='NLOS ($\sigma=4$)')
  ax.fill_between(d,NLOS-4.0,NLOS+4.0,alpha=0.2) # sigma_{SF}=4 for NLOS case
  PL=UMi_streetcanyon_pathloss(fc_GHz=1.8,h_UT=1.5,h_BS=17.5,LOS=True)
  LOS=np.array([PL(0,di) for di in d])
  ax.plot(d,LOS,lw=2,label='LOS ($\sigma=3$)') # or semilogx
  ax.fill_between(d,LOS-3.0,LOS+3.0,alpha=0.2) # sigma_{SF}=3 for LOS case
  ax.set_xlabel('distance (metres)')
  ax.set_ylabel('pathloss (dB)')
  ax.set_xlim(np.min(d),np.max(d))
  ax.set_ylim(40)
  ax.legend()
  ax.set_title('3GPP UMi street-canyon pathloss models')
  fig.tight_layout()
  fig_timestamp(fig,rotation=0,fontsize=6,author='Keith Briggs')
  fnbase='img/UMi_pathloss_model_01'
  fig.savefig(f'{fnbase}.png')
  print(f'eog {fnbase}.png &')
  fig.savefig(f'{fnbase}.pdf')
  print(f'evince {fnbase}.pdf &')

if __name__=='__main__': # simple self-test
  plot()
