# Keith Briggs 2022-11-11 2.0 version
# Simulation structure:
# Sim - Scenario - MME
# |
# RIC
# |
# Cell---Cell---Cell--- ....
# |       |      |
# UE UE  UE UE  UE UE ...

__version__='2.0.2'
'''The AIMM simulator emulates a cellular radio system roughly following 5G concepts and channel models.'''

from os.path import basename
from sys import stderr,stdout,exit,version as pyversion
from math import hypot,atan2,pi as math_pi
from time import time,sleep
from collections import deque
try:
  import numpy as np
except:
  print('numpy not found: please do "pip install numpy"',file=stderr)
  exit(1)
try:
  import simpy
except:
  print('simpy not found: please do "pip install simpy"',file=stderr)
  exit(1)
from .NR_5G_standard_functions import SINR_to_CQI,CQI_to_64QAM_efficiency
from .UMa_pathloss_model import UMa_pathloss

def np_array_to_str(x):
  ' Formats a 1-axis np.array as a tab-separated string '
  return np.array2string(x,separator='\t').replace('[','').replace(']','')

def _nearest_weighted_point(x,pts,w=1.0):
  '''
  Internal use only.
  Given a point x of shape (dim,), where dim is typically 2 or 3,
  an array of points pts of shape (npts,dim),
  and a vector of weights w of the same length as pts,
  return the index of the point minimizing w[i]*d[i],
  where d[i] is the distance from x to point i.
  Returns the index of the point minimizing w[i]*d[i].
  For the application to cellular radio systems, we let pts be the
  cell locations, and then if we set
  w[i]=p[i]**(-1/alpha),
  where p[i] is the transmit power of cell i, and alpha>=2 is the pathloss
  exponent, then this algorithm will give us the index of the cell providing
  largest received power at the point x.
  '''
  weighted_distances=w*np.linalg.norm(pts-x,axis=1)
  imin=np.argmin(weighted_distances)
  if 0: # dbg
    print('x=',x)
    print('pts=',pts)
    print('weighted_distances=',weighted_distances)
  return weighted_distances[imin],imin

def to_dB(x):
  return 10.0*np.log10(x)

def from_dB(x):
  return np.power(10.0,x/10.0)

