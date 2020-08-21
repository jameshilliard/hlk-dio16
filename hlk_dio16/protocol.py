"""HLK-DIO16 Protocol Support."""
import asyncio
from collections import deque
import logging
from hlk_dio16.const import COMMAND_HEAD, Command
from hlk_dio16.util import cksum, hexdump, format_read


class DIO16Protocol(asyncio.Protocol):
    """HLK-DIO16 relay control protocol."""

    transport = None  # type: asyncio.Transport

    def __init__(self, client, disconnect_callback=None, loop=None, logger=None):
        """Initialize the HLK-DIO16 protocol."""
        self.client = client
        self.loop = loop
        self.logger = logger
        self._buffer = b""
        self.disconnect_callback = disconnect_callback
        self.last_cmd = None
        self._timeout = None
        self._cmd_timeout = None
        self._keep_alive = None

    def connection_made(self, transport):
        """Initialize protocol transport."""
        self.logger.info("connected")
        self.transport = transport

    def _process_response(self, cmd, response):
        if self.last_cmd == cmd:
            self.client.in_transaction = False
            self.client.active_packet = False
            self.last_cmd = None
            self.client.active_transaction.set_result(response)
            if self.client.waiters:
                self.send_packet()

    def process_frame(self, frame):
        cmd = Command(frame[0])
        data = frame[1:]
        self.logger.info(f"cmd: {cmd.name}, data: {hexdump(data)}")
        if cmd == Command.OUTPUT_STATE:
            assert len(data) == 2
            states = {}
            for switch in range(0, 8):
                states[switch + 1] = data[0] >> switch & 1 == 1
            for switch in range(0, 8):
                states[switch + 9] = data[1] >> switch & 1 == 1
            self.logger.debug(f"output states: {states}")
            self._process_response(cmd, states)
        elif cmd == Command.INPUT_STATE:
            assert len(data) == 2
            states = {}
            for switch in range(0, 8):
                states[switch + 1] = data[0] >> switch & 1 == 1
            for switch in range(0, 8):
                states[switch + 9] = data[1] >> switch & 1 == 1
            self.logger.debug(f"input states: {states}")
            self._process_response(cmd, states)
        elif cmd == Command.DEVICE_TIME:
            assert len(data) == 6
            time = {}
            time["Year"] = data[0] + 2018
            time["Month"] = data[1]
            time["Day"] = data[2]
            time["Hour"] = data[3]
            time["Minute"] = data[4]
            time["Second"] = data[5]
            self.logger.debug(f"device time: {time}")
            self._process_response(cmd, time)

    def data_received(self, data):
        """Add incoming data to buffer."""
        self.logger.info(f"data received: {hexdump(data)}")
        self._buffer += data
        while (
            len(self._buffer) >= 3
            and self._buffer[0:2] == COMMAND_HEAD
            and len(self._buffer) >= (self._buffer[2] + 3)
        ):
            length = self._buffer[2]
            frame = self._buffer[3 : 2 + length]
            computed = cksum(self._buffer[: 2 + length])
            checksum = self._buffer[length + 2]
            self._buffer = self._buffer[3 + length :]
            if computed != checksum:
                self.logger.info(
                    f"got frame: {hexdump(frame)}, checksum: {hex(checksum)}, computed: {hex(computed)}"
                )
            assert computed == checksum
            self.process_frame(frame)

    def send_packet(self):
        """Write next packet in send queue."""
        waiter, packet = self.client.waiters.popleft()
        self.logger.debug("sending packet: %s", hexdump(packet))
        self.client.active_transaction = waiter
        self.client.in_transaction = True
        self.client.active_packet = packet
        self.transport.write(packet)

    def connection_lost(self, exc):
        """Log when connection is closed, if needed call callback."""
        if exc:
            self.logger.error("disconnected due to error")
        else:
            self.logger.info("disconnected because of close/abort.")
        if self._keep_alive:
            self._keep_alive.cancel()
        if self.disconnect_callback:
            asyncio.ensure_future(self.disconnect_callback(), loop=self.loop)


