#! /bin/bash

# SPDX-License-Identifier: MIT

set -e

usage()
{
    cat >>/dev/stderr<<'MSG'
trace-idle-latency.sh - Collect data for idlatest

This calls trace-cmd record to generate trace data for idlatest

== Options ==
    -h --help: Show this message.
    -s --sleep SLEEP_TIME: Duration of test (default 10)

    --no-dummy-load: Just run a single sleep under trace-cmd
    --dummy-load: Run a dummy load (default)
        The dummy load runs many small sleeps on all cpus. This ensures that
        all cpus enter and exit idle many times and provides lots of data.
MSG
}

die()
{
    echo "$@" >&2
    exit 1
}

parse_args()
{
    orig_argv=("$@")

    opt_sleep=10
    opt_mode=record
    opt_use_load=1

    eval set -- $(getopt -n trace-idle-latency.sh \
        -o -hs: -l 'help,sleep:,mode:,dummy-load,no-dummy-load,' \
        -- "$@")

    while [ $# -gt 0 ]; do
        case "$1" in
        -h|--help) usage; exit 1;;
        -s|--sleep) opt_sleep=$2; shift;;
        --mode) opt_mode=$2; shift;;
        --dummy-load) opt_use_load=1 ;;
        --no-dummy-load) opt_use_load=0 ;;
        --) break ;;
        *) opt_sleep=$1;;
        esac
        shift
    done
}

trace_if_avail()
{
    if grep -q "$1" /sys/kernel/debug/tracing/available_events; then
        event_list+=("$1")
    fi
}

main_load_worker()
{
    set +x
    while true; do
        sleep 0.2
    done
}

main_load_master()
{
    ncpus=$(grep processor /proc/cpuinfo | wc -l)
    worker_pids=()
    for cpu in `seq 0 $((ncpus - 1))`; do
        taskset -c $cpu "$0" "${orig_argv[@]}" --mode load-worker &
        worker_pids+=($!)
    done
    sleep $opt_sleep
    kill ${worker_pids[@]}
}

main()
{
    parse_args "$@"

    if [[ $opt_mode == load-master ]]; then
        main_load_master
    elif [[ $opt_mode == load-worker ]]; then
        main_load_worker
    elif [[ $opt_mode == record ]]; then
        main_record
    else
        die "Unknown mode $opt_mode"
    fi
}

main_record()
{
    # list events
    event_list=()
    if grep -q 'ipi:.*' /sys/kernel/debug/tracing/available_events; then
        event_list+=("ipi:*")
    fi
    trace_if_avail power:cpu_idle
    trace_if_avail timer:clock_event*
    trace_if_avail irq:irq_handler_entry
    trace_if_avail irq:irq_handler_exit

    cmd=(trace-cmd record)
    # Use monotonic clock, closest to ktime_get
    cmd+=(-C mono)
    for ev in "${event_list[@]}"; do
        cmd+=(-e "$ev")
    done
    if [[ $opt_use_load ]]; then
        cmd+=("$0" "${orig_argv[@]}" --mode load-master)
    else
        cmd+=(sleep "$opt_sleep")
    fi
    echo "RUN ${cmd[@]}" >&2
    exec "${cmd[@]}"
}

main "$@"
