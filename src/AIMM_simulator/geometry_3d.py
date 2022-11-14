# Keith Briggs 2021-11-22 was geometry_3d_01.py
# python version of some parts of geometry_3d.cc
# python3 geometry_3d_01.py

from sys import stderr,exit
import numpy as np
try: # if matplotlib is not installed, turn off plotting...
  from matplotlib import rcParams as matplotlib_rcParams
  import matplotlib.pyplot as plt
  from mpl_toolkits.mplot3d import Axes3D
  from mpl_toolkits.mplot3d.art3d import Poly3DCollection
  from fig_timestamp_00 import fig_timestamp
except:
  plt=None

class Plane:
  ''' Represents an infinite plane, defined by a point on the plane and a normal vector '''
  def __init__(s,point,normal):
    s.point =np.array(point ,dtype=np.float)
    s.normal=np.array(normal,dtype=np.float)
  def __repr__(s):
    return f'Plane(point={s.point},normal={s.normal})'

class Ray:
  ''' Represents a ray, defined by a tail (starting point) and a direction vector '''
  def __init__(s,tail,dv):
    s.tail=np.array(tail,dtype=np.float)
    s.dv  =np.array(dv,  dtype=np.float)
    s.dv/=np.linalg.norm(s.dv)
  def __repr__(s):
    return f'Ray({s.tail},{s.dv})'
  def intersect_triangle(s,t):
    ' convenience function '
    return intersect3D_RayTriangle(s,t)
  def distance_to_plane(ray,plane):
    '''
    Ray:   r(t)=r0+t*u
    Plane: points q s.t. (q-p0)@v=0
    Intersection: t s.t. (r0+t*u-p0)@v=0
                         t*u@v+(r0-p0)@v=0
                         t*u@v=-(r0-p0)@v
                         t=-(r0-p0)@v/u@v
                         t=(p0-r0)@v/u@v
    '''
    r0,u=ray.tail,ray.dv
    p0,v=plane.point,plane.normal
    v/=np.linalg.norm(v)
    u/=np.linalg.norm(u)
    uv=u@v
    if abs(uv)<1e-12: return np.inf # parallel
    return (p0-r0)@v/uv
  def reflect_in_plane(s,p):
    r0,u=s.tail,s.dv
    p0,v=p.point,p.normal
    v/=np.linalg.norm(v)
    u/=np.linalg.norm(u)
    uv=u@v
    d=v@(p0-r0)/uv
    intersection=r0+d*u
    reflected=u-2.0*uv*v
    return Ray(intersection,reflected/np.linalg.norm(reflected))
  def plot(s,ax,length=1.0,color='b',alpha=0.5):
    ''' Plots the ray in 3d '''
    if plt is None: return
    tip=s.tail+length*s.dv/np.linalg.norm(s.dv)
    x=(s.tail[0],tip[0])
    y=(s.tail[1],tip[1])
    z=(s.tail[2],tip[2])
    ax.plot(x,y,z,color=color,alpha=alpha)

class Triangle:
  ''' Represents a planar triangle in 3d space, defined by three points.  Unoriented. '''
  def __init__(s,p0,p1,p2):
    s.p0=np.array(p0,dtype=np.float)
    s.p1=np.array(p1,dtype=np.float)
    s.p2=np.array(p2,dtype=np.float)
    s.side0=s.p1-s.p0
    s.side1=s.p2-s.p0
    s.normal=np.cross(s.side0,s.side1)
    s.plane=Plane(s.p0,s.normal)
  def __repr__(s):
    return f'Triangle({s.p0},{s.p1},{s.p1})'
  def __add__(s,c):
    ' return a new Triangle, translated by the vector c '
    return Triangle(s.p0+c,s.p1+c,s.p2+c)
  def plot(s,ax,color='y',alpha=0.5,drawedges=True):
    ''' Plots the triangle in 3d. For kwargs, see https://matplotlib.org/stable/api/collections_api.html#matplotlib.collections.Collection '''
    if plt is None: return
    if drawedges:
      pc=Poly3DCollection([(s.p0,s.p1,s.p2)],facecolor=color,edgecolor='olive',linewidth=0.5,alpha=alpha)
    else:
      pc=Poly3DCollection([(s.p0,s.p1,s.p2)],facecolor=color,linewidth=0.25,alpha=alpha)
    ax.add_collection3d(pc)

