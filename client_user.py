#!/usr/bin/python3
import asyncio, argparse, logging
from datetime import datetime
from base64 import b64decode

from aiohttp import ClientSession
from client_dc import DCNode, ServiceType


class Service:
    def send_request(self, address, logger):
        raise NotImplementedError()


class ServiceASR(Service):
    def __init__(self, args):
        super().__init__()

        with open(args.file, mode="rb") as f:
            self.file = f.read()


    @staticmethod
    async def send_asr_request(address, file):
        async with ClientSession() as session:
            return await DCNode.query_asr_service(session, address, data={"audio_blob": file})


    def send_request(self, address, logger):
        response = asyncio.get_event_loop().run_until_complete(self.send_asr_request(address, self.file))

        try:
            text = response["r"][0]["response"]

        except Exception as e:
            logger.exception(e)
            return False

        logger.warning("Response: %s" % text)
        return True


class ServiceTTS(Service):
    def __init__(self, args):
        super().__init__()
        self.text, self.file = args.text, args.file

        if self.text is None:
            raise ValueError("empty synthesis query")

        if self.file is None:
            self.file = "Data/%s.wav" % str(datetime.now().time()).replace(".", "_").replace(":", "_")


    @staticmethod
    async def send_tts_request(address, text):
        async with ClientSession() as session:
            return await DCNode.query_tts_service(session, address, text=text)


    def send_request(self, address, logger):
        response = asyncio.get_event_loop().run_until_complete(self.send_tts_request(address, self.text))

        try:
            audio = b64decode(response["response"][0]["response_audio"].encode("utf-8"))

        except Exception as e:
            logger.exception(e)
            return False

        with open(self.file, mode="wb") as f:
            f.write(audio)

        logger.warning("Response in '%s'" % self.file)
        return True


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--address", type=str, required=True)
    parser.add_argument("--service", type=str, required=True)

    parser.add_argument("--file", type=str)
    parser.add_argument("--text", type=str)

    args = parser.parse_args()
    service = ServiceType(args.service)

    serviceHandler = {
        ServiceType.asr: ServiceASR,
        ServiceType.tts: ServiceTTS
    }[service](args)

    logger = logging.getLogger(__name__)
    status = serviceHandler.send_request(args.address, logger=logger)

    if not status:
        logger.error("Node failed")


if __name__ == "__main__":
    main()
