from pyqtgraph.Qt import QtGui, QtCore
from serial.tools import list_ports

import serial

class ListPortsDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(ListPortsDialog, self).__init__(parent=None)
        self.setWindowTitle('Select serial port.')

        self.ports_list = QtGui.QListWidget()
        self.open_btn = QtGui.QPushButton('Open serial port')
        self.open_btn.clicked.connect(self.on_open)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.ports_list)
        layout.addWidget(self.open_btn)
        self.setLayout(layout)

        self.fill_ports_list()

        self.portname = None
    
    def run(self):
        if self.ports_list.count() == 0:
            QtGui.QMessageBox.critical(self, 'Error', 
                    f'No Serial ports available')
            # self.reject()
            return False
        if self.ports_list.count() == 1:
            self.ports_list.setCurrentRow(0)
            self.on_open()
            return True
        self.show()
        return self.exec_()

    def on_open(self):
        cur_item = self.ports_list.currentItem()
        if cur_item is not None:
            portname = str(cur_item.text())
            try:
                self.ser = serial.Serial(portname, 1000000, timeout=0.5)
                self.ser.close()
                self.portname = portname
                self.accept()
            except serial.SerialException as e:
                QtGui.QMessageBox.critical(self, 'Failure', 
                        f'Failed to open {cur_item.text()}: {e}')
                self.reject()
                
    def fill_ports_list(self):
        for portname, desc, hwid in list_ports.comports():
            self.ports_list.addItem(portname)

    def get_port(self):
        return self.portname

