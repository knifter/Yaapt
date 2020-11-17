
# from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
# from pyqtgraph.dockarea import Dock
import numpy as np
import decimal
from collections import deque

# TODO: move to YDock, primary, secondary color
brushes = [pg.mkBrush(25,25,25,60)]*10
brushes[-1] = pg.mkBrush(255,0,0,255)

class Dock:
    def __init__(self):
        pass

class XYPlotDock(Dock):
    def __init__(self, area, name = 'XY'):
        self._hist = True
        
        # X-Y Alignment Plot
        dock = pg.dockarea.Dock(name, size=(600,600))

        plotwidget = pg.PlotWidget()
        plotwidget.setRange(yRange=[-1,1], xRange=[-1,1])
        plotwidget.showGrid(x=True, y=True)
        dock.addWidget(plotwidget)

        self._plot = pg.ScatterPlotItem(size=10,pen=pg.mkPen(None), brush=pg.mkBrush(255,0,0,255), name="Laser beam")
        self._plot.setSize(10)
        plotwidget.addItem(self._plot)
        
        self._data = np.zeros(shape=(10, 2))
        area.addDock(dock) # , 'left')
    
    def appendXY(self, x, y):
        x = decimal.Decimal(x)
        y = decimal.Decimal(y)
    
        self._data[:-1] = self._data[1:]
        self._data[-1][0] = x
        self._data[-1][1] = y
        if self._hist:
            self._plot.setData(pos=self._data, brush=brushes)
        else:
            self._plot.setData([x],[y])

class YTPlotDock(Dock):
    def __init__(self, area, name = 'value', samples=100, sample_rate=0.001):
            # Power Plot
        dock = pg.dockarea.Dock(name, size=(600, 100))
        plotwidget = pg.PlotWidget()
        plotwidget.enableAutoRange()
        plotwidget.setLabel('bottom', text='Time (s)')
        dock.addWidget(plotwidget)
        self._plot = plotwidget.plot(pen=(255,0,0))
        self._data = np.linspace((0.0,0.0),((sample_rate*(samples-1.0)),0.0),samples)
        self._offset = 0
        area.addDock(dock, 'bottom')
        self._dq_data = deque(np.zeros(samples), maxlen=samples)
        self._sample_rate = sample_rate

    def appendY(self, y):
        self._data[:-1] = self._data[1:]
        self._data[-1] = y

        self._offset += 1
        self._plot.setData(self._data)
        self._plot.setPos(self._offset, 0)

    def appendYs(self, y):
        self._dq_data.extend(y)
        self._data[:,1] = np.asarray(self._dq_data)

        self._plot.setData(self._data)

class FFTPlotDock(Dock):
    def __init__(self, area, name='value', samples=100, sample_rate=0.001):
            # Power Plot
        dock = pg.dockarea.Dock(name, size=(600,100))
        plotwidget = pg.PlotWidget()
        plotwidget.enableAutoRange()
        plotwidget.setLabel('bottom', text='f (Hz)')
        dock.addWidget(plotwidget)
        self._plot = plotwidget.plot(pen=(255,0,0))
        self._plot.setFftMode(True)
        self._data = np.linspace((0.0,0.0),((sample_rate*(samples-1.0)),0.0),samples)
        self._offset = 0
        area.addDock(dock, 'bottom')
        self._dq_data = deque(np.zeros(samples), maxlen=samples)
        self._sample_rate = sample_rate

    def appendY(self, y):
        self._data[:-1] = self._data[1:]
        self._data[-1][0] = self._data[-2][0] + self._sample_rate
        self._data[-1][1] = y

        self._plot.setData(self._data)

    def appendYs(self, y):
        self._dq_data.extend(y)
        self._data[:,1] = np.asarray(self._dq_data)

        self._plot.setData(self._data)
