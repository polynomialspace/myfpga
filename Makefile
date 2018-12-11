export PYTHONPATH = /home/ncl/git/migen/migen
all:
	python3 top.py
flash:
	python3 flash.py
prog:
	python3 flash.py
sim:
	python3 sim.py
clean:
	rm -rf build/ __pycache__/ *.vcd