class Cell:
  '''
  Class representing a single Cell (gNB).  As instances are created, the are automatically given indices starting from 0.  This index is available as the data member ``cell.i``.   The variable ``Cell.i`` is always the current number of cells.

  Parameters
  ----------
  sim : Sim
    Simulator instance which will manage this Cell.
  interval : float
    Time interval between Cell updates.
  bw_MHz : float
    Channel bandwidth in MHz.
  n_subbands : int
    Number of subbands.
  xyz : [float, float, float]
    Position of cell in metres, and antenna height.
  h_BS : float
    Antenna height in metres; only used if xyz is not provided.
  power_dBm : float
    Transmit power in dBm.
  MIMO_gain_dB : float
    Effective power gain from MIMO in dB.  This is no more than a crude way to
    estimate the performance gain from using MIMO.  A typical value might be 3dB for 2x2 MIMO.
  pattern : array or function
    If an array, then a 360-element array giving the antenna gain in dB in 1-degree increments (0=east, then counterclockwise).  Otherwise, a function giving the antenna gain in dB in the direction theta=(180/pi)*atan2(y,x).
  f_callback :
    A function with signature ``f_callback(self,kwargs)``, which will be called
    at each iteration of the main loop.
  verbosity : int
      Level of debugging output (0=none).
  '''
  i=0

  def __init__(s,
               sim,
               interval=10.0,
               bw_MHz=10.0,
               n_subbands=1,
               xyz=None,
               h_BS=20.0,
               power_dBm=30.0,
               MIMO_gain_dB=0.0,
               pattern=None,
               f_callback=None,
               f_callback_kwargs={},
               verbosity=0):
    # default scene 1000m x 1000m, but keep cells near the centre
    s.i=Cell.i; Cell.i+=1
    s.sim=sim
    s.interval=interval
    s.bw_MHz=bw_MHz
    s.n_subbands=n_subbands
    s.subband_mask=np.ones(n_subbands) # dtype is float, to allow soft masking
    s.rbs=simpy.Resource(s.sim.env,capacity=50)
    s.power_dBm=power_dBm
    s.pattern=pattern
    s.f_callback=f_callback
    s.f_callback_kwargs=f_callback_kwargs
    s.MIMO_gain_dB=MIMO_gain_dB
    s.attached=set()
    s.reports={'cqi': {}, 'rsrp': {}, 'throughput_Mbps': {}}
    # rsrp_history[i] will be the last 10 reports of rsrp received
    # at this cell from UE[i] (no timestamps, just for getting trend)
    s.rsrp_history={}
    if xyz is not None:
      s.xyz=np.array(xyz)
    else: # random cell locations
      s.xyz=np.empty(3)
      s.xyz[:2]=100.0+900.0*s.sim.rng.random(2)
      s.xyz[2]=h_BS
    if verbosity>1: print(f'Cell[{s.i}] is at',s.xyz,file=stderr)
    s.verbosity=verbosity
    # every time we make a new Cell, we have to check whether
    # we have a hetnet or not...
    s.sim._set_hetnet()
    #s.sim.env.process(s.loop()) # start Cell main loop

  def set_f_callback(s,f_callback,**kwargs):
    ' Add a callback function to the main loop of this Cell '
    s.f_callback=f_callback
    s.f_callback_kwargs=kwargs

  def loop(s):
    '''
      Main loop of Cell class.  Default: do nothing.
    '''
    while True:
      if s.f_callback is not None: s.f_callback(s,**s.f_callback_kwargs)
      yield s.sim.env.timeout(s.interval)

  def __repr__(s):
    return f'Cell(index={s.i},xyz={s.xyz})'

  def get_nattached(s):
    '''
    Return the current number of UEs attached to this Cell.
    '''
    return len(s.attached)

  def get_xyz(s):
    '''
    Return the current position of this Cell.
    '''
    return s.xyz

  def set_xyz(s,xyz):
    '''
    Set a new position for this Cell.
    '''
    s.xyz=np.array(xyz)
    s.sim.cell_locations[s.i]=s.xyz
    print(f'Cell[{s.i}]   is now at {s.xyz}',file=stderr)

  def get_power_dBm(s):
    '''
    Return the transmit power in dBm currently used by this cell.
    '''
    return s.power_dBm

  def set_power_dBm(s,p):
    '''
    Set the transmit power in dBm to be used by this cell.
    '''
    s.power_dBm=p
    s.sim._set_hetnet()

  def boost_power_dBm(s,p,mn=None,mx=None):
    '''
    Increase or decrease (if p<0) the transmit power in dBm to be used by this cell.
    If mn is not ``None``, then the power will not be set if it falls below mn.
    If mx is not ``None``, then the power will not be set if it exceeds mx.
    Return the new power.
    '''
    if p<0.0:
      if mn is not None and s.power_dBm+p>=mn:
        s.power_dBm+=p
      return s.power_dBm
    if p>0.0:
      if mx is not None and s.power_dBm+p<=mx:
        s.power_dBm+=p
      return s.power_dBm
    s.power_dBm+=p
    return s.power_dBm

  def get_rsrp(s,i):
    '''
    Return last RSRP reported to this cell by UE[i].
    '''
    if i in s.reports['rsrp']:
      return s.reports['rsrp'][i][1]
    return -np.inf # no reports

  def get_rsrp_history(s,i):
    '''
    Return an array of the last 10 RSRP[1]s reported to this cell by UE[i].
    '''
    if i in s.rsrp_history:
      return np.array(s.rsrp_history[i])
    return -np.inf*np.ones(10) # no recorded history

  def set_MIMO_gain(s,MIMO_gain_dB):
    '''
    Set the MIMO gain in dB to be used by this cell.
    '''
    s.MIMO_gain_dB=MIMO_gain_dB

  def get_UE_throughput(s,ue_i): # FIXME do we want an array over subbands?
    '''
    Return the total current throughput in Mb/s of UE[i] in the simulation.
    The value -np.inf indicates that there is no current report.
    '''
    reports=s.reports['throughput_Mbps']
    if ue_i in reports: return reports[ue_i][1]
    return -np.inf # special value to indicate no report

  def get_UE_CQI(s,ue_i):
    '''
    Return the current CQI of UE[i] in the simulation, as an array across all subbands.  An array of NaNs is returned if there is no report.
    '''
    reports=s.reports['cqi']
    return reports[ue_i][1] if ue_i in reports else np.nan*np.ones(s.n_subbands)

  def get_RSRP_reports(s):
    '''
    Return the current RSRP reports to this cell, as a list of tuples (ue.i, rsrp).
    '''
    reports=s.reports['rsrp']
    return [(ue.i,reports[ue.i][1]) if ue.i in reports else (ue.i,-np.inf) for ue in s.sim.UEs]

  def get_RSRP_reports_dict(s):
    '''
    Return the current RSRP reports to this cell, as a dictionary ue.i: rsrp.
    '''
    reports=s.reports['rsrp']
    return dict((ue.i,reports[ue.i][1]) if ue.i in reports else (ue.i,-np.inf) for ue in s.sim.UEs)

  def get_average_throughput(s):
    '''
    Return the average throughput over all UEs attached to this cell.
    '''
    reports,k=s.reports['throughput_Mbps'],0
    ave=np.zeros(s.n_subbands)
    for ue_i in reports:
      k+=1
      #ave+=(reports[ue_i][1][0]-ave)/k
      ave+=(np.sum(reports[ue_i][1])-ave)/k
    return np.sum(ave)

  def set_pattern(s,pattern):
    '''
    Set the antenna radiation pattern.
    '''
    s.pattern=pattern

  def set_subband_mask(s,mask):
    '''
    Set the subband mask to ``mask``.
    '''
    #print('set_subband_mask',s.subband_mask.shape,len(mask),file=stderr)
    assert s.subband_mask.shape[0]==len(mask)
    s.subband_mask=np.array(mask)

  def get_subband_mask(s):
    '''
    Get the current subband mask.
    '''
    return s.subband_mask

  def monitor_rbs(s):
    while True:
      if s.rbs.queue:
        if s.verbosity>0: print(f'rbs at {s.sim.env.now:.2f} ={s.rbs.count}')
      yield s.sim.env.timeout(5.0)
