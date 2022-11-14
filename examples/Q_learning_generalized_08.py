#!/usr/bin/env python
# Keith Briggs 2022-01-31 make reward a function of state and new_state (not action).  Test it with python3 Q_learning_chessboard_demo_04.py
# Keith Briggs 2022-01-24 linear option to episode
# Keith Briggs 2021-12-20 allow states to be tuples
# Keith Briggs 2021-07-26 normalize row of Q-table before exponentiating
# Keith Briggs 2021-07-16 experiment with "simulated annealing" variable exploration rate
# Keith Briggs 2021-07-07 pick_max rejigged
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
from numpy import array as np_array,argmax,exp as np_exp,sum as np_sum

class Q_learner:

  def __init__(s,reward_function,alpha=0.5,gamma=1.0,verbose=False):
    s.reward_function=reward_function # callback
    s.verbose=verbose
    s.alpha=alpha
    s.gamma=gamma
    s.Q={}
    s.last_action=None
    s.last_state =None

  def add_state(s,state,actions=[],init=1.0):
    s.Q.setdefault(state,{})
    for action in actions:
      s.Q[state][action]=init

  def episode(s,state,eps=0.0,linear=True,pick_max=False,verbose=False):
    Q_row=s.Q[state]
    if 0:
      actions=tuple(Q_row.keys())
      weights=np_array([Q_row[a] for a in actions])
    else: # is this better?
      items=Q_row.items()
      actions=tuple(item[0] for item in items)
      weights=tuple(item[1] for item in items)
    if not linear: # eps not used for linear case
      weights=np_array(weights)
      weights=np_exp(eps*weights/np_sum(weights))
    if pick_max:
      action=actions[argmax(weights)]
    else:
      action=choices(actions,weights,k=1)[0]
    if verbose: print(f'episode: state={state} weights={weights} action={action}',file=stderr)
    s.last_action=copy(action) # FIXME is copy needed?
    s.last_state=copy(state)
    return s.last_action

  def update_Q(s,new_state,reward_value=None):
    # client must remember to call this after each episode!
    mx=max(s.Q[new_state].values())
    if reward_value is None: # used stored reward_function
      s.Q[s.last_state][s.last_action]+=s.alpha*(s.reward_function(s.last_state,new_state)+s.gamma*mx-s.Q[s.last_state][s.last_action])
    else: # use passed reward_value
      s.Q[s.last_state][s.last_action]+=s.alpha*(reward_value+s.gamma*mx-s.Q[s.last_state][s.last_action])

  def show_Q(s,f=stdout,verbosity=0):
    states=list(s.Q.keys())
    states.sort()
    for state in states:
      actions=s.Q[state]
      p=set(actions.values())
      if verbosity==0 and len(p)==1: continue # don't print states never seen
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
    def reward_function(state,new_state):
      x,y=new_state[:2]
      return 1.0/(1e-20+hypot(x-goal[0],y-goal[1]))**4
    ql=Q_learner(reward_function=reward_function)
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
