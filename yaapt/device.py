import serial
from time import sleep

from yaapt.constants import *

class DeviceConnection:
	def __init__(self, port):
		self._serial = serial.Serial(
			port=port, 
			baudrate=YAAPT_SERIAL_BAUD, 
			bytesize = 8,
			parity = 'N',
			stopbits=1,
			timeout = 1,
			xonxoff=0, rtscts=0)
		self.buffer = b''
		self.bootmsg = ""

	def device_reset(self):
		self._serial.setDTR(0);
		sleep(0.1);
		self._serial.reset_input_buffer()
		self._serial.setDTR(1);

	def port(self):
		return self._serial.port

	def parse_start(self):
		b = self.buffer = b''
		print("sB ", id(self.buffer))
		print("B  ", id(b))
		self.bootmsg = ""
		found_start = False

		# scan for "YaaptStart"
		# before = SerPort.read_until(YAAPT_STARTSTRING)
		# print("BOOTMSGs:", before)
		# print("AFTER: ", SerPort.read_all())
		# return

		print("[INFO] Opened port. Initial Boot Messages:");
		while 1:
			self._read()
			if len(b) < len(YAAPT_STARTSTRING):
				sleep(0.01)
				continue
			# print("serbuf(%s) [%s]\n" % (len(serbuf), serbuf))
			try:
				i = b.index(YAAPT_STARTSTRING)
				found_start = True
				# print("F = ", i)
			except ValueError:
				i = len(b) - len(YAAPT_STARTSTRING) + 1
				# print("N = ", i)
			bootpart = b[0:i].decode(encoding="ascii", errors='replace')
			self.bootmsg += bootpart
			b = b[i:]
			print(bootpart, end='')
			if(found_start):
				break
			sleep(0.01)
		# @"YaaptStart"
		b = b[len(YAAPT_STARTSTRING):]

		try:
			i = b.index(YAAPT_CHANNEL_DESC_END)
			self.channel_desc = b[:i]
			b = b[i:]
		except ValueError:
			raise ValueError("No DESC_END found in device init stream")

		print("DESC: ", self.channel_desc)
		print("REST: ", b)
		print("REST: ", self.buffer)

	def _read(self):
		s = self._serial.read_all()
		b += s

	def pop(self, n=1):
		p = b[:n]
		b = b[n:]
		return p
