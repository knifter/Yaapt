
import serial
import serial.tools.list_ports
from time import sleep
# from serial import Serial
# from serial.tools import list_ports
from listportsdialog import ListPortsDialog
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.dockarea import DockArea, Dock

SERIAL_BAUD = 1000000

SerPort = None
# MainWindow = None

def main():
    # global MainWindow
    app = QtGui.QApplication([])
    MainWindow = QtGui.QMainWindow()
    area = DockArea()
    MainWindow.setCentralWidget(area)
    MainWindow.resize(1000,800)
    MainWindow.setWindowTitle('Yaapt')

    port_open()
    target_reboot()

    while 1:
        sleep(0.01)
        s = SerPort.read_all()
        if s:
            print("> %s" % s.decode(encoding='ascii', errors='replace'), end='')

def port_open():
    global SerPort
    dlg = ListPortsDialog()#parent=MainWindow)
    result = dlg.run()
    port = dlg.get_port()
    SerPort = serial.Serial(
        port=port, 
        baudrate=SERIAL_BAUD, 
        bytesize = 8,
        parity = 'N',
        stopbits=1,
        timeout = 1,
        xonxoff=0, rtscts=0)
    print(f"Opened port {port}\n")

def target_reboot():
    SerPort.setDTR(0);
    sleep(0.1);
    SerPort.setDTR(1);

if __name__ == '__main__':
    main()
