# SPDX-License-Identifier: MIT

import re
import subprocess
import pandas
import numpy
from logging import getLogger
logger = getLogger(__name__)

RE_TRACEPOINT = re.compile(
        '\s+(?P<comm>.*)-(?P<pid>[0-9]+)\s+'
        '\[(?P<cpu>[0-9]+)\]\s+(?P<timestamp>[0-9.]+): '
        '(?P<tracepoint>[a-z_0-9]+): (?P<traceprint>.*)$')
RE_TRACEPOINT_DUMP = re.compile(
        '(?P<comm>.*)-(?P<pid>[0-9]+)\s+'
        '(?P<cpu>[0-9])\s+(?P<timestamp>[0-9]+us) : '
        '(?P<tracepoint>[a-z_0-9]+): (?P<traceprint>.*)$')

def match_tracepoint(line):
    m = RE_TRACEPOINT.match(line)
    if m:
        return m
    m = RE_TRACEPOINT_DUMP.match(line)
    if m:
        return m
    return None

def get_tracepoint_timestamp_sec(m):
    tsstr = m.group('timestamp')
    if tsstr.endswith('us'):
        return int(tsstr[:-2]) / 1000000.0
    elif '.' in tsstr:
        # Assume float values are seconds
        return float(tsstr)
    else:
        # Assume int values are nanoseconds
        return float(tsstr) / 1000000000.0

RE_TRACEPRINT_CPUIDLE = re.compile('state=(?P<state>[0-9]+) cpu_id=(?P<cpu_id>[0-9]+)')
def parse_traceprint_cpu_idle(traceprint):
    m = RE_TRACEPRINT_CPUIDLE.match(traceprint)
    if not m:
        logger.warning("Failed to parse cpuidle traceprint %r", traceprint)
        return None
    r = m.groupdict()
    if r['state'] == '4294967295':
        r['state'] = -1
    else:
        r['state'] = int(r['state'])
    r['cpu_id'] = int(r['cpu_id'])
    return r

RE_TRACEPRINT_IPI_RAISE = re.compile('target_mask=(?P<target_mask>[0-9a-f,]+) \((?P<ipi_name>[a-zA-Z ]+)\)')
RE_TRACEPRINT_IPI_ENTER = re.compile('\((?P<ipi_name>[a-zA-Z ]+)\)')
RE_TRACEPRINT_IPI_EXIT = re.compile('\((?P<ipi_name>[a-zA-Z ]+)\)')
def parse_traceprint_ipi_raise(traceprint):
    m = RE_TRACEPRINT_IPI_RAISE.match(traceprint)
    if not m:
        return None
    r = m.groupdict()
    r['target_mask'] = int(r['target_mask'].replace(',', ''), 16)
    return r

def parse_traceprint_ipi_enter(traceprint):
    m = RE_TRACEPRINT_IPI_ENTER.match(traceprint)
    return m.groupdict() if m else None

def parse_traceprint_ipi_exit(traceprint):
    m = RE_TRACEPRINT_IPI_EXIT.match(traceprint)
    return m.groupdict() if m else None

RE_TRACEPRINT_CLOCK_EVENT = re.compile('clock_event_device=(?P<cedptr>0x[0-9a-f]+) time=(?P<event_time>[0-9]+)')
def parse_traceprint_clock_event(traceprint):
    m = RE_TRACEPRINT_CLOCK_EVENT.match(traceprint)
    if not m:
        return None
    r = m.groupdict()
    # To seconds:
    r['event_time'] = float(r['event_time']) / 1000000000.0
    return r

RE_TRACEPRINT_IRQ_HANDLER_ENTRY = re.compile('irq=(?P<irq>[0-9]+) name=(?P<name>.*)')
def parse_traceprint_irq_handler_entry(traceprint):
    m = RE_TRACEPRINT_IRQ_HANDLER_ENTRY.match(traceprint)
    if not m:
        return None
    r = m.groupdict()
    r['irq'] = int(r['irq'])
    return r

def trace_cmd_report(arg='trace.dat'):
    cmd = ['trace-cmd', 'report']
    cmd += ['-t']
    cmd += [arg]
    p = subprocess.Popen(cmd,
            universal_newlines=True,
            stdout=subprocess.PIPE)
    for line in p.stdout.readlines():
        m = match_tracepoint(line)
        if not m:
           logger.warning("unmatched line %r", line)
           continue

        item = m.groupdict()
        item['cpu'] = int(item['cpu'])
        item['timestamp'] = get_tracepoint_timestamp_sec(m)

        # per-tracepoint handling:
        tracepoint = m.group('tracepoint')
        traceprint = m.group('traceprint').strip()
        if tracepoint in ['cpu_idle', 'cpu_idle_exit']:
            extra = parse_traceprint_cpu_idle(traceprint)
        elif tracepoint == 'ipi_raise':
            extra = parse_traceprint_ipi_raise(traceprint)
        elif tracepoint == 'ipi_enter':
            extra = parse_traceprint_ipi_enter(traceprint)
        elif tracepoint == 'ipi_exit':
            extra = parse_traceprint_ipi_exit(traceprint)
        elif tracepoint == 'irq_handler_entry':
            extra = parse_traceprint_irq_handler_entry(traceprint)
        elif tracepoint.startswith('clock_event'):
            extra = parse_traceprint_clock_event(traceprint)
        else:
            extra = None

        if extra:
            item.update(**extra)
        yield item

