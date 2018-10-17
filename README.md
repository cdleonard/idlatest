# Idle Latency Estimator

This tool attempts to estimate linux CPU idle wakeup latency based on
tracepoints.

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

Feel free to contact with questions or git send-email patches.
