#! /bin/bash

set -e
set -x

trace_if_avail()
{
    if grep -q "$1" /sys/kernel/debug/tracing/available_events; then
        event_list+=("$1")
    fi
}

main()
{
    opt_sleep="${1:-10}"

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
