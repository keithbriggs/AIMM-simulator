#!/bin/bash
# Keith Briggs 2022-01-31

python3 AIMM_simulator_RIC_example_01.py | \
   ./realtime_plotter.py \
   -author='Keith Briggs' \
   -nplots=7 \
   -tmax=10000 \
   -fst=30 \
   -fnb='img/AIMM_simulator_RIC_example' \
   -ylims='{0: (-100,100), 1: (-100,100), 2: (-1,16), 3: (-1,16), 4: (-1,16), 5: (0,50), 6: (0,9)}' \
   -ylabels='{0: "$x$", 1: "$y$", 2: "CQI$_0$", 3: "CQI$_1$", 4: "CQI$_2$", 5: "throughput", 6: "serving cell"}' \
   -title 'UE$_0$'
