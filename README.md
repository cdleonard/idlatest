# Idle Lantency Estimator

This tool attempts to estimate linux CPU idle wakeup latency based on
tracepoints.

## Python requirements

* numpy
* matplotlib
* pandas
* jupyter-notebook

These should be installable with apt-get or pip

## Kernel requirements

Following config options are required:

* CONFIG_FTRACE=y
* CONFIG_TRACER_SNAPSHOT=y
* CONFIG_ENABLE_DEFAULT_TRACERS=y

Tracepoints for clock_event_device are out-of-tree.

Tracepoints for ipi_raise/ipi_enter/ipi_exit are only available on arm and
arm64.

## How to run

* Copy trace-idle-latency.sh to the target system and run it
* Copy trace.dat back next to idlatest.ipynb
* Run the notebook

## Author

Leonard Crestez <leonard.crestez@nxp.com>
