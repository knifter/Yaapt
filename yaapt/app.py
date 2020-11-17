
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.dockarea import DockArea, Dock
from yaapt.docks import XYPlotDock, YTPlotDock
import pyqtgraph as pg

class YaaptApplication:
	def __init__(self):
		self._app = QtGui.QApplication([])
		self._MainWindow = QtGui.QMainWindow()
		self._DockArea = DockArea()
		self._MainWindow.setCentralWidget(self._DockArea)
		self._MainWindow.resize(1000,800)
		self._MainWindow.setWindowTitle('Yaapt')

		pg.setConfigOptions(antialias=True)
		pg.setConfigOption('background', 'w')
		pg.setConfigOption('foreground', 'k')

		# XYPlotDock(self._DockArea, 'Laser Alignment')
		YTPlotDock(self._DockArea, 'Plot1')
		YTPlotDock(self._DockArea, 'Plot2')
	

	def exec(self):
	    #QtGui.QApplication.instance().exec_()
		self._MainWindow.show()
		self._app.exec()