def iter_set_bits(arg):
    for i in range(0, arg.bit_length()):
        if (arg & (1 << i)) != 0:
            yield i

class IdleLatencyEstimator:
    class CpuState:
        idle_state = None

    def __init__(self):
        self.reset()

    def reset(self):
        self.cpu_data_dict = {}

        self.df = pandas.DataFrame()
        self.df['cpu'] = pandas.Series(dtype=int)
        self.df['state'] = pandas.Series(dtype=int)
        self.df['state_attempt'] = pandas.Series(dtype=int)
        self.df['wake_src'] = pandas.Series(dtype=str)
        self.df['enter_ts'] = pandas.Series(dtype=numpy.float64)
        self.df['wake_ts'] = pandas.Series(dtype=numpy.float64)
        self.df['exit_ts'] = pandas.Series(dtype=numpy.float64)

    def on_wake_event(self, cpu_data, ts, source):
        if cpu_data.idle_state is None:
            # not idling
            return
        if (ts < cpu_data.idle_enter_ts or
                (cpu_data.idle_exit_ts and ts > cpu_data.idle_exit_ts)):
            # out of range
            return
        if cpu_data.idle_wake_ts is None or cpu_data.idle_wake_ts > ts:
            # first known possible wakeup event
            cpu_data.idle_wake_ts = ts
            cpu_data.idle_wake_src = source

    def get_cpu_data(self, cpu):
        return self.cpu_data_dict.setdefault(cpu,
                IdleLatencyEstimator.CpuState())

    def flush(self, cpu, cpu_data):
        if cpu_data.idle_state is None:
            return
        def numconv(arg):
            if arg is None:
                return numpy.nan
            else:
                return arg
        kw = dict(
                cpu=cpu,
                state=cpu_data.idle_state,
                state_attempt=cpu_data.idle_state_attempt,

                enter_ts=numconv(cpu_data.idle_enter_ts),
                wake_ts=numconv(cpu_data.idle_wake_ts),
                exit_ts=numconv(cpu_data.idle_exit_ts),

                wake_src=cpu_data.idle_wake_src,
        )
        #logger.debug("flush {!r}".format(kw))
        self.df = self.df.append(kw, ignore_index=True)
        cpu_data.idle_state = None

    def handle_event(self, item):
        """Handle events (to be called in order)"""
        tracepoint = item['tracepoint']
        ts = item['timestamp']
        cpu = item['cpu']
        cpu_data = self.get_cpu_data(cpu)

        if tracepoint == 'cpu_idle':
            if item['state'] >= 0:
                cpu_data.idle_state = item['state']
                cpu_data.idle_state_attempt = cpu_data.idle_state
                cpu_data.idle_enter_ts = ts
                cpu_data.idle_wake_ts = None
                cpu_data.idle_wake_src = ''
                cpu_data.idle_exit_ts = None
            elif item['state'] < 0:
                cpu_data.idle_exit_ts = ts

        elif tracepoint == 'cpu_idle_exit':
            # Optionally determine the real state!

            item_state = item['state']
            if item_state < 0:
                # No idle state was actually entered, cpuidle driver returned error
                cpu_data.idle_state = None
            elif cpu_data.idle_state is not None:
                # Note the real state that was entered.
                cpu_data.idle_state = item['state']

        elif tracepoint == 'ipi_raise':
            for target_cpu in iter_set_bits(item['target_mask']):
                self.on_wake_event(self.get_cpu_data(target_cpu), ts, 'ipi')
        elif tracepoint == 'ipi_enter':
            self.on_wake_event(cpu_data, ts, 'ipi')
        elif tracepoint == 'ipi_exit':
            self.flush(cpu, cpu_data)
        elif tracepoint == 'irq_handler_entry':
            self.on_wake_event(cpu_data, ts, 'irq_%s_%s' % (
                    item['irq'], item['name']))
        elif tracepoint == 'irq_handler_exit':
            self.flush(cpu, cpu_data)
        elif tracepoint.startswith('clock_event_handle'):
            self.on_wake_event(cpu_data, item['event_time'], tracepoint)
        else:
            #logger.debug("ignore tracepoint %s %r", tracepoint, item)
            pass

    def main(self, trace):
        allev = []
        for item in trace_cmd_report(trace):
            allev.append(item)        
        allev = list(sorted(allev, key = lambda item: item['timestamp']))
        for ev in allev:
            self.handle_event(ev)
        return self

def estimate_idle_latency(trace):
    est = IdleLatencyEstimator()
    est.main(trace)
    df = est.df

    assert(df['exit_ts'].dtype == numpy.float64)
    assert(df['cpu'].dtype == numpy.int64)
    assert(df['state'].dtype == numpy.int64)

    return df
