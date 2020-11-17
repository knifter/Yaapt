
class YaaptChannel(object):
	pass

class DataChannel(YaaptChannel):
	pass

class DebugChannel(YaaptChannel):
	pass

def read_descr(buf):
    print("[INFO] Reading Channel Descriptors:")
    print("[DBG ] DESC: [%s]" % buf)
    if(buf[0] != YAAPT_INIT_START):
        print("1: %x" % buf[0])
        raise ValueError("No DESC_START after YaaptStart")
    buf = buf[1:]
    return
    while 1:
        s = SerPort.read_all()
        if not s:
            sleep(0.01)
            continue
        # if s == 'Y':
        #     start = 1;
        # else if s == 
