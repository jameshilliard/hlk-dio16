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

def format_relay_cmd(cmd, switches, state):
    """Format frame to be sent."""
    state = 0x01 if state else 0x00
    mask = bytearray(b'\x00\x00')
    for switch in range(1, 9):
        if switch in switches:
            mask[0] = mask[0] | (1 << (switch - 1))
    for switch in range(9, 17):
        if switch in switches:
            mask[1] = mask[1] | (1 << (switch - 9))
    payload = pack("B", state)
    payload += mask
    frame = COMMAND_HEAD
    frame += pack("B", len(payload) + 2)
    frame += pack("B", cmd)
    frame += payload
    frame += pack("B", cksum(frame))
    return frame