def intersect3D_RayTriangle(r,t):
  #  find the 3D intersection of a ray with a triangle
  #  Input:  a ray R, and a triangle T
  #  Return: intersection point, and distance to triangle.
  u=t.side0
  v=t.side1
  n=t.normal
  d=r.dv
  d/=np.linalg.norm(d) # assumes unit direction vector
  w0=r.tail-t.p0
  a=-n@w0
  b=n@d
  if abs(b)<1e-12:                      # ray is  parallel to triangle plane
    if abs(a)<1e-12: return r.tail,0.0  # ray lies in triangle plane
    return None,np.inf                  # ray disjoint from plane
  #  get intersect point of ray with triangle plane...
  q=a/b
  if q<0.0: return None,np.inf
  # for a segment, also test if q>1.0 => no intersect...
  I=r.tail+q*d
  # is I inside T?
  w=I-t.p0
  uu=u@u; uv=u@v; vv=v@v; wu=w@u; wv=w@v
  D=uv*uv-uu*vv
  s=(uv*wv-vv*wu)/D
  if s<0.0 or s>  1.0: return None,np.inf # I is outside T
  z=(uv*wu-uu*wv)/D
  if z<0.0 or s+z>1.0: return None,np.inf # I is outside T
  return I,q # it does intersect

class Panel:
  ''' Represents a collection of triangles (which must be parallel) making up a single flat wall panel. '''
  def __init__(s,triangles):
    if len(triangles)<1:
      print('Panel: empty triangle list!')
      exit(1)
    s.triangles=triangles
    # check normals are parallel...
    n0=triangles[0].normal
    for triangle in triangles[1:]:
      if np.linalg.norm(np.cross(triangle.normal,n0))>1e-10:
        print('Panel: triangles are not parallel!')
        exit(1)
  def __repr__(s):
    r=','.join([str(t) for t in s.triangles])
    return f'Panel({r})'
  def __iter__(s):
    return iter(s.triangles)
  def plot(s,ax,color='b',alpha=0.5,drawedges=True):
    for triangle in s.triangles:
      triangle.plot(ax,color=color,alpha=alpha,drawedges=drawedges)

class RIS: # TODO
  ''' TODO a RIS. '''
  def __init__(s,panel):
    s.panel=panel
  def __repr__(s):
    return f'RIS({s.panel})'

class Building:
  ''' Represents a collection of panels making up a building. '''
  def __init__(s,panels):
    s.panels=panels
  def __repr__(s):
    r=','.join([str(p) for p in s.panels])
    return f'Building({r})'
  def plot(s,ax,color='b',alpha=0.5,drawedges=True):
    for panel in s.panels:
      panel.plot(ax,color=color,alpha=alpha,drawedges=drawedges)
  def number_of_panels_cut(s,ray,max_distance,dbg=False):
    k,d,dd=0,0.0,0.0
    d_seen=[]
    for panel in s.panels:
      panel_cut=False
      for triangle in panel:
        I,d=ray.intersect_triangle(triangle)
        if dbg: print(f'# I={I} d={d:.2f}',file=stderr)
        if I is not None and d>1e-9: # this triangle is cut (and is not at the tail of the ray)
          panel_cut,dd=True,d
          break # this panel is cut, so we don't need to check other triangles
      if panel_cut:
        if dbg: print(f'{panel} is cut, dd={dd:.2f}',file=stderr)
        if max_distance<dd<np.inf: return k,set(d_seen)
        if all(abs(dd-d)>1e-6 for d in d_seen): k+=1 # do not count identical panels
        d_seen.append(dd)
      if dbg: print(f'# panel_cut={panel_cut} k={k}',file=stderr)
    return k,set(d_seen)

