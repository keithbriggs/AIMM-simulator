AIMM 5G system simulator
------------------------

The AIMM simulator emulates a cellular radio system roughly following 5G concepts and channel models.  The intention is to have an easy-to-use and fast system written in pure Python with minimal dependencies. It is especially designed to be suitable for interfacing to AI engines such as ``tensorflow`` or ``pytorch``, and it is not a principal aim for it to be extremely accurate at the level of the radio channel.  The simulator was developed for the AIMM project (<https://aimm.celticnext.eu>) by Keith Briggs (<https://keithbriggs.info>).

The full documentation is at <https://aimm-simulator.readthedocs.io/en/latest/>.

Software dependencies
---------------------

1. Python 3.8 or higher <https://python.org>.
2. NumPy <https://numpy.org/>. 
3. Simpy <https://pypi.org/project/simpy/>.
4. If real-time plotting is needed, matplotlib <https://matplotlib.org>.

Installation
------------

Three ways are possible:

* The simplest way, direct from PyPI: ``pip install AIMM-simulator``. This will not always get the latest version.

* Download the wheel, typically ``dist/aimm_simulator-2.x.y-py3-none-any.whl`` from github, and run ``pip install <wheel>``.

* Alternatively, the package can be installed by downloading the complete repository (using the green ``<> Code ⌄`` button) as a zip, unpacking it, and then doing ``make install_local`` from inside the unpacked zip. 

After installation, run a test with ``python3 examples/basic_test.py``.


Simulator block diagram
-----------------------

The diagram below (not visible on pypi.org) shows the main classes in the code and the relationships between them. 

![AIMM Simulator block diagram](https://github.com/keithbriggs/AIMM-simulator/blob/main/doc/sphinx_source/AIMM_Simulator_block_diagram.png)

