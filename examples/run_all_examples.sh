#!/bin/bash
# Keith Briggs 2022-11-14

PLOTTER="./src/realtime_plotter.py"

# do-nothing example - no output expected...
python3 examples/AIMM_simulator_example_n0.py
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n0.py failed with exit code $? - quitting!"
  exit 1
fi

# Tutorial example 1...
python3 examples/AIMM_simulator_example_n1.py
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n1.py failed - quitting!"
  exit 1
fi

# Tutorial example 2...
python3 examples/AIMM_simulator_example_n2.py
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n2.py failed - quitting!"
  exit 1
fi

# Tutorial example 3...
python3 examples/AIMM_simulator_example_n3.py
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n3.py failed - quitting!"
  exit 1
fi

# Tutorial example 3a...
python3 examples/AIMM_simulator_example_n3a.py
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n3a.py failed - quitting!"
  exit 1
fi

# Tutorial example 4...
python3 examples/AIMM_simulator_example_n4.py
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n4.py failed - quitting!"
  exit 1
fi

# Tutorial example 5...
(time python3 examples/AIMM_simulator_example_n5.py | "${PLOTTER}" -nplots=3 -tmax=500 -ylims='{0: (-100,100), 1: (-100,100), 2: (0,30)}' -ylabels='{0: "UE[0] $x$", 1: "UE[0] $y$", 2: "UE[0] throughput"}' -fnb='examples/img/AIMM_simulator_example_n5' -author='Keith Briggs')
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n5.py failed - quitting!"
  exit 1
fi

# Tutorial example 6...
(time python3 examples/AIMM_simulator_example_n6.py | "${PLOTTER}" -nplots=1 -tmax=100 -ylims='[(0,1),]' -ylabels='{0: "average downlink throughput over all UEs"}' -fnb='examples/img/AIMM_simulator_example_n6' -author='Keith Briggs')
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n6.py failed - quitting!"
  exit 1
fi

# Tutorial example 7...
(python3 examples/AIMM_simulator_example_n7.py | "${PLOTTER}" -nplots=4 -tmax=2000 -ylims='{0: (0,10), 1: (0,1000), 2: (0,1000), 3: (0,30)}' -ylabels='{0: "UE[0] throughput", 1: "UE[0] $x$", 2: "UE[0] $y$", 3: "UE[0] serving cell"}' -fnb='examples/img/AIMM_simulator_example_n7' -author='Keith Briggs')
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n7.py failed - quitting!"
  exit 1
fi

# Tutorial example 8...
python3 examples/AIMM_simulator_example_n8.py
if [ $? -ne 0 ]
then
  echo "AIMM_simulator_example_n8.py failed - quitting!"
  exit 1
fi

#bash run_RIC_example.sh