# END class Cell

class UE:
  '''
    Represents a single UE. As instances are created, the are automatically given indices starting from 0.  This index is available as the data member ``ue.i``.   The static (class-level) variable ``UE.i`` is always the current number of UEs.

    Parameters
    ----------
    sim : Sim
      The Sim instance which will manage this UE.
    xyz : [float, float, float]
      Position of UE in metres, and antenna height.
    h_UT : float
      Antenna height of user terminal in metres; only used if xyz is not provided.
    reporting_interval : float
      Time interval between UE reports being sent to the serving cell.
    f_callback :
      A function with signature ``f_callback(self,kwargs)``, which will be called at each iteration of the main loop.
    f_callback_kwargs :
      kwargs for previous function.
    pathloss_model
      An instance of a pathloss model.  This must be a callable object which
      takes two arguments, each a 3-vector.  The first represent the transmitter
      location, and the second the receiver location.  It must return the
      pathloss in dB along this signal path.
      If set to ``None`` (the default), a standard urban macrocell model
      is used.
      See further ``NR_5G_standard_functions_00.py``.
  '''
  i=0

  def __init__(s,sim,xyz=None,reporting_interval=1.0,pathloss_model=None,h_UT=2.0,f_callback=None,f_callback_kwargs={},verbosity=0):
    s.sim=sim
    s.i=UE.i; UE.i+=1
    s.serving_cell=None
    s.f_callback=f_callback
    s.f_callback_kwargs=f_callback_kwargs
    # next will be a record of last 10 serving cell ids,
    # with time of last attachment.
    # 0=>current, 1=>previous, etc. -1 => not valid)
    # This is for use in handover algorithms
    s.serving_cell_ids=deque([(-1,None)]*10,maxlen=10)
    s.reporting_interval=reporting_interval
    if xyz is not None:
      s.xyz=np.array(xyz,dtype=float)
    else:
      s.xyz=250.0+500.0*s.sim.rng.random(3)
      s.xyz[2]=h_UT
    if verbosity>1: print(f'UE[{s.i}]   is at',s.xyz,file=stderr)
    # We assume here that the UMa_pathloss model needs to be instantiated,
    # but other user-provided models are already instantiated,
    # and provide callable objects...
    if pathloss_model is None:
      s.pathloss=UMa_pathloss(fc_GHz=s.sim.params['fc_GHz'],h_UT=s.sim.params['h_UT'],h_BS=s.sim.params['h_BS'])
      if verbosity>1: print(f'Using 5G standard urban macrocell pathloss model.',file=stderr)
    else:
      s.pathloss=pathloss_model
      if s.pathloss.__doc__ is not None:
        if verbosity>1: print(f'Using user-specified pathloss model "{s.pathloss.__doc__}".',file=stderr)
      else:
        print(f'Using user-specified pathloss model.',file=stderr)
    s.verbosity=verbosity
    s.noise_power_dBm=-140.0
    s.cqi=None
    s.sinr_dB=None
    # Keith Briggs 2022-10-12 loops now started in Sim.__init__
    #s.sim.env.process(s.run_subband_cqi_report())
    #s.sim.env.process(s.loop()) # this does reports to all cells

  def __repr__(s):
    return f'UE(index={s.i},xyz={s.xyz},serving_cell={s.serving_cell})'

  def set_f_callback(s,f_callback,**kwargs):
    ' Add a callback function to the main loop of this UE '
    s.f_callback=f_callback
    s.f_callback_kwargs=kwargs

  def loop(s):
    ' Main loop of UE class '
    if s.verbosity>1:
      print(f'Main loop of UE[{s.i}] started')
      stdout.flush()
    while True:
      if s.f_callback is not None: s.f_callback(s,**s.f_callback_kwargs)
      s.send_rsrp_reports()
      s.send_subband_cqi_report() # FIXME merge these two reports
      #print(f'dbg: Main loop of UE class started'); exit()
      yield s.sim.env.timeout(s.reporting_interval)

  def get_serving_cell(s):
    '''
    Return the current serving Cell object (not index) for this UE instance.
    '''
    ss=s.serving_cell
    if ss is None: return None
    return s.serving_cell

  def get_serving_cell_i(s):
    '''
    Return the current serving Cell index for this UE instance.
    '''
    ss=s.serving_cell
    if ss is None: return None
    return s.serving_cell.i

  def get_xyz(s):
    '''
    Return the current position of this UE.
    '''
    return s.xyz

  def set_xyz(s,xyz,verbose=False):
    '''
    Set a new position for this UE.
    '''
    s.xyz=np.array(xyz)
    if verbose: print(f'UE[{s.i}] is now at {s.xyz}',file=stderr)

  def attach(s,cell,quiet=True):
    '''
    Attach this UE to a specific Cell instance.
    '''
    cell.attached.add(s.i)
    s.serving_cell=cell
    s.serving_cell_ids.appendleft((cell.i,s.sim.env.now,))
    if not quiet and s.verbosity>0:
      print(f'UE[{s.i:2}] is attached to cell[{cell.i}]',file=stderr)

  def detach(s,quiet=True):
    '''
    Detach this UE from its serving cell.
    '''
    if s.serving_cell is None:  # Keith Briggs 2022-08-08 added None test
      return
    s.serving_cell.attached.remove(s.i)
    # clear saved reports from this UE...
    reports=s.serving_cell.reports
    for x in reports:
      if s.i in reports[x]: del reports[x][s.i]
    if not quiet and s.verbosity>0:
      print(f'UE[{s.i}] detached from cell[{s.serving_cell.i}]',file=stderr)
    s.serving_cell=None

  def attach_to_strongest_cell_simple_pathloss_model(s):
    '''
    Attach to the cell delivering the strongest signal
    at the current UE position. Intended for initial attachment only.
    Uses only a simple power-law pathloss model.  For proper handover
    behaviour, use the MME module.
    '''
    celli=s.sim.get_strongest_cell_simple_pathloss_model(s.xyz)
    s.serving_cell=s.sim.cells[celli]
    s.serving_cell.attached.add(s.i)
    if s.verbosity>0:
      print(f'UE[{s.i:2}] ⟵⟶  cell[{celli}]',file=stderr)

  def attach_to_nearest_cell(s):
    '''
    Attach this UE to the geographically nearest Cell instance.
    Intended for initial attachment only.
    '''
    dmin,celli=_nearest_weighted_point(s.xyz[:2],s.sim.cell_locations[:,:2])
    if 0: # dbg
      print(f'_nearest_weighted_point: celli={celli} dmin={dmin:.2f}')
      for cell in s.sim.cells:
        d=np.linalg.norm(cell.xyz-s.xyz)
        print(f'Cell[{cell.i}] is at distance {d:.2f}')
    s.serving_cell=s.sim.cells[celli]
    s.serving_cell.attached.add(s.i)
    if s.verbosity>0:
      print(f'UE[{s.i:2}] ⟵⟶  cell[{celli}]',file=stderr)

  def get_CQI(s):
    '''
    Return the current CQI of this UE, as an array across all subbands.
    '''
    return s.cqi

  def get_SINR_dB(s):
    '''
    Return the current SINR of this UE, as an array across all subbands.
    The return value ``None`` indicates that there is no current report.
    '''
    return s.sinr_dB

  def send_rsrp_reports(s,threshold=-120.0):
    '''
    Send RSRP reports in dBm to all cells for which it is over the threshold.
    Subbands not handled.
    '''
    # antenna pattern computation added Keith Briggs 2021-11-24.
    for cell in s.sim.cells:
      pl_dB=s.pathloss(cell.xyz,s.xyz) # 2021-10-29
      antenna_gain_dB=0.0
      if cell.pattern is not None:
        vector=s.xyz-cell.xyz # vector pointing from cell to UE
        angle_degrees=(180.0/math_pi)*atan2(vector[1],vector[0])
        antenna_gain_dB=cell.pattern(angle_degrees) if callable(cell.pattern) \
          else cell.pattern[int(angle_degrees)%360]
      rsrp_dBm=cell.power_dBm+antenna_gain_dB+cell.MIMO_gain_dB-pl_dB
      rsrp=from_dB(rsrp_dBm)
      if rsrp_dBm>threshold:
        cell.reports['rsrp'][s.i]=(s.sim.env.now,rsrp_dBm)
        if s.i not in cell.rsrp_history:
          cell.rsrp_history[s.i]=deque([-np.inf,]*10,maxlen=10)
        cell.rsrp_history[s.i].appendleft(rsrp_dBm)

  def send_subband_cqi_report(s):
    '''
    For this UE, send an array of CQI reports, one for each subband; and a total throughput report, to the serving cell.
    What is sent is a 2-tuple (current time, array of reports).
    For RSRP reports, use the function ``send_rsrp_reports``.
    Also saves the CQI[1]s in s.cqi, and returns the throughput value.
    '''
    if s.serving_cell is None: return 0.0 # 2022-08-08 detached
    interference=from_dB(s.noise_power_dBm)*np.ones(s.serving_cell.n_subbands)
    for cell in s.sim.cells:
      pl_dB=s.pathloss(cell.xyz,s.xyz)
      antenna_gain_dB=0.0
      if cell.pattern is not None:
        vector=s.xyz-cell.xyz # vector pointing from cell to UE
        angle_degrees=(180.0/math_pi)*atan2(vector[1],vector[0])
        antenna_gain_dB=cell.pattern(angle_degrees) if callable(cell.pattern) \
          else cell.pattern[int(angle_degrees)%360]
      if cell.i==s.serving_cell.i: # wanted signal
        rsrp_dBm=cell.MIMO_gain_dB+antenna_gain_dB+cell.power_dBm-pl_dB
      else: # unwanted interference
        received_interference_power=antenna_gain_dB+cell.power_dBm-pl_dB
        interference+=from_dB(received_interference_power)*cell.subband_mask
    rsrp=from_dB(rsrp_dBm)
    s.sinr_dB=to_dB(rsrp/interference) # scalar/array
    s.cqi=cqi=SINR_to_CQI(s.sinr_dB)
    spectral_efficiency=np.array([CQI_to_64QAM_efficiency(cqi_i) for cqi_i in cqi])
    now=float(s.sim.env.now)
    # per-UE throughput...
    throughput_Mbps=s.serving_cell.bw_MHz*(spectral_efficiency@s.serving_cell.subband_mask)/s.serving_cell.n_subbands/len(s.serving_cell.attached)
    s.serving_cell.reports['cqi'][s.i]=(now,cqi)
    s.serving_cell.reports['throughput_Mbps'][s.i]=(now,throughput_Mbps,)
    return throughput_Mbps

  def run_subband_cqi_report(s): # FIXME merge this with rsrp reporting
    while True:
      #if s.serving_cell is not None: # UE must be attached 2022-08-08
        s.send_subband_cqi_report()
        yield s.sim.env.timeout(s.reporting_interval)

