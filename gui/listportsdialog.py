"""
Port selection dialog.

Shows one button per available serial port. A single click connects.
The last-used port is remembered across sessions and marked "(last)".
If only one port is available it is selected automatically.
"""

import serial
from PyQt6 import QtWidgets, QtCore
from serial.tools import list_ports

SETTINGS_ORG      = 'Yaapt'
SETTINGS_APP      = 'Yaapt'
SETTINGS_LAST_KEY = 'last_port'


class ListPortsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Select serial port')
        self.setMinimumWidth(300)

        self._settings = QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._last_port = self._settings.value(SETTINGS_LAST_KEY, '')
        self.portname = None

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel('Available ports:'))

        self._btn_group = QtWidgets.QVBoxLayout()
        layout.addLayout(self._btn_group)

        layout.addStretch()

        self._status = QtWidgets.QLabel('')
        self._status.setStyleSheet('color: red;')
        layout.addWidget(self._status)

        self.setLayout(layout)
        self._populate()

    def _populate(self):
        ports = sorted(list_ports.comports(), key=lambda p: p.device)

        # Clear existing buttons
        while self._btn_group.count():
            item = self._btn_group.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not ports:
            self._status.setText('No serial ports found.')
            return

        for info in ports:
            label = info.device
            if info.description and info.description != 'n/a':
                label += f'  —  {info.description}'
            if info.device == self._last_port:
                label += '  (last)'

            btn = QtWidgets.QPushButton(label)
            btn.setProperty('portname', info.device)
            # Highlight the last-used port
            if info.device == self._last_port:
                btn.setStyleSheet('font-weight: bold;')
            btn.clicked.connect(self._on_button_clicked)
            self._btn_group.addWidget(btn)

    def _on_button_clicked(self):
        btn = self.sender()
        portname = btn.property('portname')
        try:
            s = serial.Serial(portname, timeout=0.5)
            s.close()
            self.portname = portname
            self._settings.setValue(SETTINGS_LAST_KEY, portname)
            self.accept()
        except serial.SerialException as e:
            self._status.setText(f'Cannot open {portname}: {e}')

    def run(self):
        """
        Show the dialog and return True if a port was selected.
        Auto-connects if only one port is available.
        """
        ports = list(list_ports.comports())

        if not ports:
            QtWidgets.QMessageBox.critical(self, 'No ports', 'No serial ports available.')
            return False

        if len(ports) == 1:
            # Single port: try to connect without showing the dialog
            self.portname = ports[0].device
            try:
                s = serial.Serial(self.portname, timeout=0.5)
                s.close()
                self._settings.setValue(SETTINGS_LAST_KEY, self.portname)
                return True
            except serial.SerialException:
                pass  # fall through to show dialog

        self.exec()
        return self.portname is not None

    def get_port(self):
        return self.portname
