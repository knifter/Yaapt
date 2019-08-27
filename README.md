# Yaapt
Yet Again Another Terminal Plotter: Multi channel plotting terminal

# Features
*Yaapt* will support:
 * Being a basic serial terminal
 * quick but also command line connect/disconnect (so you can incorporate that into your build process ;)
 * But also a multi-channel terminal where each channel can:
 * Show debug lines
 * accept commands / show results
 * plot data, X vs T, X vs Y
 * process and represent data: FFT, binning
 * we'll see...
 
# Prerequisites
 * Python 3.6
 * pyqtgraph 0.10.0
 * PyQt 5.9.2
 * msgpack-python 0.6.1
 
Or maybe this works for you if you've got (ana/mini)conda installed:
> conda create -n yaapt python=3.6 -c conda-forge pyqtgraph msgpack-python