# END class UE

class Sim:
  '''
  Class representing the complete simulation.

  Parameters
  ----------
  params : dict
    A dictionary of additional global parameters which need to be accessible to downstream functions. In the instance, these parameters will be available as ``sim.params``.  If ``params['profile']`` is set to a non-empty string, then a code profile will be performed and the results saved to the filename given by the string.  There will be some execution time overhead when profiling.
  '''

  def __init__(s,params={'fc_GHz':3.5,'h_UT':2.0,'h_BS':20.0},show_params=True,rng_seed=0):
    s.__version__=__version__
    s.params=params
    # set default values for operating frequenct, user terminal height, and
    # base station height...
    if 'fc_GHz' not in params: params['fc_GHz']=3.5
    if 'h_UT'   not in params: params['h_UT']=2.0
    if 'h_BS'   not in params: params['h_BS']=20.0
    s.env=simpy.Environment()
    s.rng=np.random.default_rng(rng_seed)
    s.loggers=[]
    s.scenario=None
    s.ric=None
    s.mme=None
    s.hetnet=None # unknown at this point; will be set to True or False
    s.cells=[]
    s.UEs=[]
    s.events=[]
    s.cell_locations=np.empty((0,3))
    np.set_printoptions(precision=2,linewidth=200)
    pyv=pyversion.replace('\n','') #[:pyversion.index('(default')]
    print(f'python version={pyv}',file=stderr)
    print(f'numpy  version={np.__version__}',file=stderr)
    print(f'simpy  version={simpy.__version__}',file=stderr)
    print(f'AIMM simulator version={s.__version__}',file=stderr)
    if show_params:
      print(f'Simulation parameters:',file=stderr)
      for param in s.params:
        print(f"  {param}={s.params[param]}",file=stderr)

  def _set_hetnet(s):
    #  internal function only - decide whether we have a hetnet
    powers=set(cell.get_power_dBm() for cell in s.cells)
    s.hetnet=len(powers)>1 # powers are not all equal

  def wait(s,interval=1.0):
    '''
    Convenience function to avoid low-level reference to env.timeout().
    ``loop`` functions in each class must yield this.
    '''
    return s.env.timeout(interval)

  def make_cell(s,**kwargs):
    '''
    Convenience function: make a new Cell instance and add it to the simulation; parameters as for the Cell class. Return the new Cell instance.  It is assumed that Cells never move after being created (i.e. the initial xyz[1] stays the same throughout the simulation).
    '''
    s.cells.append(Cell(s,**kwargs))
    xyz=s.cells[-1].get_xyz()
    s.cell_locations=np.vstack([s.cell_locations,xyz])
    return s.cells[-1]

  def make_UE(s,**kwargs):
    '''
    Convenience function: make a new UE instance and add it to the simulation; parameters as for the UE class. Return the new UE instance.
    '''
    s.UEs.append(UE(s,**kwargs))
    return s.UEs[-1]

  def get_ncells(s):
    '''
    Return the current number of cells in the simulation.
    '''
    return len(s.cells)

  def get_nues(s):
    '''
    Return the current number of UEs in the simulation.
    '''
    return len(s.UEs)

  def get_UE_position(s,ue_i):
    '''
    Return the xyz position of UE[i] in the simulation.
    '''
    return s.UEs[ue_i].xyz

  def get_average_throughput(s):
    '''
    Return the average throughput over all UEs attached to all cells.
    '''
    ave,k=0.0,0
    for cell in s.cells:
      k+=1
      ave+=(cell.get_average_throughput()-ave)/k
    return ave

  def add_logger(s,logger):
    '''
    Add a logger to the simulation.
    '''
    assert isinstance(logger,Logger)
    s.loggers.append(logger)

  def add_loggers(s,loggers):
    '''
    Add a sequence of loggers to the simulation.
    '''
    for logger in loggers:
      assert isinstance(logger,Logger)
      s.loggers.append(logger)

  def add_scenario(s,scenario):
    '''
    Add a Scenario instance to the simulation.
    '''
    assert isinstance(scenario,Scenario)
    s.scenario=scenario

  def add_ric(s,ric):
    '''
    Add a RIC instance to the simulation.
    '''
    assert isinstance(ric,RIC)
    s.ric=ric

  def add_MME(s,mme):
    '''
    Add an MME instance to the simulation.
    '''
    assert isinstance(mme,MME)
    s.mme=mme

  def add_event(s,event):
    s.events.append(event)

  def get_serving_cell(s,ue_i):
    if ue_i<len(s.UEs): return s.UEs[ue_i].serving_cell
    return None

  def get_serving_cell_i(s,ue_i):
    if ue_i<len(s.UEs): return s.UEs[ue_i].serving_cell.i
    return None

  def get_nearest_cell(s,xy):
    '''
    Return the index of the geographical nearest cell (in 2 dimensions)
    to the point xy.
    '''
    return _nearest_weighted_point(xy[:2],s.cell_locations[:,:2],w=1.0)[1]

  def get_strongest_cell_simple_pathloss_model(s,xyz,alpha=3.5):
    '''
    Return the index of the cell delivering the strongest signal
    at the point xyz (in 3 dimensions), with pathloss exponent alpha.
    Note: antenna pattern is not used, so this function is deprecated,
    but is adequate for initial UE attachment.
    '''
    p=np.array([from_dB(cell.get_power_dBm()) for cell in s.cells])
    return _nearest_weighted_point(xyz,s.cell_locations,w=p**(-1.0/alpha))[1]

  def get_best_rsrp_cell(s,ue_i,dbg=False):
    '''
    Return the index of the cell delivering the highest RSRP at UE[i].
    Relies on UE reports, and ``None`` is returned if there are not enough
    reports (yet) to determine the desired output.
    '''
    k,best_rsrp=None,-np.inf
    cell_rsrp_reports=dict((cell.i,cell.reports['rsrp']) for cell in s.cells)
    for cell in s.cells:
      if ue_i not in cell_rsrp_reports[cell.i]: continue # no reports for this UE
      time,rsrp=cell_rsrp_reports[cell.i][ue_i] # (time, subband reports)
      if dbg: print(f"get_best_rsrp_cell at {float(s.env.now):.0f}: cell={cell.i} UE={ue_i} rsrp=",rsrp,file=stderr)
      ave_rsrp=np.average(rsrp) # average RSRP over subbands
      if ave_rsrp>best_rsrp: k,best_rsrp=cell.i,ave_rsrp
    return k

  def _start_loops(s):
    # internal use only - start all main loops
    for logger in s.loggers:
      s.env.process(logger.loop())
    if s.scenario is not None:
      s.env.process(s.scenario.loop())
    if s.ric is not None:
      s.env.process(s.ric.loop())
    if s.mme is not None:
      s.env.process(s.mme.loop())
    for event in s.events: # TODO ?
      s.env.process(event)
    for cell in s.cells: # 2022-10-12 start Cells
      s.env.process(cell.loop())
    for ue in s.UEs: # 2022-10-12 start UEs
      #print(f'About to start main loop of UE[{ue.i}]..')
      s.env.process(ue.loop())
      #s.env.process(UE.run_subband_cqi_report())
    #sleep(2); exit()

  def run(s,until):
    s._set_hetnet()
    s.until=until
    print(f'Sim: starting run for simulation time {until} seconds...',file=stderr)
    s._start_loops()
    t0=time()
    if 'profile' in s.params and s.params['profile']:
      # https://docs.python.org/3.6/library/profile.html
      # to keep python 3.6 compatibility, we don't use all the
      # features for profiling added in 3.8 or 3.9.
      profile_filename=s.params['profile']
      print(f'profiling enabled: output file will be {profile_filename}.',file=stderr)
      import cProfile,pstats,io
      pr=cProfile.Profile()
      pr.enable()
      s.env.run(until=until) # this is what is profiled
      pr.disable()
      strm=io.StringIO()
      ps=pstats.Stats(pr,stream=strm).sort_stats('tottime')
      ps.print_stats()
      tbl=strm.getvalue().split('\n')
      profile_file=open(profile_filename,'w')
      for line in tbl[:50]: print(line,file=profile_file)
      profile_file.close()
      print(f'profile written to {profile_filename}.',file=stderr)
    else:
      s.env.run(until=until)
    print(f'Sim: finished main loop in {(time()-t0):.2f} seconds.',file=stderr)
    #print(f'Sim: hetnet={s.hetnet}.',file=stderr)
    if s.mme is not None:
      s.mme.finalize()
    if s.ric is not None:
      s.ric.finalize()
    for logger in s.loggers:
      logger.finalize()

