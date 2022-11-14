# Keith Briggs 2021-01-20

from time import strftime,localtime

def fig_timestamp(fig,author='',fontsize=6,color='gray',alpha=0.7,rotation=0,prespace='  '):
  # Keith Briggs 2020-01-07
  # https://riptutorial.com/matplotlib/example/16030/coordinate-systems-and-text
  date=strftime('%Y-%m-%d %H:%M',localtime())
  fig.text( # position text relative to Figure
    0.01,0.005,prespace+'%s %s'%(author,date,),
    ha='left',va='bottom',fontsize=fontsize,color=color,
    rotation=rotation,
    transform=fig.transFigure,alpha=alpha)
