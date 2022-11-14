# Keith Briggs 2022-03-07 NLOS case implemented.
# Keith Briggs 2021-10-29 pathloss function now take two arguments, cell position and UE position.  This allows pathloss to depend on absolute position, not just distance
# Keith Briggs 2021-05-17
# Keith Briggs 2020-10-05; cf. ~/Voronoi-2.1/try_3GPP_UMa_pathloss_01.py
# Self-test (makes a plot): python3 UMa_pathloss_model_01.py

from math import log10,hypot
from numpy.linalg import norm

class UMa_pathloss:
  '''
  Urban macrocell dual-slope pathloss model, from 3GPP standard 36.873,
  Table 7.2-1.

  The model is defined in 36873-c70.doc from https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=2574.

  This code covers the cases 3D-UMa LOS and NLOS.
  3D-UMa = three dimensional urban macrocell model.
  LOS    = line-of-sight.
  NLOS   = non-line-of-sight.

  '''
  def __init__(s,fc_GHz=3.5,h_UT=2.0,h_BS=25.0,LOS=True,h=20.0,W=20.0):
    '''
    Initialize a pathloss model instance.

    Parameters
    ----------
    fc_GHz : float
      Centre frequency in GigaHertz (default 3.5).
    h_UT : float
      Height of User Terminal (=UE) in metres  (default 2).
    h_BS : float
      Height of Base Station in metres (default 25).
    LOS: bool
      Whether line-of-sight model is to be used (default True).
    h : float
      Average building height (default 20, used in NLOS case only)
    W : float
      Street width (default 20, used in NLOS case only)
    '''
    s.fc=fc_GHz # GHz
    s.log10fc=log10(s.fc)
    s.h_UT=h_UT
    s.h_BS=h_BS
    s.LOS=LOS
    s.h=h
    s.W=W
    s.c=3e8
    s.h_E=1.0
    s.dBP=4.0*(s.h_BS-s.h_E)*(s.h_UT-s.h_E)*s.fc*1e9/s.c # Note 1
    s.a=9.0*log10(s.dBP**2+(s.h_BS-s.h_UT)**2)
    # pre-compute constants to speed up calls...
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
    d3D_m=norm(xyz_cell-xyz_UE) # new way 2021-10-29
    # TODO 2022-04-27: is the next faster? 
    #dxyz=xyz_cell-xyz_UE; d3D_m=hypot(dxyz[0],hypot(dxyz[1],dxyz[2]))
    if d3D_m<s.dBP: PL3D_UMa_LOS=s.const_close+22.0*log10(d3D_m)
    else:           PL3D_UMa_LOS=s.const_far  +40.0*log10(d3D_m)
    if s.LOS:
      return PL3D_UMa_LOS
    # else NLOS:
    # Formulas from Table 7.2-1 are...
    # PL3D-UMa-NLOS=161.04-7.1*log10(W)+7.5*log10(h)-(24.37-3.7*(h/hBS)**2)*log10(hBS)+(43.42-3.1*log10(hBS))*(log10(d3D)-3)+20*log10(fc)-(3.2*(log10(17.625))**2-4.97)-0.6*(hUT-1.5)
    # PL=max(PL3D-UMa-NLOS,PL3D-UMa-LOS)
    c1=-9.1904695449517596702522e-4 # =3.2*(log10(17.625))**2-4.97
    PL3D_UMa_NLOS=161.04-7.1*log10(s.W)+7.5*log10(s.h)-(24.37-3.7*(s.h/s.h_BS)**2)*log10(s.h_BS)+(43.42-3.1*log10(s.h_BS))*(log10(d3D_m)-3.0)+20*log10(s.fc)-(c1)-0.6*(s.h_UT-1.5) # TODO pre-compute more constants to speed this up!
    return max(PL3D_UMa_NLOS,PL3D_UMa_LOS)

def plot():
  ' Plot the pathloss model predictions, as a self-test. '
  import numpy as np
  import matplotlib.pyplot as plt
  from fig_timestamp_00 import fig_timestamp
  fig=plt.figure(figsize=(8,6))
  ax=fig.add_subplot()
  ax.grid(color='gray',alpha=0.7,lw=0.5)
  d=np.linspace(10,5000,100) # valid from 10m
  PL=UMa_pathloss(fc_GHz=1.8,h_UT=1.5,h_BS=17.5,LOS=False)
  NLOS=np.array([PL(0,di) for di in d])
  ax.plot(d,NLOS,lw=2,label='NLOS ($\sigma=6$)') # or semilogx
  ax.fill_between(d,NLOS-6.0,NLOS+6.0,alpha=0.2) # sigma_{SF}=6 for NLOS case
  PL=UMa_pathloss(fc_GHz=1.8,h_UT=1.5,h_BS=17.5,LOS=True)
  LOS=np.array([PL(0,di) for di in d])
  ax.plot(d,LOS,lw=2,label='LOS ($\sigma=4$)') # or semilogx
  ax.fill_between(d,LOS-4.0,LOS+4.0,alpha=0.2) # sigma_{SF}=4 for LOS case
  ax.set_xlabel('distance (metres)')
  ax.set_ylabel('pathloss (dB)')
  ax.set_xlim(0,np.max(d))
  ax.set_ylim(40)
  ax.legend()
  ax.set_title('3GPP UMa pathloss models')
  fig.tight_layout()
  fig_timestamp(fig,rotation=0,fontsize=6,author='Keith Briggs')
  fnbase='img/UMa_pathloss_model_01'
  fig.savefig(f'{fnbase}.png')
  print(f'eog {fnbase}.png &')
  fig.savefig(f'{fnbase}.pdf')
  print(f'evince {fnbase}.pdf &')

if __name__=='__main__':
  plot() # simple self-test