# END class Sim

class Scenario:

  '''
    Base class for a simulation scenario. The default does nothing.

    Parameters
    ----------
    sim : Sim
      Simulator instance which will manage this Scenario.
    func : function
      Function called to perform actions.
    interval : float
      Time interval between actions.
    verbosity : int
      Level of debugging output (0=none).

  '''

  def __init__(s,sim,func=None,interval=1.0,verbosity=0):
    s.sim=sim
    s.func=func
    s.verbosity=verbosity
    s.interval=interval

  def loop(s):
    '''
    Main loop of Scenario class.  Should be overridden to provide different functionalities.
    '''
    while True:
      if s.func is not None: s.func(s.sim)
      yield s.sim.env.timeout(s.interval)

# END class Scenario

class Logger:

  '''
  Represents a simulation logger. Multiple loggers (each with their own file) can be used if desired.

  Parameters
  ----------
    sim : Sim
      The Sim instance which will manage this Logger.
    func : function
      Function called to perform logginf action.
    header : str
      Arbitrary text to write to the top of the logfile.
    f : file object
      An open file object which will be written or appended to.
    logging_interval : float
      Time interval between logging actions.

  '''
  def __init__(s,sim,func=None,header='',f=stdout,logging_interval=10,np_array_to_str=np_array_to_str):
    s.sim=sim
    s.func=s.default_logger if func is None else func
    s.f=f
    s.np_array_to_str=np_array_to_str
    s.logging_interval=float(logging_interval)
    if header: s.f.write(header)

  def default_logger(s,f=stdout):
    for cell in s.sim.cells:
      for ue_i in cell.reports['cqi']:
        rep=cell.reports['cqi'][ue_i]
        if rep is None: continue
        cqi=s.np_array_to_str(rep[1])
        f.write(f'{cell.i}\t{ue_i}\t{cqi}\n')

  def loop(s):
    '''
    Main loop of Logger class.
    Can be overridden to provide custom functionality.
    '''
    while True:
      s.func(f=s.f)
      yield s.sim.env.timeout(s.logging_interval)

  def finalize(s):
    '''
    Function called at end of simulation, to implement any required finalization actions.
    '''
    pass

