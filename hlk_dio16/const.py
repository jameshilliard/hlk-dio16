from enum import IntEnum

COMMAND_HEAD = b"\x6a\xa6"
COMMAND_TYPE_OUTPUT_CTR = 0x01
COMMAND_TYPE_READ = 0xFE


class Command(IntEnum):
    OUTPUT_CTR = 0x01
    DEVICE_TIME = 0x02
    TAP_TIME = 0x03
    DELAY_TIME = 0x04
    MODBUS_ADDRESS = 0x05
    OUTPUT_STATE = 0x06
    INPUT_STATE = 0x07
    CYCLE_TIME = 0x08
    AUTO_ENABLE = 0x0F
    AUTO_1 = 0x10
    AUTO_2 = 0x11
    AUTO_3 = 0x12
    AUTO_4 = 0x13
    AUTO_5 = 0x14
    AUTO_6 = 0x15
    AUTO_7 = 0x16
    AUTO_8 = 0x17
    AUTO_9 = 0x18
    AUTO_10 = 0x19
    AUTO_11 = 0x1A
    AUTO_12 = 0x1B
    AUTO_13 = 0x1C
    AUTO_14 = 0x1D
    AUTO_15 = 0x1E
    AUTO_16 = 0x1F
    TYPE_RESPONSE = 0xFF
