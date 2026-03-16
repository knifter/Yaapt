"""
PC-side channel representations.

These are created automatically by YaaptApplication when the device sends its
channel descriptor on startup. Each channel class holds a ring buffer of
received data and exposes an update() method that the app calls with each
parsed message from DeviceConnection.poll().
"""

from collections import deque

from yaapt.constants import (
    CHANNEL_TYPE_LOG, CHANNEL_TYPE_PLOT_X, CHANNEL_TYPE_PLOT_T, CHANNEL_TYPE_PLOT_XY,
    CHANNEL_TYPE_DATA, CHANNEL_TYPE_TEXT,
)


def make_channel(desc):
    """
    Factory: create the right YaaptChannel subclass from a descriptor dict.
    desc keys: 'id', 'type', 'name', 'n_values'
    """
    ct = desc.get('type', 0)
    if   ct == CHANNEL_TYPE_LOG:     return LogChannel(desc)
    elif ct == CHANNEL_TYPE_PLOT_X:  return PlotXChannel(desc)
    elif ct == CHANNEL_TYPE_PLOT_T:  return PlotTChannel(desc)
    elif ct == CHANNEL_TYPE_PLOT_XY: return PlotXYChannel(desc)
    elif ct in (CHANNEL_TYPE_DATA, CHANNEL_TYPE_TEXT): return RawChannel(desc)
    else:
        return RawChannel(desc)


class YaaptChannel:
    """Base class for all PC-side channels."""

    def __init__(self, desc):
        self.channel_id = desc.get('id', 0)
        self.name       = desc.get('name', '?')
        self.type_code  = desc.get('type', 0)
        self.n_values   = desc.get('n_values', 1)

    def update(self, msg_type, msg):  # noqa: unused-arg — subclasses use both
        """Called by the app for every message belonging to this channel."""
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__} id={self.channel_id!r} name={self.name!r}>'


class LogChannel(YaaptChannel):
    """
    Accumulates log messages.
    Each entry is a dict: level, level_name, linenr, file, function, message.
    """
    MAX_ENTRIES = 2000

    def __init__(self, desc):
        super().__init__(desc)
        self.entries = deque(maxlen=self.MAX_ENTRIES)
        self._listeners = []

    def add_listener(self, fn):
        """fn(entry_dict) is called on every new log message."""
        self._listeners.append(fn)

    def update(self, msg_type, msg):
        if msg_type != 'log':
            return
        entry = {
            'level':      msg.get('level', 0),
            'level_name': msg.get('level_name', '?'),
            'linenr':     msg.get('linenr', 0),
            'file':       msg.get('file', ''),
            'function':   msg.get('function', ''),
            'message':    msg.get('message', ''),
        }
        self.entries.append(entry)
        for fn in self._listeners:
            fn(entry)


class PlotXChannel(YaaptChannel):
    """
    Plot channel: Y values with sequential index on X.
    Maintains one ring buffer per series (n_values series total).
    """
    DEFAULT_HISTORY = 500

    def __init__(self, desc, history=DEFAULT_HISTORY):
        super().__init__(desc)
        self.history = history
        # One deque per series
        self.series = [deque([0.0] * history, maxlen=history)
                       for _ in range(self.n_values)]
        self._listeners = []

    def add_listener(self, fn):
        """fn(series_index: list[deque]) called after every update."""
        self._listeners.append(fn)

    def update(self, msg_type, msg):
        if msg_type != 'plot_x':
            return
        values = msg.get('values', [])
        for i, v in enumerate(values):
            if i < len(self.series):
                self.series[i].append(v)
        for fn in self._listeners:
            fn(self.series)


class PlotTChannel(YaaptChannel):
    """
    Plot channel: Y values with micros() timestamp.
    Stores (timestamp_s, value) pairs per series.
    Timestamps are converted from uint32 micros to float seconds.
    Handles the 71-minute uint32 wraparound.
    """
    DEFAULT_HISTORY = 500

    def __init__(self, desc, history=DEFAULT_HISTORY):
        super().__init__(desc)
        self.history = history
        self.times  = deque(maxlen=history)   # float seconds (unwrapped)
        self.series = [deque(maxlen=history) for _ in range(self.n_values)]
        self._last_ts_raw = None
        self._ts_offset   = 0.0
        self._listeners   = []

    def add_listener(self, fn):
        self._listeners.append(fn)

    def update(self, msg_type, msg):
        if msg_type != 'plot_t':
            return
        ts_raw = msg.get('timestamp', 0)

        # Detect uint32 wraparound (~71 min at 1 µs resolution)
        if self._last_ts_raw is not None and ts_raw < self._last_ts_raw:
            self._ts_offset += (0xFFFFFFFF + 1) / 1e6
        self._last_ts_raw = ts_raw
        ts_s = self._ts_offset + ts_raw / 1e6

        self.times.append(ts_s)
        values = msg.get('values', [])
        for i, v in enumerate(values):
            if i < len(self.series):
                self.series[i].append(v)

        for fn in self._listeners:
            fn(self.times, self.series)


class PlotXYChannel(YaaptChannel):
    """
    Plot channel: explicit X-Y pairs (scatter / parametric plot).
    """
    DEFAULT_HISTORY = 200

    def __init__(self, desc, history=DEFAULT_HISTORY):
        super().__init__(desc)
        self.history = history
        self.xs = deque(maxlen=history)
        self.ys = deque(maxlen=history)
        self._listeners = []

    def add_listener(self, fn):
        self._listeners.append(fn)

    def update(self, msg_type, msg):
        if msg_type != 'plot_xy':
            return
        self.xs.append(msg.get('x', 0.0))
        self.ys.append(msg.get('y', 0.0))
        for fn in self._listeners:
            fn(self.xs, self.ys)


class RawChannel(YaaptChannel):
    """Fallback for unknown / data / text channel types."""

    def __init__(self, desc):
        super().__init__(desc)
        self.payloads = deque(maxlen=200)

    def update(self, msg_type, msg):  # noqa: unused-arg msg_type
        self.payloads.append(msg.get('payload', b''))