# END class Logger

class MME:
  '''
  Represents a MME, for handling UE handovers.

  Parameters
  ----------
    sim : Sim
      Sim instance which will manage this Scenario.
    interval : float
      Time interval between checks for handover actions.
    verbosity : int
      Level of debugging output (0=none).
    strategy : str
      Handover strategy; possible values are ``strongest_cell_simple_pathloss_model`` (default), or ``best_rsrp_cell``.
    anti_pingpong : float
      If greater than zero, then a handover pattern x->y->x between cells x and y is not allowed within this number of seconds. Default is 0.0, meaning pingponging is not suppressed.
  '''

  def __init__(s,sim,interval=10.0,strategy='strongest_cell_simple_pathloss_model',anti_pingpong=30.0,verbosity=0):
    s.sim=sim
    s.interval=interval
    s.strategy=strategy
    s.anti_pingpong=anti_pingpong
    s.verbosity=verbosity
    print(f'MME: using handover strategy {s.strategy}.',file=stderr)

  def do_handovers(s):
    '''
    Check whether handovers are required, and do them if so.
    Normally called from loop(), but can be called manually if required.
    '''
    for ue in s.sim.UEs:
      if ue.serving_cell is None: continue # no handover needed for this UE. 2022-08-08 added None test
      oldcelli=ue.serving_cell.i # 2022-08-26
      CQI_before=ue.serving_cell.get_UE_CQI(ue.i)
      previous,tm=ue.serving_cell_ids[1]
      if s.strategy=='strongest_cell_simple_pathloss_model':
        celli=s.sim.get_strongest_cell_simple_pathloss_model(ue.xyz)
      elif s.strategy=='best_rsrp_cell':
        celli=s.sim.get_best_rsrp_cell(ue.i)
        if celli is None:
          celli=s.sim.get_strongest_cell_simple_pathloss_model(ue.xyz)
      else:
        print(f'MME.loop: strategy {s.strategy} not implemented, quitting!',file=stderr)
        exit()
      if celli==ue.serving_cell.i: continue
      if s.anti_pingpong>0.0 and previous==celli:
        if s.sim.env.now-tm<s.anti_pingpong:
          if s.verbosity>2:
            print(f't={float(s.sim.env.now):8.2f} handover of UE[{ue.i}] suppressed by anti_pingpong heuristic.',file=stderr)
          continue # not enough time since we were last on this cell
      ue.detach(quiet=True)
      ue.attach(s.sim.cells[celli])
      ue.send_rsrp_reports() # make sure we have reports immediately
      ue.send_subband_cqi_report()
      if s.verbosity>1:
        CQI_after=ue.serving_cell.get_UE_CQI(ue.i)
        print(f't={float(s.sim.env.now):8.2f} handover of UE[{ue.i:3}] from Cell[{oldcelli:3}] to Cell[{ue.serving_cell.i:3}]',file=stderr,end=' ')
        print(f'CQI change {CQI_before} -> {CQI_after}',file=stderr)

  def loop(s):
    '''
    Main loop of MME.
    '''
    yield s.sim.env.timeout(0.5*s.interval) # stagger the intervals
    print(f'MME started at {float(s.sim.env.now):.2f}, using strategy="{s.strategy}" and anti_pingpong={s.anti_pingpong:.0f}.',file=stderr)
    while True:
      s.do_handovers()
      yield s.sim.env.timeout(s.interval)

  def finalize(s):
    '''
    Function called at end of simulation, to implement any required finalization actions.
    '''
    pass

