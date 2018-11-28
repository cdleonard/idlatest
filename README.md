# Idle Latency Estimator

This tool attempts to estimate linux CPU idle wakeup latency based on
tracepoints. It can be used to measure cpuidle_state.exit_latency in a CPU and
SOC-independent way using the tracepoint infrastructure offered by linux.

It does not require hardware instrumentation of the target system (such as
probing voltages) and can be combined with arbitrary workloads.

This tool analyzes tracepoint data and reports a histogram of observed wakeup
latencies. The real exit_latency values are noticeable as "spikes" in the data.

## General approach

The exit_latency is defined as the interval between when a wakeup signal is
received and when the CPU can start executing code again. This is done by
examining all power:cpu_idle exit events and attempting to find the wakeup
source and a timestamp for it.

Wakeup sources do not generally have timestamps attached, but some do. In
particular:
 * IPIs are sent by software running on another core and timestamp is
automatically associated to the ipi:ipi_raise event. This is currently only
available on arm/arm64.
 * When the kernel goes to sleep it arms timers through a generic
clock_event_device.set_next_event callback which takes wakeup time as a
parameter. A tracepoint can be added for this.

In theory timestamps from various peripherals could be used (for example PTP)
but luckly IPIs and clock_events are very common.

### Limitations

Wakeups that come from sources without timestamps will confound the data.

#### Coupled states

It is common for idle states to be "coupled" and multiple CPUs, this is generally
implemented by having all cpus in a cluster enter a shallow state and only
moving to the deep state with the last CPU.

Drivers for cpuidle can report this (the return value from enter func) however:
 * This result value is not exposed via tracepoints
 * Many SOC-specific drivers don't do this (it's hard)
 * The generic ARM PSCI driver can't do this (PSCI limitation)

In practice this means the latency histogram for deeper states will include
values for shallower states.

## Python requirements

* numpy
* pandas
* matplotlib
* jupyter notebook

These can be installed in many ways.

#### Installing with debian packages for python2:

```
# apt-get install python-matplotlib python-pandas python-notebook
$ python2 -m notebook --notebook-dir "CHECKOUT_DIR"
```

#### Installing with debian packages for python3:

```
# apt install python3-pandas python3-matplotlib jupyter-notebook
$ jupyter-notebook --notebook-dir "CHECKOUT_DIR"
```

#### Installing with pip

Using pip instead of distro packages should be very portable.

Running inside a virtualenv avoid contaminating your environment:
```
# apt-get install virtualenv
$ virtualenv venv
$ . ./venv/bin/activate
$ pip install notebook pandas matplotlib
$ jupyter-notebook --notebook-dir "CHECKOUT_DIR"
```

## Kernel requirements

Following config options are required:

* CONFIG_FTRACE=y
* CONFIG_TRACER_SNAPSHOT=y
* CONFIG_ENABLE_DEFAULT_TRACERS=y

Tracepoints for clock_event_device are out-of-tree, you need this patch:

https://bitbucket.sw.nxp.com/users/nxf25340/repos/linux-imx/commits/3f9c1254a197679d6e2675a611be758e1e0e13dc

Tracepoints for ipi_raise/ipi_enter/ipi_exit are only available on arm and
arm64.

## How to run

* Copy trace-idle-latency.sh to the target system and run it
* Copy trace.dat back next to idlatest.ipynb
* Run the notebook
    * Start jupyter-notebook
    * Go to http://localhost:8888/notebooks/idlatest.ipynb
    * Kernel -> Restart & Run All

Both the host system (running the notebook) and the target need to have
`trace-cmd` installed. The trace.dat format is mostly compatible so default
versions from debian/ubuntu or yocto should work fine.

## Author

[Leonard Crestez](mailto:leonard.crestez@nxp.com)

Feel free to contact with questions or `git send-email` patches.
