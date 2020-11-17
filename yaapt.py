
from time import sleep
from listportsdialog import ListPortsDialog

from yaapt import *

SerPort = None
# MainWindow = None
BootMsg = ""
App = None

def main():
    global App
    App = YaaptApplication()

    # # global MainWindow
    # app = QtGui.QApplication([])
    # MainWindow = QtGui.QMainWindow()
    # area = DockArea()
    # MainWindow.setCentralWidget(area)
    # MainWindow.resize(1000,800)
    # MainWindow.setWindowTitle('Yaapt')

    dev = port_open()
    dev.device_reset()
    dev.parse_start()
    sleep(0.05)

    # read_descr(serbuf[len(YAAPT_STARTSTRING):])
    # App.exec()

def port_open():
    global SerPort
    dlg = ListPortsDialog()#parent=MainWindow)
    result = dlg.run()
    port = dlg.get_port()
    if port == None:
        print("No port selected. exit.");
        quit();
    dev = DeviceConnection(port)
    print(f"Opened port {dev.port()}\n")
    return dev

if __name__ == '__main__':
    main()
