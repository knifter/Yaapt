import queue
import struct
import threading
import time

import serial

from yaapt.constants import (
    YAAPT_MAGIC, YAAPT_SYNC_TIMEOUT, YAAPT_DEVICE_TIMEOUT, YAAPT_SERIAL_BAUD,
    CMD_DESC_REQUEST,
    FIELD_CHANNEL_DESC, FIELD_GROUP_START, FIELD_GROUP_END,
    FIELD_CHANNEL_ID, FIELD_CHANNEL_TYPE, FIELD_CHANNEL_NAME, FIELD_CHANNEL_N_VALUES,
    FIELD_LOG_LEVEL, FIELD_LOG_LINENR, FIELD_LOG_FILENAME, FIELD_LOG_FUNCTION, FIELD_LOG_MESSAGE,
    FIELD_VALUE_SIZES, FIELD_VALUE_FORMATS,
    CHANNEL_TYPE_LOG, CHANNEL_TYPE_PLOT_X, CHANNEL_TYPE_PLOT_T, CHANNEL_TYPE_PLOT_XY,
    LOG_LEVEL_NAMES,
)


class DeviceConnection:
    """
    Manages a serial connection to a Yaapt-enabled microcontroller.

    After calling start(), a background thread continuously reads and parses
    the binary protocol. Parsed messages are placed in an internal queue.
    Call poll() from the main/GUI thread to retrieve pending messages.

    Message format returned by poll():
        ('channel_desc', { 'id': int, 'type': int, 'name': str, 'n_values': int })
        ('log',  { 'channel_id': int, 'level': int, 'level_name': str,
                   'linenr': int, 'file': str, 'function': str, 'message': str })
        ('plot_x',  { 'channel_id': int, 'values': [float, ...] })
        ('plot_t',  { 'channel_id': int, 'timestamp': int, 'values': [float, ...] })
        ('plot_xy', { 'channel_id': int, 'x': float, 'y': float })
        ('raw',     { 'channel_id': int, 'payload': bytes })
        ('connected', { 'version': int })
        ('disconnected', {})
    """

    def __init__(self, port, baudrate=YAAPT_SERIAL_BAUD):
        self._serial = serial.Serial(port, baudrate,
                                     bytesize=8, parity='N', stopbits=1,
                                     timeout=YAAPT_SYNC_TIMEOUT / 2)
        self._channels = {}   # id -> channel info dict
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._reader_thread, daemon=True)
        self._running = False

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def start(self):
        self._running = True
        self._thread.start()

    def stop(self):
        self._running = False
        try:
            self._serial.close()
        except Exception:
            pass

    def device_reset(self):
        """Toggle DTR to reset an Arduino-style device."""
        self._serial.setDTR(False)
        time.sleep(0.1)
        self._serial.reset_input_buffer()
        self._serial.setDTR(True)

    def send_command(self, cmd):
        """
        Send a channel-0 command to the device.
        cmd: one of the CMD_* constants from yaapt.constants.
        Frame: <channel_id=0x00> <length=0x01 0x00> <cmd>.
        """
        try:
            self._serial.write(bytes([0x00, 0x01, 0x00, cmd]))
        except serial.SerialException:
            pass

    def poll(self):
        """
        Drain and return all pending parsed messages as a list.
        Call this periodically from the GUI thread (e.g. via QTimer).
        """
        msgs = []
        while True:
            try:
                msgs.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return msgs

    @property
    def port(self):
        return self._serial.port

    @property
    def channels(self):
        return dict(self._channels)

    # ------------------------------------------------------------------ #
    # Background reader thread                                             #
    # ------------------------------------------------------------------ #

    def _reader_thread(self):
        while self._running:
            if self._sync():
                self._read_messages()
        self._queue.put(('disconnected', {}))

    def _sync(self):
        """
        Synchronise with the device. Sends CMD_DESC_REQUEST once and accepts either:
          - YAAPT_MAGIC + version byte  (device just booted)
          - Channel-0 descriptor frame  (device already running, responding to request)
        On prolonged silence, emits 'no_device' and retries the request.
        Returns True when synced, False if stopped or serial error.
        """
        self.send_command(CMD_DESC_REQUEST)

        buf = bytearray()
        mlen = len(YAAPT_MAGIC)
        deadline = time.monotonic() + YAAPT_DEVICE_TIMEOUT

        while self._running:
            try:
                b = self._serial.read(1)
            except serial.SerialException:
                return False
            if not b:
                if time.monotonic() > deadline:
                    self._queue.put(('no_device', {}))
                    self.send_command(CMD_DESC_REQUEST)
                    deadline = time.monotonic() + YAAPT_DEVICE_TIMEOUT
                    buf.clear()
                continue
            deadline = time.monotonic() + YAAPT_DEVICE_TIMEOUT
            buf.append(b[0])

            # Style 1: device startup magic
            if bytes(buf[-mlen:]) == YAAPT_MAGIC:
                try:
                    self._serial.read(1)   # consume version byte
                except serial.SerialException:
                    return False
                self._queue.put(('connected', {}))
                return True

            # Style 2: channel-0 descriptor frame (CMD_DESC_REQUEST response, no magic)
            # Header pattern: 0x00 <len_lo> 0x00 <FIELD_CHANNEL_DESC>
            if (len(buf) >= 4
                    and buf[-4] == 0x00
                    and buf[-2] == 0x00
                    and buf[-1] == FIELD_CHANNEL_DESC):
                length = buf[-3]
                rest = self._read_exact(length - 1) if length > 1 else b''
                if rest is None:
                    return False
                self._parse_descriptors(bytes([FIELD_CHANNEL_DESC]) + rest)
                self._queue.put(('connected', {}))
                return True

            if len(buf) > mlen:
                del buf[:-mlen]

        return False

    def _request_descriptors(self):
        """Explicitly request channel descriptors (e.g. after reconnect or from GUI)."""
        self.send_command(CMD_DESC_REQUEST)

    def _read_exact(self, n):
        """
        Read exactly n bytes from the serial port.
        Resets the silence deadline each time data arrives.
        Returns bytes or None on silence-timeout / stop.
        """
        buf = bytearray()
        deadline = time.monotonic() + YAAPT_SYNC_TIMEOUT
        while len(buf) < n and self._running:
            try:
                chunk = self._serial.read(n - len(buf))
            except serial.SerialException:
                return None
            if chunk:
                buf += chunk
                deadline = time.monotonic() + YAAPT_SYNC_TIMEOUT
            elif time.monotonic() > deadline:
                return None  # silence timeout → trigger resync
        return bytes(buf) if len(buf) == n else None

    def _read_messages(self):
        """
        Read framed messages: <channel_id:u8> <length:u16le> <payload>
        Returns when a timeout (silence) or serial error occurs.
        """
        while self._running:
            try:
                id_byte = self._serial.read(1)
            except serial.SerialException:
                return
            if not id_byte:
                # Brief silence on the channel_id byte is acceptable — just wait.
                # Longer silence is handled inside _read_exact.
                continue

            channel_id = id_byte[0]

            len_bytes = self._read_exact(2)
            if len_bytes is None:
                return  # resync
            length = struct.unpack('<H', len_bytes)[0]

            payload = self._read_exact(length) if length > 0 else b''
            if payload is None:
                return  # resync

            self._dispatch(channel_id, payload)

    # ------------------------------------------------------------------ #
    # Dispatch & parsing                                                   #
    # ------------------------------------------------------------------ #

    def _dispatch(self, channel_id, payload):
        if channel_id == 0x00:
            self._parse_descriptors(payload)
        elif channel_id in self._channels:
            ch = self._channels[channel_id]
            ct = ch.get('type', 0)
            if   ct == CHANNEL_TYPE_LOG:     self._parse_log(channel_id, payload)
            elif ct == CHANNEL_TYPE_PLOT_X:  self._parse_plot_x(channel_id, payload)
            elif ct == CHANNEL_TYPE_PLOT_T:  self._parse_plot_t(channel_id, payload)
            elif ct == CHANNEL_TYPE_PLOT_XY: self._parse_plot_xy(channel_id, payload)
            else:
                self._queue.put(('raw', {'channel_id': channel_id, 'payload': payload}))

    def _parse_descriptors(self, payload):
        """
        Parse channel 0 descriptor payload.
        Each channel is wrapped in FIELD_CHANNEL_DESC { ... }.
        """
        i = 0
        while i < len(payload):
            if payload[i] != FIELD_CHANNEL_DESC:
                i += 1
                continue
            i += 1
            if i >= len(payload) or payload[i] != FIELD_GROUP_START:
                continue
            i += 1

            ch = {'n_values': 1}
            while i < len(payload) and payload[i] != FIELD_GROUP_END:
                tag = payload[i]; i += 1
                if i >= len(payload):
                    break
                if tag == FIELD_CHANNEL_ID:
                    ch['id'] = payload[i]; i += 1
                elif tag == FIELD_CHANNEL_TYPE:
                    ch['type'] = payload[i]; i += 1
                elif tag == FIELD_CHANNEL_NAME:
                    end = payload.find(0, i)
                    if end == -1:
                        break
                    ch['name'] = payload[i:end].decode('ascii', errors='replace')
                    i = end + 1
                elif tag == FIELD_CHANNEL_N_VALUES:
                    ch['n_values'] = payload[i]; i += 1

            if i < len(payload):
                i += 1  # skip FIELD_GROUP_END

            if 'id' in ch:
                self._channels[ch['id']] = ch
                self._queue.put(('channel_desc', dict(ch)))

    def _parse_log(self, channel_id, payload):
        """
        Parse log payload. Fields are tagged so optional ones can be absent:
          FIELD_LOG_LEVEL    <level:u8>
          FIELD_LOG_LINENR   <linenr:u32le>    (optional)
          FIELD_LOG_FILENAME <file:str\0>       (optional)
          FIELD_LOG_FUNCTION <function:str\0>   (optional)
          FIELD_LOG_MESSAGE  <message:str\0>
        """
        msg = {
            'channel_id': channel_id,
            'level': 0, 'level_name': '?',
            'linenr': 0, 'file': '', 'function': '', 'message': '',
        }
        i = 0
        try:
            while i < len(payload):
                tag = payload[i]; i += 1
                if tag == FIELD_LOG_LEVEL:
                    msg['level'] = payload[i]
                    msg['level_name'] = LOG_LEVEL_NAMES.get(payload[i], '?')
                    i += 1
                elif tag == FIELD_LOG_LINENR:
                    msg['linenr'] = struct.unpack_from('<I', payload, i)[0]; i += 4
                elif tag == FIELD_LOG_FILENAME:
                    end = payload.find(0, i)
                    if end == -1: break
                    msg['file'] = payload[i:end].decode('ascii', errors='replace'); i = end + 1
                elif tag == FIELD_LOG_FUNCTION:
                    end = payload.find(0, i)
                    if end == -1: break
                    msg['function'] = payload[i:end].decode('ascii', errors='replace'); i = end + 1
                elif tag == FIELD_LOG_MESSAGE:
                    end = payload.find(0, i)
                    end = end if end != -1 else len(payload)
                    msg['message'] = payload[i:end].decode('ascii', errors='replace'); i = end + 1
                else:
                    break  # unknown tag, stop
        except (struct.error, IndexError):
            pass
        self._queue.put(('log', msg))

    def _parse_typed_values(self, payload, offset=0):
        """
        Parse a sequence of <type_tag:u8> <value:N bytes> from payload[offset:].
        Returns a list of numeric values (all promoted to float for simplicity).
        """
        values = []
        i = offset
        while i < len(payload):
            tag = payload[i]; i += 1
            fmt = FIELD_VALUE_FORMATS.get(tag)
            size = FIELD_VALUE_SIZES.get(tag)
            if fmt is None or i + size > len(payload):
                break
            values.append(struct.unpack_from(fmt, payload, i)[0])
            i += size
        return values

    def _parse_plot_x(self, channel_id, payload):
        values = self._parse_typed_values(payload)
        if values:
            self._queue.put(('plot_x', {'channel_id': channel_id, 'values': values}))

    def _parse_plot_t(self, channel_id, payload):
        if len(payload) < 4:
            return
        timestamp = struct.unpack_from('<I', payload, 0)[0]
        values = self._parse_typed_values(payload, offset=4)
        if values is not None:
            self._queue.put(('plot_t', {'channel_id': channel_id,
                                        'timestamp': timestamp, 'values': values}))

    def _parse_plot_xy(self, channel_id, payload):
        values = self._parse_typed_values(payload)
        if len(values) >= 2:
            self._queue.put(('plot_xy', {'channel_id': channel_id,
                                         'x': values[0], 'y': values[1]}))