def draw_building_3d(building,rays=[],line_segments=[],dots=[],color='y',fontsize=6,limits=[(0,10),(0,10),(0,5)],labels=['','',''],drawedges=True,show=True,pdffn='',pngfn='',dbg=False):
  ' General function to draw a building, also rays and lines. '
  matplotlib_rcParams.update({'font.size': fontsize})
  fig=plt.figure()
  fig_timestamp(fig)
  ax=Axes3D(fig)
  building.plot(ax,color=color,drawedges=drawedges)
  for ray in rays:
    ray.plot(ax,length=20,color='r',alpha=1)
    k,dists=building.number_of_panels_cut(ray,max_distance=20,dbg=False)
    if dbg: print(f'{ray} has {k} cuts')
    for dist in dists: # plot intersections...
      x=(ray.tail[0]+dist*ray.dv[0],)
      y=(ray.tail[1]+dist*ray.dv[1],)
      z=(ray.tail[2]+dist*ray.dv[2],)
      ax.plot(x,y,z,color='k',marker='o',ms=6,alpha=1.0)
  if line_segments: ax.plot(*line_segments,color='b',marker='o',ms=1,lw=1,alpha=1.0)
  for dot in dots:
    ax.plot(*dot,color='r',marker='o',ms=8,alpha=1.0)
  if labels[0]: ax.set_xlabel(labels[0])
  if labels[1]: ax.set_ylabel(labels[1])
  if labels[2]: ax.set_zlabel(labels[2])
  ax.set_xlim(limits[0])
  ax.set_ylim(limits[1])
  ax.set_zlim(limits[2])
  # https://stackoverflow.com/questions/8130823/set-matplotlib-3d-plot-aspect-ratio
  limits=np.array([getattr(ax,f'get_{axis}lim')() for axis in 'xyz'])
  ax.set_box_aspect(np.ptp(limits,axis=1))
  if show: plt.show()
  if pngfn:
    fig.savefig(pngfn)
    print(f'eog {pngfn} &',file=stderr)
  if pdffn:
    fig.savefig(pdffn)
    print(f'e {pdffn} &',file=stderr)

def test_00():
  p=Plane((0,0,0),(1,1,1))
  print(p.point)
  print(p.normal)
  t=Triangle((0,0,0),(1,1,0),(1,0,0))
  r=Ray((0.75,0.75,-1.0),(0,-0.2,1))
  I,q=intersect3D_RayTriangle(r,t)
  print(I,q)

def test_01():
  # set of unit-square vertical panels at integer x values
  panels=[]
  for i in range(10):
    panel=Panel([Triangle((i,0,0),(i,1,0),(i,1,1)),Triangle((i,0,0),(i,0,1),(i,1,1))])
    panels.append(panel)
  b=Building(panels)
  r=Ray((-1.0,0.8,0.7),(1,0,0))
  k,d=b.number_of_panels_cut(r,1.5)
  print(k)

def cube(a,b,c=(0.0,0.0,0.0)):
  # deprecated - use block()
  ' cube c+[a,b]x[a,b]x[a,b], with each face a square Panel of two Triangles '
  c=np.array(c,dtype=np.float)
  return (
    Panel([Triangle((a,a,a),(a,b,a),(b,b,a))+c,Triangle((a,a,a),(b,a,a),(b,b,a))+c]),
    Panel([Triangle((a,a,b),(a,b,b),(b,b,b))+c,Triangle((a,a,b),(b,a,b),(b,b,b))+c]),
    Panel([Triangle((a,a,a),(a,a,b),(a,b,b))+c,Triangle((a,a,a),(a,b,a),(a,b,b))+c]),
    Panel([Triangle((b,a,a),(b,a,b),(b,b,b))+c,Triangle((b,a,a),(b,b,a),(b,b,b))+c]),
    Panel([Triangle((a,a,a),(b,a,a),(b,a,b))+c,Triangle((a,a,a),(a,a,b),(b,a,b))+c]),
    Panel([Triangle((a,b,a),(b,b,a),(b,b,b))+c,Triangle((a,b,a),(a,b,b),(b,b,b))+c]),
  )

#def rectangle(c0,c1):
#  ' rectangular panel with opposite corners c0 and c1 '
#  a,b,c=c0
#  d,e,f=c1
#  return Panel([Triangle((a,b,c),(d,b,c),(d,e,f)),
#                Triangle((a,b,c),(a,e,f),(d,b,f))])

def block(c0,c1):
  ''' Represents a rectangular block with opposite corners c0 and c1, with each face a rectangular Panel '''
  a,b,c=c0
  d,e,f=c1
  return (
    Panel([Triangle((a,b,c),(d,b,c),(d,b,f)),Triangle((a,b,c),(a,b,f),(d,b,f))]), # front
    Panel([Triangle((a,e,c),(d,e,c),(d,e,f)),Triangle((a,e,c),(a,e,f),(d,e,f))]), # back
    Panel([Triangle((a,b,c),(a,e,c),(a,e,f)),Triangle((a,b,c),(a,b,f),(a,e,f))]), # one side
    Panel([Triangle((d,b,c),(d,e,c),(d,e,f)),Triangle((d,b,c),(d,b,f),(d,e,f))]), # opposite side
    Panel([Triangle((a,b,c),(d,b,c),(d,e,c)),Triangle((a,b,c),(d,e,c),(a,e,c))]), # floor
    Panel([Triangle((a,b,f),(d,b,f),(d,e,f)),Triangle((a,b,f),(d,e,f),(a,e,f))]), # ceiling
  )

