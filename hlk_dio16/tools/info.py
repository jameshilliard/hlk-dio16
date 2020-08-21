import asyncio
import argparse
import logging
from hlk_dio16 import create_hlk_dio16_connection
from pprint import pformat

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="HLK-DIO16 get info")


parser.add_argument(
    "--host", dest="host", type=str, default="127.0.0.1", help="Host to connect to"
)

parser.add_argument(
    "--port", dest="port", type=int, default=8080, help="Port to connect to"
)

options = parser.parse_args()


async def main():
    loop = asyncio.get_event_loop()
    client = await create_hlk_dio16_connection(
        host=options.host, port=options.port, loop=loop
    )
    output_state = await client.output_state()
    logger.info(f"output_state:\n{pformat(output_state)}")
    input_state = await client.input_state()
    logger.info(f"input_state:\n{pformat(input_state)}")
    device_time = await client.device_time()
    logger.info(f"device_time:\n{pformat(device_time)}")
    client.stop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())

    except KeyboardInterrupt:
        loop.close()