# END class MME

class RIC:
  '''
  Base class for a RIC, for hosting xApps.  The default does nothing.

  Parameters
  ----------
    sim : Sim
      Simulator instance which will manage this Scenario.
    interval : float
      Time interval between RIC actions.
    verbosity : int
      Level of debugging output (0=none).
  '''

  def __init__(s,sim,interval=10,verbosity=0):
    s.sim=sim
    s.interval=interval
    s.verbosity=verbosity

  def finalize(s):
    '''
    Function called at end of simulation, to implement any required finalization actions.
    '''
    pass

  def loop(s):
    '''
    Main loop of RIC class.  Must be overridden to provide functionality.
    '''
    print(f'RIC started at {float(s.sim.env.now):.2}.',file=stderr)
    while True:
      yield s.sim.env.timeout(s.interval)
# END class RIC

if __name__=='__main__': # a simple self-test

  np.set_printoptions(precision=4,linewidth=200)

  class MyLogger(Logger):
    def loop(s):
      while True:
        for cell in s.sim.cells:
          if cell.i!=0: continue # cell[0] only
          for ue_i in cell.reports['cqi']:
            if ue_i!=0: continue # UE[0] only
            rep=cell.reports['cqi'][ue_i]
            if not rep: continue
            xy= s.np_array_to_str(s.sim.UEs[ue_i].xyz[:2])
            cqi=s.np_array_to_str(cell.reports['cqi'][ue_i][1])
            tp= s.np_array_to_str(cell.reports['throughput_Mbps'][ue_i][1])
            s.f.write(f'{s.sim.env.now:.1f}\t{xy}\t{cqi}\t{tp}\n')
        yield s.sim.env.timeout(s.logging_interval)

  def test_01(ncells=4,nues=9,n_subbands=2,until=1000.0):
    sim=Sim()
    for i in range(ncells):
      sim.make_cell(n_subbands=n_subbands,MIMO_gain_dB=3.0,verbosity=0)
    sim.cells[0].set_xyz((500.0,500.0,20.0)) # fix cell[0]
    for i in range(nues):
      ue=sim.make_UE(verbosity=1)
      if 0==i: # force ue[0] to attach to cell[0]
        ue.set_xyz([501.0,502.0,2.0],verbose=True)
      ue.attach_to_nearest_cell()
    scenario=Scenario(sim,verbosity=0)
    logger=MyLogger(sim,logging_interval=1.0)
    ric=RIC(sim)
    sim.add_logger(logger)
    sim.add_scenario(scenario)
    sim.add_ric(ric)
    sim.run(until=until)

  test_01()
