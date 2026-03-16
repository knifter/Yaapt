"""
Yaapt protocol monitor — standalone example (no GUI).

Usage:
    python examples/monitor.py COM4
    python examples/monitor.py /dev/ttyUSB0

Prints connection status, discovered channels, and every incoming message
to stdout. Press Ctrl+C to quit.

Run from the Yaapt/ directory so the yaapt package is on sys.path.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from yaapt.device import DeviceConnection
from yaapt.constants import (
    CHANNEL_TYPE_LOG, CHANNEL_TYPE_PLOT_X, CHANNEL_TYPE_PLOT_T, CHANNEL_TYPE_PLOT_XY,
    CHANNEL_TYPE_DATA, CHANNEL_TYPE_TEXT,
    LOG_LEVEL_NAMES,
)

CHANNEL_TYPE_NAMES = {
    CHANNEL_TYPE_LOG:     'log',
    CHANNEL_TYPE_PLOT_X:  'plot-X',
    CHANNEL_TYPE_PLOT_T:  'plot-T',
    CHANNEL_TYPE_PLOT_XY: 'plot-XY',
    CHANNEL_TYPE_DATA:    'data',
    CHANNEL_TYPE_TEXT:    'text',
}

POLL_INTERVAL = 0.02   # seconds between poll() calls


def fmt_channel_id(ch_id):
    """Show channel id as both its ASCII character and hex value."""
    c = chr(ch_id) if 0x20 <= ch_id <= 0x7e else '?'
    return f"'{c}' (0x{ch_id:02x})"


def main():
    if len(sys.argv) < 2:
        print(f'Usage: python {sys.argv[0]} <port>')
        print('Example: python examples/monitor.py COM4')
        sys.exit(1)

    port = sys.argv[1]
    print(f'Opening {port} …')

    dev = DeviceConnection(port)
    dev.start()

    channels = {}   # id -> descriptor dict

    try:
        while True:
            for msg_type, msg in dev.poll():

                if msg_type == 'connected':
                    print(f'\r[+] Connected          ')

                elif msg_type == 'no_device':
                    print('\r[?] No Yaapt device — retrying…', end='', flush=True)

                elif msg_type == 'disconnected':
                    print('\n[-] Disconnected. Waiting for device …')
                    channels.clear()

                elif msg_type == 'channel_desc':
                    ch_id  = msg['id']
                    ct     = msg.get('type', 0)
                    name   = msg.get('name', '?')
                    n      = msg.get('n_values', 1)
                    tname  = CHANNEL_TYPE_NAMES.get(ct, f'0x{ct:02x}')
                    channels[ch_id] = msg
                    print(f'  [channel] {fmt_channel_id(ch_id)}'
                          f'  type={tname!r}  name={name!r}'
                          + (f'  n_values={n}' if ct in (CHANNEL_TYPE_PLOT_X,
                                                          CHANNEL_TYPE_PLOT_T,
                                                          CHANNEL_TYPE_PLOT_XY) else ''))

                elif msg_type == 'log':
                    ch_id = msg['channel_id']
                    lvl   = msg.get('level_name', '?')
                    loc   = ''
                    if msg.get('file'):
                        loc = f'{msg["file"]}:{msg["linenr"]} {msg["function"]}()  '
                    print(f'  [log/{lvl}] ch={fmt_channel_id(ch_id)}  {loc}{msg["message"]}')

                elif msg_type == 'plot_x':
                    ch_id = msg['channel_id']
                    vals  = '  '.join(f'{v: .4f}' for v in msg['values'])
                    name  = channels.get(ch_id, {}).get('name', '?')
                    print(f'  [plot-X]  ch={fmt_channel_id(ch_id)} ({name!r})  {vals}')

                elif msg_type == 'plot_t':
                    ch_id = msg['channel_id']
                    ts    = msg['timestamp'] / 1e6
                    vals  = '  '.join(f'{v: .4f}' for v in msg['values'])
                    name  = channels.get(ch_id, {}).get('name', '?')
                    print(f'  [plot-T]  ch={fmt_channel_id(ch_id)} ({name!r})'
                          f'  t={ts:.4f}s  {vals}')

                elif msg_type == 'plot_xy':
                    ch_id = msg['channel_id']
                    name  = channels.get(ch_id, {}).get('name', '?')
                    print(f'  [plot-XY] ch={fmt_channel_id(ch_id)} ({name!r})'
                          f'  x={msg["x"]:.4f}  y={msg["y"]:.4f}')

                elif msg_type == 'raw':
                    ch_id = msg['channel_id']
                    data  = msg['payload']
                    print(f'  [raw]     ch={fmt_channel_id(ch_id)}'
                          f'  {len(data)} bytes: {data[:16].hex()} …')

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        dev.stop()


if __name__ == '__main__':
    main()
