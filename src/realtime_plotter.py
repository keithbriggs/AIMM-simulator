#!/usr/bin/env python3
# Keith Briggs 2021-12-14 naxes, not necessarily equal to nplots
# Keith Briggs 2021-12-14 column_to_axis_map
# Keith Briggs 2021-10-26 does matplotlib version=3.3.4 cause problems?
# Keith Briggs 2021-07-19 try saving animation
# Keith Briggs 2021-07-06 -extra
# Keith Briggs 2021-03-18 cleanup
# Keith Briggs 2021-02-03 read stdin
# Keith Briggs 2020-09-30 move labels etc to __init__
# Keith Briggs 2020-09-17 class for animated real-time plotting
# Keith Briggs 2020-06-17 class

from sys import stdin,stderr,exit,argv
from os.path import basename
from time import time,sleep,strftime,localtime
import numpy #as np
from random import random
import argparse
import matplotlib.pyplot as plt
from matplotlib import animation,use as matplotlib_use
from matplotlib.patches import ConnectionPatch
from matplotlib.lines import Line2D
from matplotlib import __version__ as matplotlib_version
matplotlib_use('TkAgg') # TkAgg or wxAgg or Qt5Agg or Qt4Agg
matplotlib_use('Qt5Agg') # TkAgg or wxAgg or Qt5Agg or Qt4Agg
_t0=time()
_second_call=False

def fig_timestamp(fig,author='',brand='AIMM Sim —',fontsize=6,color='blue',alpha=0.7,rotation=0,prespace='  '):
  # Keith Briggs 2020-01-07
  # https://riptutorial.com/matplotlib/example/16030/coordinate-systems-and-text
  date=strftime('%Y-%m-%d %H:%M',localtime())
  fig.text( # position text relative to Figure
    0.01,0.005,prespace+'%s %s'%(brand+' '+author,date,),
    ha='left',va='bottom',fontsize=fontsize,color=color,
    rotation=rotation,
    transform=fig.transFigure,alpha=alpha)

