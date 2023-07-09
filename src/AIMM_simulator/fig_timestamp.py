# Keith Briggs 2020-02-12

from time import time,strptime,strftime,localtime

def fig_timestamp(fig,fontsize=6,color='black',alpha=0.7,rotation=0,prespace='  ',author='Keith Briggs'):
  # Keith Briggs 2020-01-07
  # https://riptutorial.com/matplotlib/example/16030/coordinate-systems-and-text
  date=strftime('%Y-%m-%d %H:%M',localtime())
  fig.text( # position text relative to Figure
    0.01,0.005,prespace+f'{author} {date}',
    ha='left',va='bottom',fontsize=fontsize,color=color,
    rotation=rotation,
    transform=fig.transFigure,alpha=alpha)