def test_02():
  room0=cube(0,1)
  room1=cube(0,1,c=(1.1,0,0))
  room2=cube(0,1,c=(2,0,0))
  b=Building(room0+room1+room2)
  #print(b)
  r=Ray((-0.01,0.1,0.2),(1.0,0.0,0.0))
  k,d=b.number_of_panels_cut(r,max_distance=2.9,dbg=False)
  print(f'{k} intersections of {r} with Building')

def test_03():
  r=Ray((0.0,0.0,0.0),(1.0,1.0,1.0))
  p=Plane((0.5,0.5,0.5),(1,1,1))
  ref=r.reflect_in_plane(p)
  print(ref)
  panel=Panel([Triangle((0,0,0),(0,0.866,0),(0,1,0))])
  ris=RIS(panel)
  print(f'ris={ris}')

def test_04(dbg=False,fontsize=4):
  fig=plt.figure()
  ax=Axes3D(fig)
  t0=Triangle((0,0,0),(0,1,0),(0,0,1))
  t1=Triangle((0,1,1),(0,1,0),(0,0,1))
  panel=Panel([t0,t1])
  room0=cube(0,1)
  room1=cube(0,1,c=(1.0,0,0))
  room2=cube(0,1,c=(2.1,0,0))
  room2=cube(0,0.5,c=(0,1.0,0))
  b=Building(room0+room1+room2)
  b.plot(ax,color='y')
  r=Ray((0.0,0.0,0.0),(1.0,0.3,0.2))
  p=Plane((0,0,2),(0,0,1))
  if dbg: print(f'p={p}')
  d=r.distance_to_plane(p)
  k,dists=b.number_of_panels_cut(r,max_distance=10,dbg=False)
  for dist in dists: # plot intersections...
    x=(r.tail[0]+dist*r.dv[0],)
    y=(r.tail[1]+dist*r.dv[1],)
    z=(r.tail[2]+dist*r.dv[2],)
    ax.plot(x,y,z,color='k',marker='o',ms=6,alpha=1.0)
    print(dist,x,y,z)
  if dbg: print(f'r={r} distance_to_plane={d} number_of_panels_cut={k}')
  r.plot(ax,length=d,color='r',alpha=1)
  ref=r.reflect_in_plane(p)
  if dbg: print(f'ref={ref}')
  ref.plot(ax,length=1,color='b',alpha=1)
  ax.set_xlim((0,3.5e0))
  ax.set_ylim((0,3.0e0))
  ax.set_zlim((0,2.0e0))
  ax.set_xlabel('$x$')
  ax.set_ylabel('$y$')
  ax.set_zlabel('$z$')
  plt.show()
  fig.savefig('foo.pdf')

def test_05():
  ' the best example to follow! '
  blk0=block(np.array([0, 0,0]),np.array([5,10,3]))
  blk1=block(np.array([0,10,0]),np.array([6,12,2]))
  blk2=block(np.array([0,12,0]),np.array([6,14,2]))
  blk3=block(np.array([0,14,0]),np.array([6,16,2]))
  blk4=block(np.array([0,16.5,0]),np.array([6,17,2]))
  fence=Panel([Triangle((8,0,0),(8,15,0),(8,15,1)),
               Triangle((8,0,1),(8, 0,0),(8,15,1))])
  b=Building(blk0+blk1+blk2+blk3+blk4+(fence,))
  ray0=Ray((0.3,0.3,2.0),(0.1,1,-0.01))
  line_segments=[(8,8),(18,18),(0,4)] # [xs,ys,zs]
  draw_building(b,rays=[ray0],line_segments=line_segments,color='y',limits=[(0,10),(0,20),(0,4)],labels=['$x$','$y$','$z$'],fontsize=6,show=True,pdffn='img/building0.pdf',pngfn='img/building0.png')

if __name__=='__main__':
  test_05()
