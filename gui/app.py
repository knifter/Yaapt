"""
YaaptApplication: main GUI application.

Architecture:
  - A QTimer fires every ~16 ms to call device.poll() and dispatch messages.
  - When a 'channel_desc' message arrives, the appropriate dock is created.
  - When data messages arrive, the corresponding channel object is updated,
    which in turn notifies its dock via a listener callback.
  - Window layout is saved/restored via QSettings.
  - Connection is managed via the toolbar port-selector + connect button.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock
from PyQt6 import QtWidgets, QtCore, QtGui
from serial.tools import list_ports

from yaapt.channels import make_channel, LogChannel, PlotXChannel, PlotTChannel, PlotXYChannel
from yaapt.constants import CHANNEL_TYPE_LOG, CHANNEL_TYPE_PLOT_X, CHANNEL_TYPE_PLOT_T, CHANNEL_TYPE_PLOT_XY
from yaapt.device import DeviceConnection


pg.setConfigOptions(antialias=True)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

SETTINGS_ORG       = 'Yaapt'
SETTINGS_APP       = 'Yaapt'
SETTINGS_STATE_KEY = 'dockstate'
SETTINGS_GEOM_KEY  = 'geometry'
SETTINGS_PORT_KEY  = 'last_port'


class _PortComboBox(QtWidgets.QComboBox):
    """Port combo that refreshes the port list every time the dropdown is opened."""

    def showPopup(self):
        current = self.currentText()
        self.clear()
        for info in sorted(list_ports.comports(), key=lambda p: p.device):
            label = info.device
            if info.description and info.description != 'n/a':
                label += f'  —  {info.description}'
            self.addItem(label, userData=info.device)
        # Restore previously selected port
        for i in range(self.count()):
            if self.itemData(i) == current or self.itemText(i).startswith(current):
                self.setCurrentIndex(i)
                break
        super().showPopup()

    def current_port(self):
        """Return the raw device name of the selected item (e.g. 'COM4')."""
        data = self.currentData()
        return data if data else self.currentText().split()[0] if self.currentText() else ''


class YaaptApplication:
    """
    Creates the main window with toolbar + menubar, manages the device
    connection and auto-creates docks from channel descriptors.
    Call exec() to enter the Qt event loop.
    """

    def __init__(self):
        self._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        self._settings = QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)

        self._win = QtWidgets.QMainWindow()
        self._win.setWindowTitle('Yaapt')
        self._area = DockArea()
        self._win.setCentralWidget(self._area)

        geom = self._settings.value(SETTINGS_GEOM_KEY)
        if geom:
            self._win.restoreGeometry(geom)
        else:
            self._win.resize(1200, 800)

        self._device   = None
        self._channels = {}   # channel_id -> YaaptChannel
        self._docks    = {}   # channel_id -> Dock

        self._status_bar = self._win.statusBar()
        self._status_bar.showMessage('Not connected.')

        self._setup_menubar()
        self._setup_toolbar()

        # Single always-running poll timer; _poll() no-ops when no device.
        self._timer = QtCore.QTimer()
        self._timer.setInterval(16)   # ~60 fps
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    # ------------------------------------------------------------------ #
    # Menubar                                                              #
    # ------------------------------------------------------------------ #

    def _setup_menubar(self):
        mb = self._win.menuBar()

        file_menu = mb.addMenu('&File')

        self._act_connect    = QtGui.QAction('&Connect',    self._win)
        self._act_disconnect = QtGui.QAction('&Disconnect', self._win)
        self._act_disconnect.setEnabled(False)

        self._act_connect.triggered.connect(self._connect)
        self._act_disconnect.triggered.connect(self._disconnect)

        file_menu.addAction(self._act_connect)
        file_menu.addAction(self._act_disconnect)
        file_menu.addSeparator()

        act_exit = QtGui.QAction('E&xit', self._win)
        act_exit.triggered.connect(self._win.close)
        file_menu.addAction(act_exit)

    # ------------------------------------------------------------------ #
    # Toolbar                                                              #
    # ------------------------------------------------------------------ #

    def _setup_toolbar(self):
        tb = self._win.addToolBar('Connection')
        tb.setMovable(False)
        tb.setFloatable(False)

        tb.addWidget(QtWidgets.QLabel(' Port: '))

        self._port_combo = _PortComboBox()
        self._port_combo.setMinimumWidth(180)
        self._port_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        # Pre-populate
        last = self._settings.value(SETTINGS_PORT_KEY, '')
        for info in sorted(list_ports.comports(), key=lambda p: p.device):
            label = info.device
            if info.description and info.description != 'n/a':
                label += f'  —  {info.description}'
            self._port_combo.addItem(label, userData=info.device)
            if info.device == last:
                self._port_combo.setCurrentIndex(self._port_combo.count() - 1)
        tb.addWidget(self._port_combo)

        tb.addSeparator()

        self._connect_btn = QtWidgets.QPushButton('Connect')
        self._connect_btn.setCheckable(True)
        self._connect_btn.setMinimumWidth(100)
        self._connect_btn.clicked.connect(self._on_connect_btn)
        tb.addWidget(self._connect_btn)

    # ------------------------------------------------------------------ #
    # Connection management                                                #
    # ------------------------------------------------------------------ #

    def _on_connect_btn(self, checked):
        if checked:
            self._connect()
        else:
            self._disconnect()

    def _connect(self):
        port = self._port_combo.current_port()
        if not port:
            self._status_bar.showMessage('No port selected.')
            self._connect_btn.setChecked(False)
            return
        try:
            dev = DeviceConnection(port)
            dev.start()
            self._attach_device(dev)
        except Exception as e:
            self._status_bar.showMessage(f'Failed to open {port}: {e}')
            self._connect_btn.setChecked(False)

    def _disconnect(self):
        if self._device:
            self._device.stop()
        self._device = None
        self._set_connected_state(False)

    def _attach_device(self, device):
        """Attach a running DeviceConnection and update UI state."""
        self._device = device
        port = getattr(device, 'port', '?')
        self._settings.setValue(SETTINGS_PORT_KEY, port)
        self._set_connected_state(True)
        self._status_bar.showMessage(f'Connecting to {port}…')

    def _set_connected_state(self, connected: bool):
        self._connect_btn.setChecked(connected)
        self._connect_btn.setText('Disconnect' if connected else 'Connect')
        self._connect_btn.setStyleSheet(
            'color: #c00000; font-weight: bold;' if connected else '')
        self._port_combo.setEnabled(not connected)
        self._act_connect.setEnabled(not connected)
        self._act_disconnect.setEnabled(connected)
        if not connected:
            self._status_bar.showMessage('Not connected.')

    # ------------------------------------------------------------------ #
    # Poll loop                                                            #
    # ------------------------------------------------------------------ #

    def _poll(self):
        if self._device is None:
            return
        for msg_type, msg in self._device.poll():
            if msg_type == 'connected':
                port = getattr(self._device, 'port', '?')
                self._status_bar.showMessage(f'Connected — {port}')
            elif msg_type == 'disconnected':
                self._device = None
                self._set_connected_state(False)
            elif msg_type == 'no_device':
                port = getattr(self._device, 'port', '?')
                self._status_bar.showMessage(
                    f'No Yaapt device on {port} — retrying…')
            elif msg_type == 'channel_desc':
                self._on_channel_desc(msg)
            else:
                ch_id = msg.get('channel_id')
                if ch_id in self._channels:
                    self._channels[ch_id].update(msg_type, msg)

    # ------------------------------------------------------------------ #
    # Auto-dock creation                                                   #
    # ------------------------------------------------------------------ #

    def _on_channel_desc(self, desc):
        ch_id = desc.get('id')
        if ch_id is None or ch_id in self._channels:
            return

        ch = make_channel(desc)
        self._channels[ch_id] = ch

        ct = desc.get('type', 0)
        if   ct == CHANNEL_TYPE_LOG:     dock = self._make_log_dock(ch)
        elif ct == CHANNEL_TYPE_PLOT_X:  dock = self._make_plot_x_dock(ch)
        elif ct == CHANNEL_TYPE_PLOT_T:  dock = self._make_plot_t_dock(ch)
        elif ct == CHANNEL_TYPE_PLOT_XY: dock = self._make_plot_xy_dock(ch)
        else:
            return

        self._docks[ch_id] = dock
        self._area.addDock(dock, 'bottom')

        # Try to restore saved layout positions.
        saved_state = self._settings.value(SETTINGS_STATE_KEY)
        if saved_state:
            try:
                self._area.restoreState(saved_state)
            except Exception:
                pass

    # ---- Log dock ----

    def _make_log_dock(self, ch: LogChannel):
        dock = Dock(ch.name, size=(1200, 150))
        text = QtWidgets.QPlainTextEdit()
        text.setReadOnly(True)
        text.setMaximumBlockCount(ch.MAX_ENTRIES)
        text.setStyleSheet('font-family: monospace; font-size: 10pt;')
        dock.addWidget(text)

        def on_entry(entry):
            lvl  = entry['level_name']
            fil  = entry['file']
            func = entry['function']
            line = entry['linenr']
            msg  = entry['message']
            loc  = f'{fil}:{line} {func}()' if fil else ''
            text.appendPlainText(f'[{lvl}] {loc}  {msg}')

        ch.add_listener(on_entry)
        return dock

    # ---- Plot-X dock (Y vs index) ----

    def _make_plot_x_dock(self, ch: PlotXChannel):
        dock = Dock(ch.name, size=(800, 200))
        pw = pg.PlotWidget()
        pw.enableAutoRange()
        pw.showGrid(x=True, y=True)
        dock.addWidget(pw)

        colors = ['r', 'b', 'g', 'y', 'm', 'c']
        curves = [pw.plot(pen=colors[i % len(colors)]) for i in range(ch.n_values)]

        def on_update(series):
            for i, curve in enumerate(curves):
                if i < len(series):
                    curve.setData(list(series[i]))

        ch.add_listener(on_update)
        return dock

    # ---- Plot-T dock (Y vs real time) ----

    def _make_plot_t_dock(self, ch: PlotTChannel):
        dock = Dock(ch.name, size=(800, 200))
        pw = pg.PlotWidget()
        pw.enableAutoRange()
        pw.showGrid(x=True, y=True)
        pw.setLabel('bottom', 'Time', units='s')
        dock.addWidget(pw)

        colors = ['r', 'b', 'g', 'y', 'm', 'c']
        curves = [pw.plot(pen=colors[i % len(colors)]) for i in range(ch.n_values)]

        def on_update(times, series):
            t = np.array(times)
            for i, curve in enumerate(curves):
                if i < len(series):
                    curve.setData(t, np.array(series[i]))

        ch.add_listener(on_update)
        return dock

    # ---- Plot-XY dock ----

    def _make_plot_xy_dock(self, ch: PlotXYChannel):
        dock = Dock(ch.name, size=(400, 400))
        pw = pg.PlotWidget()
        pw.enableAutoRange()
        pw.showGrid(x=True, y=True)
        pw.setAspectLocked(True)
        dock.addWidget(pw)

        scatter = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None),
                                     brush=pg.mkBrush(255, 0, 0, 180))
        pw.addItem(scatter)

        def on_update(xs, ys):
            scatter.setData(list(xs), list(ys))

        ch.add_listener(on_update)
        return dock

    # ------------------------------------------------------------------ #
    # Run / shutdown                                                       #
    # ------------------------------------------------------------------ #

    def exec(self):
        self._win.show()
        self._app.aboutToQuit.connect(self._on_quit)
        self._app.exec()

    def _on_quit(self):
        self._settings.setValue(SETTINGS_GEOM_KEY, self._win.saveGeometry())
        try:
            self._settings.setValue(SETTINGS_STATE_KEY, self._area.saveState())
        except Exception:
            pass
        if self._device:
            self._device.stop()