class Animate:

  def __init__(s,getter,naxes,nplots,xlim=(0,1),ylims={},xlabel='',ylabels={},legends={},title='',lw=2,image_fnbase='',tmax=None,figscale=1.5,final_sleep_time=5,author='',extra='',inputfile='',column_to_axis_map={},xlabel_fontsize=10,ylabel_fontsize=10,title_fontsize=12,cmap_type='hsv'):
    # https://matplotlib.org/stable/tutorials/colors/colormaps.html
    s.getter=getter
    s.naxes=naxes
    s.nplots=nplots
    s.xlim,s.ylims=xlim,ylims
    s.lw=lw
    s.xlabel,s.ylabels,s.title=xlabel,ylabels,title
    s.image_fnbase=image_fnbase
    s.legends=legends
    s.tmax=tmax
    s.lines=[]
    s.final_sleep_time=final_sleep_time
    s.x=[]
    s.ys=[[] for i in range(s.nplots)]
    s.fig=plt.figure(figsize=(figscale*6.4,figscale*4.8))
    #s.fig.tight_layout()
    if 0: # old
      if column_to_axis_map:
        s.column_to_axis_map=column_to_axis_map
      else:
        s.column_to_axis_map=dict((i,i) for i in range(s.naxes)) # default
    else:
      if column_to_axis_map:
        s.column_to_axis_map={} # Keith Briggs 2022-08-08
      else:
        s.column_to_axis_map=dict((i,i) for i in range(s.naxes)) # default
      if s.nplots>s.naxes: # map extra plots to last axis (so we don't lose any)
        for x in range(s.naxes,s.nplots):
          s.column_to_axis_map[x]=s.naxes-1
      for x,y in column_to_axis_map.items():
        s.column_to_axis_map[x]=y # overwrite defaults with passed argument
    s.ax=[s.fig.add_subplot(s.naxes,1,1+i) for i in range(s.naxes)]
    s.fig.align_ylabels(s.ax)
    print(f'  naxes={s.naxes} nplots={s.nplots}',file=stderr)
    print(f'  column_to_axis_map={s.column_to_axis_map}',file=stderr)
    print(f'  ylims={s.ylims}',file=stderr)
    s.transfigure=s.fig.transFigure.inverted()
    s.ax.reverse() # ax[0] at bottom
    s.extra=extra
    s.inputfile=inputfile
    s.anim=None # gets created later (in run())
    if 0: # old
      s.colors=('r','g','b','c','y','k',)
      s.ncolors=len(s.colors)
    else: # better
      s.ncolors=nplots
      s.cmap=plt.get_cmap(cmap_type)
      s.colors=tuple(s.cmap(0.9*i/s.ncolors) for i in range(s.ncolors))
    props=dict(boxstyle='round',facecolor='white',alpha=0.8)
    for i in range(s.naxes):
      if i==0: # bottom plot
        if s.xlabel: s.ax[i].set_xlabel(s.xlabel,fontsize=xlabel_fontsize)
      else: # other plots
       s.ax[i].xaxis.set_ticklabels([])
      if i in ylims: s.ax[i].set_ylim(*ylims[i])
      if i in ylabels: s.ax[i].set_ylabel(s.ylabels[i],fontsize=ylabel_fontsize)
      s.ax[i].grid(lw=0.5,alpha=0.5,color='gray')
      s.ax[i].set_xlim(*xlim)
      s.ax[i].xaxis.set_major_locator(plt.MaxNLocator(10))
      if s.naxes<4: # set number of ticks on y axes...
        s.ax[i].yaxis.set_major_locator(plt.MaxNLocator(6))
      else:
        s.ax[i].yaxis.set_major_locator(plt.MaxNLocator(4))
      if i in s.legends: # FIXME
        try:
          lx,ly,lt=s.legends[i].split('\t')
          lx,ly=float(lx),float(ly) # legend position
          s.ax[i].text(lx,ly,lt,fontsize=8,verticalalignment='top',horizontalalignment='right',bbox=props)
        except:
          print('legend must have format "x<tab>y<tab>text"',file=stderr)
    if s.title: s.ax[-1].set_title(s.title,fontsize=title_fontsize)
    s.pdf_saved=False
    fig_timestamp(s.fig,author=author,rotation=0,fontsize=8)

  def init(s):
    for line in s.lines: line.set_data([],[])
    return s.lines

  def animate(s,k,dbg=True):
    global _second_call
    xy=next(s.getter)
    if xy is None or len(xy)==0: # no more data
      if dbg: print(f'{basename(__file__)}: input data exhausted.',file=stderr)
      if not _second_call:
        #for i in range(s.nplots): # replot; it gets deleted when show() returns
        #  s.ax[i].plot(s.x,s.ys[i],lw=s.lw,color=s.colors[i%5],alpha=1)
        try: # Keith Briggs 2022-08-08 FIXME why is this needed?
          #print(f'not _second_call: s.column_to_axis_map={s.column_to_axis_map}',file=stderr)
          for i,j in s.column_to_axis_map.items(): # 2021-12-17 replot
            #print(f'not _second_call: i={i} j={j}',file=stderr)
            if i<len(s.ys): s.ax[j].plot(s.x,s.ys[i],lw=s.lw,color=s.colors[i%s.ncolors],alpha=1) # line
            #s.ax[j].plot(s.x,s.ys[i],lw=0.5,marker='o',markersize=0.5,color=s.colors[i%s.ncolors]) # dot only
        except:
          print(f'not _second_call: plot failed!',file=stderr)
        if s.extra: # plot "extra" again to make sure it's on top!
          s.transfigure=s.fig.transFigure.inverted() # this needs updating!
          try:
            exec(s.extra)
            print(f'"extra" executed at t={time()-_t0:.2f}',file=stderr)
            s.extra=None # make sure it's only done once
          except Exception as e:
            print(f'extra="{s.extra}" failed with message "{str(e)}"!',file=stderr)
      if s.image_fnbase:
        print(f'animate: saving final image files at t={time()-_t0:.2f}...',file=stderr,end='')
        s.fig.savefig(s.image_fnbase+'.png')
        s.fig.savefig(s.image_fnbase+'.pdf')
        print('done.',file=stderr)
        print('eog    '+s.image_fnbase+'.png &',file=stderr)
        print('evince '+s.image_fnbase+'.pdf &',file=stderr)
      _second_call=True
      sleep(s.final_sleep_time)
      exit(0)
    # else (xy is not None)...
    s.x.append(xy[0]) # time
    if 1: # old way
      for j in range(s.nplots): s.ys[j].append(xy[1+j])
    else: # FIXME
      for i,j in s.column_to_axis_map.items():
        print(f'{i}->{j}',file=stderr)
        s.ys[j].append(xy[1+i])
    #print(f'{s.ys}',file=stderr)
    #exit()
    for i,ysi in enumerate(s.ys):
      s.lines[i].set_data(s.x,ysi)
      #s.lines[s.column_to_axis_map[i]].set_data(s.x,ysi)
    return s.lines

  def run_OLD(s,nframes=1000):
    plt.ion()
    for i in range(s.naxes):
      lobj=s.ax[i].plot([],[],lw=s.lw,color=s.colors[i%s.ncolors])[0]
      s.lines.append(lobj)
    s.anim=animation.FuncAnimation(s.fig,s.animate,init_func=s.init,frames=nframes,interval=0.01,blit=True,save_count=1000) #,repeat=False)
    plt.show(block=True)

  def run(s,nframes=1000):
    # create a plot object for each plot, and map them to axes
    plt.ion()
    for i,j in s.column_to_axis_map.items():
      print(f'run: column[{i}] is mapped to axis [{j}].',file=stderr)
      s.lines.append(s.ax[j].plot([],[],lw=s.lw,color=s.colors[i%s.ncolors],alpha=1)[0])
      #s.lines.append(s.ax[j].plot(s.x,s.ys[i],lw=0.0,marker='o',markersize=0.5,color=s.colors[i%s.ncolors])[0]) # dot only
    s.anim=animation.FuncAnimation(s.fig,s.animate,init_func=s.init,frames=nframes,interval=0.01,blit=True,save_count=1000) #,repeat=False)
    plt.show(block=True)

  def run_noshow(s,nframes=2*5000):
    # FIXME need a good way to set nframes
    for i in range(s.naxes):
      axi=s.ax[i]
      axi.plot([],[],lw=s.lw)
      lobj=axi.plot([],[],lw=s.lw,color=s.colors[i%s.ncolors])[0]
      s.lines.append(lobj)
    s.anim=animation.FuncAnimation(s.fig,s.animate,init_func=s.init,frames=nframes,interval=0.01,blit=True,save_count=nframes)
    plt.draw()
    s.save_mp4()

  def save_mp4(s):
    print(f's.anim={s.anim}',file=stderr)
    writervideo=animation.FFMpegWriter(fps=30,bitrate=2000)
    #print(f'writervideo={writervideo} ...',file=stderr)
    filename_mp4=f'{s.inputfile}.mp4'
    print(f'Writing {filename_mp4} ...',end='',file=stderr); stderr.flush()
    s.anim.save(filename_mp4,writer=writervideo)
    print('done',file=stderr)

  def add_line_betweenaxes(s,xy0,xy1,ax0,ax1,color='r',lw=1,arrowstyle='-',shrinkB=0): # 2021-10-28
    # Draw an arrow between two points in data coordinates, possibly 
    # in different axes.
    s.fig.add_artist(ConnectionPatch(
      xyA=xy0, coordsA=s.ax[ax0].transData,
      xyB=xy1, coordsB=s.ax[ax1].transData,
      arrowstyle=arrowstyle,shrinkB=shrinkB,color=color,lw=lw)
    )

