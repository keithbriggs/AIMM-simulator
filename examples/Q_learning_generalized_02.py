#!/usr/bin/env python
# Keith Briggs 2021-06-15 try out some improvements
# Keith Briggs 2020-11-30 states and actions now dicts
# Keith Briggs 2020-11-10 fix Q updating
# Keith Briggs 2020-11-06 better defns of states and actions
# rewrite to use a callback function for reward
# Keith Briggs 2020-09-23 was ~/python/Q_learning_02.py

from sys import stdout,stderr,exit
from copy import copy
from math import hypot
from random import choices
from numpy import argmax

class Q_learner:

  def __init__(s,reward,pick_max=False,alpha=0.5,gamma=1.0,verbose=False):
    s.reward=reward # callback
    s.pick_max=pick_max
    s.verbose=verbose
    s.nstates=0
    s.alpha,s.gamma=alpha,gamma
    s.beta=1.0-s.alpha
    s.Q={}
    s.last_action=None
    s.last_state=None
  
  def add_state(s,state,actions=[],init=1.0e-2):
    s.Q[state]={}
    s.nstates=len(s.Q)
    for action in actions:
      s.Q[state][action]=init

  def episode(s,state,verbose=False):
    actions=list(s.Q[state].keys())
    weights=list(s.Q[state].values())
    if s.pick_max:
      action=actions[argmax(weights)] # FIXME
    else:
      action=choices(actions,weights=weights,k=1)[0]
    if verbose: print('episode: state=',state,'action=',action)
    s.last_action=action
    s.last_state=copy(state)
    return action
  
  def update_Q(s,new_state,reward=None):
    # client must remember to call this after each episode!
    mx=max(s.Q[new_state].values())
    if reward is not None: # use passed reward
      s.Q[s.last_state][s.last_action]+=s.alpha*(reward+s.gamma*mx-s.Q[s.last_state][s.last_action])
    else: # used stored reward function
      s.Q[s.last_state][s.last_action]+=s.alpha*(s.reward(s.last_action)+s.gamma*mx-s.Q[s.last_state][s.last_action])

  def show_Q(s,f=stdout):
    states=list(s.Q.keys())
    states.sort()
    for state in states:
      actions=s.Q[state]
      p=set(actions.values())
      if len(p)==1: continue # don't print states never seen
      a=dict((x,float(f'{actions[x]:.2f}')) for x in actions)
      print(f'state={state}\tactions={a}',file=f)
 
if __name__ == '__main__':
  from random import seed
  seed(1)

  def test_00():
    ni,nj=4,3
    goal=ni-1,nj-1,0
    blocked=[(-1,j,0) for j in range(nj)]+\
            [(ni,j,0) for j in range(nj)]+\
            [(i,-1,0) for i in range(ni)]+\
            [(i,nj,0) for i in range(ni)]+\
            [(ni//2,nj//2,0)]
    ql=Q_learner(reward=lambda state: 1.0/(1e-6+hypot(state[0]-goal[0],state[1]-goal[1])))
    for i in range(ni):
      for j in range(nj):
        if (i,j,0) in blocked: continue
        actions=[]
        for action in ((0,1),(1,0),(-1,0),(0,-1),):
          if (action[0]+i,action[1]+j,0) not in blocked:
            actions.append(action)
        ql.add_state((i,j,0),actions)
    # training...
    state=(0,0,0)
    for i in range(100000):
      action=ql.episode(state)
      state=(state[0]+action[0],state[1]+action[1],0)
      ql.update_Q(state)
    ql.show_Q()
    # check it has learnt...
    state=(0,0,0)
    for i in range(1000):
      action=ql.episode(state)
      state=(state[0]+action[0],state[1]+action[1],0)
      print('episode % 3d: state='%i,state,'action=',action)
      if state==goal: break
      ql.update_Q(state)
 
  #np.random.seed(1)
  #np.set_printoptions(precision=4,suppress=True,linewidth=150,formatter={'complexfloat': lambda x: '% .4f%s%.4fj'%(x.real,('+','-')[x.imag<0],abs(x.imag),)})
  test_00()