class DIO16Client:
    """HLK-DIO16 client wrapper class."""

    def __init__(
        self,
        host,
        port=8080,
        disconnect_callback=None,
        reconnect_callback=None,
        loop=None,
        logger=None,
        timeout=10,
        reconnect_interval=10,
        keep_alive_interval=3,
    ):
        """Initialize the HLK-DIO16 client wrapper."""
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
        self.host = host
        self.port = port
        self.transport = None
        self.protocol = None
        self.is_connected = False
        self.reconnect = True
        self.timeout = timeout
        self.reconnect_interval = reconnect_interval
        self.keep_alive_interval = keep_alive_interval
        self.disconnect_callback = disconnect_callback
        self.reconnect_callback = reconnect_callback
        self.waiters = deque()
        self.status_waiters = deque()
        self.in_transaction = False
        self.active_transaction = None
        self.active_packet = None
        self.status_callbacks = {}
        self.states = {}

    async def setup(self):
        """Set up the connection with automatic retry."""
        while True:
            fut = self.loop.create_connection(
                lambda: DIO16Protocol(
                    self,
                    disconnect_callback=self.handle_disconnect_callback,
                    loop=self.loop,
                    logger=self.logger,
                ),
                host=self.host,
                port=self.port,
            )
            try:
                self.transport, self.protocol = await asyncio.wait_for(
                    fut, timeout=self.timeout
                )
            except asyncio.TimeoutError:
                self.logger.warning("Could not connect due to timeout error.")
            except OSError as exc:
                self.logger.warning("Could not connect due to error: %s", str(exc))
            else:
                self.is_connected = True
                if self.reconnect_callback:
                    self.reconnect_callback()
                break
            await asyncio.sleep(self.reconnect_interval)

    def stop(self):
        """Shut down transport."""
        self.reconnect = False
        self.logger.debug("Shutting down.")
        if self.transport:
            self.transport.close()

    async def handle_disconnect_callback(self):
        """Reconnect automatically unless stopping."""
        self.is_connected = False
        if self.disconnect_callback:
            self.disconnect_callback()
        if self.reconnect:
            self.logger.debug("Protocol disconnected...reconnecting")
            await self.setup()
            if self.in_transaction:
                self.protocol.transport.write(self.active_packet)
            else:
                packet = format_frame()
                self.protocol.transport.write(packet)

    def register_status_callback(self, callback, switch):
        """Register a callback which will fire when state changes."""
        if self.status_callbacks.get(switch, None) is None:
            self.status_callbacks[switch] = []
        self.status_callbacks[switch].append(callback)

    def _send(self, packet):
        """Add packet to send queue."""
        fut = self.loop.create_future()
        self.waiters.append((fut, packet))
        if self.waiters and self.in_transaction is False:
            self.protocol.send_packet()
        return fut

    async def output_state(self):
        """Get current relay output state."""
        cmd = Command.OUTPUT_STATE
        self.protocol.last_cmd = cmd
        packet = format_read(cmd)
        states = await self._send(packet)
        return states

    async def input_state(self):
        """Get current relay output state."""
        cmd = Command.INPUT_STATE
        self.protocol.last_cmd = cmd
        packet = format_read(cmd)
        states = await self._send(packet)
        return states

    async def device_time(self):
        """Get current relay output state."""
        cmd = Command.DEVICE_TIME
        self.protocol.last_cmd = cmd
        packet = format_read(cmd)
        time = await self._send(packet)
        return time


async def create_hlk_dio16_connection(
    port=None,
    host=None,
    disconnect_callback=None,
    reconnect_callback=None,
    loop=None,
    logger=None,
    timeout=None,
    reconnect_interval=None,
    keep_alive_interval=None,
):
    """Create HLK-DIO16 Client class."""
    client = DIO16Client(
        host,
        port=port,
        disconnect_callback=disconnect_callback,
        reconnect_callback=reconnect_callback,
        loop=loop,
        logger=logger,
        timeout=timeout,
        reconnect_interval=reconnect_interval,
        keep_alive_interval=keep_alive_interval,
    )
    await client.setup()

    return client