def _getter_random(n):
  global _k,last
  while True:
    if _k>n: yield None
    _k+=1
    x=numpy.random.random(3)
    nxt=0.2*x+0.8*last
    last=nxt
    yield _k,nxt[0],nxt[1],10*nxt[2]

def getter_stdin(nrowsmax=None):
  k=0
  while True:
    if nrowsmax and k>nrowsmax: yield None
    k+=1
    line=stdin.readline()
    if not line: yield None
    if line and line[0]=='#':
      continue # 2021-10-29
    else:
      yield numpy.fromstring(line,sep='\t') # 2021-12-15
      #yield numpy.array(list(map(float,line.split()))) # 2021-07-15

def getter_tsv(tsv,skip=10):
  # Keith Briggs 2021-07-19 - return rows of a pre-loaded tsv file
  k=0
  nrows=tsv.shape[0]
  while k<nrows:
    yield tsv[k]
    k+=skip
  print('getter_tsv done',file=stderr)
  yield None

def test_01(n=100,naxes=3):
  animate=Animate(_getter_random(n),naxes=naxes,ncols=naxes,xlim=(0,n),ylims=[(0,1),(0,1),(0,10),],xlabel='time',ylabels=['random']*naxes,legends=['90\t0.9\trandom','90\t0.9\trandom','90\t0.9\trandom'])
  animate.run(nframes=n)

