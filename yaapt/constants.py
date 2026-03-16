# Protocol constants — mirror of the FieldType_t and ChannelType_t enums in yaapt.cpp / yaapt.h.
# Keep in sync with the C++ side.

# ---- Channel types (ChannelType_t) ----
CHANNEL_TYPE_NONE    = 0x00
CHANNEL_TYPE_LOG     = ord('L')
CHANNEL_TYPE_PLOT_X  = ord('X')   # Y values, evenly-spaced index on X
CHANNEL_TYPE_PLOT_T  = ord('T')   # Y values with micros() timestamp
CHANNEL_TYPE_PLOT_XY = ord('Y')   # explicit X-Y pairs
CHANNEL_TYPE_DATA    = ord('D')
CHANNEL_TYPE_TEXT    = ord('P')   # Arduino Print interface

# ---- Startup magic ----
YAAPT_MAGIC = b'Yaapt#v'          # followed by 1 decimal version byte

# ---- Channel 0 commands (host → device, single-byte payload, range 0x01–0x0F) ----
CMD_DESC_REQUEST  = 0x01   # request channel descriptors (device responds with descriptor frames, no magic/version)
CMD_REBOOT        = 0x02   # reboot / reset the device
CMD_READ_CONFIG   = 0x03   # re-read configuration from storage
CMD_RESET_CONFIG  = 0x04   # reset configuration to defaults
CMD_BEEP          = 0x05   # audible beep

# ---- Channel descriptor fields (FieldType_t, used in channel 0 payload) ----
FIELD_CHANNEL_DESC     = 0x10
FIELD_GROUP_START      = ord('{')
FIELD_GROUP_END        = ord('}')
FIELD_CHANNEL_ID       = ord('C')
FIELD_CHANNEL_TYPE     = 0x11
FIELD_CHANNEL_NAME     = 0x12
FIELD_CHANNEL_N_VALUES = 0x13

# ---- Log payload field tags ----
FIELD_LOG_LEVEL    = 0x20
FIELD_LOG_LINENR   = 0x21
FIELD_LOG_FILENAME = 0x22
FIELD_LOG_FUNCTION = 0x23
FIELD_LOG_MESSAGE  = 0x24

# ---- Log level codes ----
LOG_LEVEL_DEBUG   = ord('D')
LOG_LEVEL_INFO    = ord('I')
LOG_LEVEL_WARNING = ord('W')
LOG_LEVEL_ERROR   = ord('E')

LOG_LEVEL_NAMES = {
    LOG_LEVEL_DEBUG:   'DEBUG',
    LOG_LEVEL_INFO:    'INFO',
    LOG_LEVEL_WARNING: 'WARNING',
    LOG_LEVEL_ERROR:   'ERROR',
}

# ---- Value type tags (used inside plot payloads) ----
FIELD_FLOAT  = ord('F')
FIELD_DOUBLE = ord('D')
FIELD_UINT8  = ord('8')
FIELD_INT8   = ord('7')
FIELD_UINT32 = ord('U')
FIELD_INT32  = ord('I')   # was 'S' — fixed collision with FIELD_STRING
FIELD_UINT64 = ord('V')
FIELD_INT64  = ord('L')
FIELD_STRING = ord('S')

# Size in bytes for each value type tag
FIELD_VALUE_SIZES = {
    FIELD_FLOAT:  4,
    FIELD_DOUBLE: 8,
    FIELD_UINT8:  1,
    FIELD_INT8:   1,
    FIELD_UINT32: 4,
    FIELD_INT32:  4,
    FIELD_UINT64: 8,
    FIELD_INT64:  8,
}

# struct format strings for unpacking value type tags (little-endian)
FIELD_VALUE_FORMATS = {
    FIELD_FLOAT:  '<f',
    FIELD_DOUBLE: '<d',
    FIELD_UINT8:  '<B',
    FIELD_INT8:   '<b',
    FIELD_UINT32: '<I',
    FIELD_INT32:  '<i',
    FIELD_UINT64: '<Q',
    FIELD_INT64:  '<q',
}

# ---- Serial defaults ----
YAAPT_SERIAL_BAUD    = 115200
YAAPT_SYNC_TIMEOUT   = 0.1    # seconds of silence → trigger resync
YAAPT_DEVICE_TIMEOUT = 0.2    # seconds without magic string → emit 'no_device'
