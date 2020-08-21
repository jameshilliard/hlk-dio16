from hlk_dio16.const import COMMAND_HEAD, COMMAND_TYPE_READ
from functools import reduce
from struct import pack


def cksum(data):
    return (reduce(lambda x, y: x + y, data) - 16) % 256


def hexdump(data, length=None, sep=":"):
    if length is not None:
        lines = ""
        for seq in range(0, len(data), 16):
            line = data[seq : seq + 16]
            lines += sep.join("{:02x}".format(c) for c in line) + "\n"
    else:
        lines = sep.join("{:02x}".format(c) for c in data)
    return lines


def format_read(cmd, data=None):
    """Format frame to be sent."""
    payload = pack("B", cmd.value)
    if data is not None:
        payload += data
    frame = COMMAND_HEAD
    frame += pack("B", len(payload) + 2)
    frame += pack("B", COMMAND_TYPE_READ)
    frame += payload
    frame += pack("B", cksum(frame))
    return frame
