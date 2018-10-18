#! /bin/bash

set -e

usage()
{
    cat >>/dev/stderr<<'MSG'
trace-idle-latency.sh - Collect data for idlatest

This calls trace-cmd record to generate trace data for idlatest

== Options ==
    -h --help: Show this message.
    -s --sleep SLEEP_TIME: Duration of test (default 10)
MSG
}

parse_args()
{
    opt_sleep=10

    eval set -- $(getopt -n trace-idle-latency.sh \
        -o -hs: -l 'help,sleep:' \
        -- "$@")

    while [ $# -gt 0 ]; do
        case "$1" in
        -h|--help) usage; exit 1;;
        --sleep) opt_sleep=$2; shift;;
        *) opt_sleep=$1 ;;
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

main()
{
    parse_args "$@"

    # list events
    event_list=()
    if grep -q 'ipi:.*' /sys/kernel/debug/tracing/available_events; then
        event_list+=("ipi:*")
    fi
    if grep -q 'power:cpu_idle' /sys/kernel/debug/tracing/available_events; then
        event_list+=("power:cpu_idle")
    fi
    for item in $(grep timer:clock_event /sys/kernel/debug/tracing/available_events); do
        event_list+=($item)
    done
    trace_if_avail irq:irq_handler_entry
    trace_if_avail irq:irq_handler_exit

    cmd=(trace-cmd record)
    # Use monotonic clock, closest to ktime_get
    cmd+=(-C mono)
    for ev in "${event_list[@]}"; do
        cmd+=(-e "$ev")
    done
    cmd+=(sleep "$opt_sleep")
    exec "${cmd[@]}"
}

main "$@"