def main():
  parser=argparse.ArgumentParser()
  parser.add_argument('--selftest',       help='self-test',action='store_true')
  parser.add_argument('-naxes',type=int, help='number of axes',default=0)
  parser.add_argument('-nplots',type=int,help='number of plots',default=1)
  #parser.add_argument('-ncols',type=int,  help='number of columns to read')
  parser.add_argument('-tmax',type=float,   help='t_max',default=100.0)
  parser.add_argument('-xlabel',type=str,     help='x axis label',default='time')
  parser.add_argument('-fst',type=float,  help='final sleep time',default=5.0)
  parser.add_argument('-fnb',type=str,    help='filename base',default='')
  parser.add_argument('-ylims',type=str,  help='y limits (dict)',default='')
  parser.add_argument('-ylabels',type=str,help='ylabels (dict)',default='')
  parser.add_argument('-title',type=str,  help='figure title',default='')
  parser.add_argument('-lw',type=str,     help='linewidth',default=2)
  parser.add_argument('-author',type=str, help='author name for plot bottom margin',default='')
  parser.add_argument('-extra',type=str,  help='extra features to be added to the plot; raw python code',default='')
  parser.add_argument('-inputfile',type=str,  help='file to read input from instead of stdin; in this case the plot is not displayed, but written to an mp4 file',default='')
  parser.add_argument('-column_to_axis_map',type=str,  help='column_to_axis_map',default='{}')
  args=parser.parse_args()
  if args.selftest:
    global _k,last,nplots
    _k=0; last=numpy.zeros(3); test_01(); exit()
  if args.naxes==0: # default
    args.naxes=args.nplots
  #if args.ncols: ncols=args.ncols
  #else: ncols=nplots
  xlim=(0.0,args.tmax),
  ylims={i: (0.0,20.0) for i in range(args.naxes)} # default ylims
  if args.ylims:
    try:
      d=eval(args.ylims)
      if type(d) is dict:
        for q in d: ylims[q]=d[q]
      elif type(d) in (tuple,list):
        for i,q in enumerate(d): ylims[i]=q
    except:
      print(f'Could not parse -ylims="{args.ylims}"',file=stderr)
  ylabels={i: f'$y_{{{i}}}$' for i in range(args.naxes)}
  if args.ylabels:
    try:
      d=eval(args.ylabels)
      if type(d) is dict:
        for q in d: ylabels[q]=d[q]
      elif type(d) is list: # 2021-11-09 allow list of labels
        for i,q in enumerate(d): ylabels[i]=q
      elif type(d) is str:
        for q in range(args.naxes): ylabels[q]=f'{d}$_{{{q}}}$'
    except:
      print(f'Could not parse -ylabels="{args.ylabels}"',file=stderr)
  if args.inputfile and args.inputfile not in ('stdin','-',):
    try:
      tsv=numpy.loadtxt(args.inputfile)
      nrows=tsv.shape[0]
      print(f'Loaded tsv file "{args.inputfile}", {nrows} rows',file=stderr)
    except:
      print(f'Could not load tsv file "{args.inputfile}", quitting',file=stderr)
      exit(1)
    getter=getter_tsv(tsv)
  else:
    getter=getter_stdin()
  if args.naxes>4: plt.rcParams.update({'font.size': 6})
  #column_to_axis_map={}
  #column_to_axis_map={0:0,1:0,2:1,3:2,4:2,5:3,6:4} # FIXME
  #column_to_axis_map={1:0,2:1,3:2,4:2,5:3,6:4} # FIXME
  try:
    column_to_axis_map=eval(args.column_to_axis_map)
  except:
    print(f'{basename(__file__)}: could not parse column_to_axis_map={column_to_axis_map},using default',file=stderr)
    column_to_axis_map={}
  animate=Animate(
    getter,
    naxes=args.naxes,
    nplots=args.nplots,
    #ncols=ncols, # number of columns read from input file
    xlim=xlim,
    title=args.title,
    lw=args.lw,
    ylims=ylims,
    xlabel=args.xlabel,
    ylabels=ylabels,
    legends=[],
    final_sleep_time=args.fst,
    image_fnbase=args.fnb,
    author=args.author,
    extra=args.extra,
    inputfile=args.inputfile,
    column_to_axis_map=column_to_axis_map
  )
  if args.inputfile in ('','stdin','-',):
    animate.run(nframes=100)
  else:
    animate.run_noshow()

if __name__=='__main__':
  print(f'matplotlib version={matplotlib_version}',file=stderr)
  print(f'{basename(__file__)} starting...',file=stderr)
  plt.rcParams.update({'font.size': 12}) 
  plt.rcParams.update({'figure.autolayout': True})
  # https://matplotlib.org/stable/tutorials/intermediate/constrainedlayout_guide.html
  # 'figure.autolayout': True, 
  # 'figure.constrained_layout.use': True
  main()
