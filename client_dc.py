#!/usr/bin/python3
import argparse, logging, json, asyncio, random
from enum import Enum

from aiohttp import web, ClientSession

from node import MultiValueNode


class BackendType(Enum):
    cpu = "cpu"
    gpu = "gpu"


class ServiceType(Enum):
    asr = "asr"
    tts = "tts"


class DCNode(MultiValueNode):
    def __init__(self, port, neighbours, storage_items, ksize, debug=False):
        super().__init__(port, neighbours, storage_items, ksize)

        self.dht_runner = None
        self.debug = debug


    async def start_dht(self, _):
        self.dht_runner = asyncio.create_task(self.run(ping=True))


    async def stop_dht(self, _):
        self.dht_runner.cancel()
        await self.dht_runner


    async def find_service_addr(self, service, backend):
        key = self.generate_service_key(service, backend)
        nodes = await self.get_multi_value(key, shallow=True)

        for node in nodes:
            await self.node.set(key, node)

        parsed_value = self.parse_storage_value(random.choice(nodes))

        if parsed_value is None:
            raise RuntimeError("invalid service address")

        return parsed_value[-1]


    async def asr(self, request):
        try:
            address = await self.find_service_addr(ServiceType.asr, BackendType.cpu)
            request_data = await request.post()

            async with ClientSession() as session:
                response = await self.query_asr_service(
                    session, address, data={"audio_blob": request_data["audio_blob"].file.read()}, timeout=10.0
                )

                if response is not None:
                    return web.json_response(response)

        except Exception as e:
            request.app.logger.exception(e)

        return web.json_response({"response_code": 1})


    async def synthesize(self, request):
        try:
            address = await self.find_service_addr(ServiceType.tts, BackendType.cpu)
            request_data = await request.json()

            async with ClientSession() as session:
                response = await self.query_tts_service(
                    session, address, text=request_data["text"], voice=request_data["voice"], timeout=10.0
                )

            if response is not None:
                return web.json_response(response)

        except Exception as e:
            request.app.logger.exception(e)

        return web.json_response({"response_code": 1})


    @staticmethod
    def validate_service_address(address):
        if any(address.startswith(prefix) for prefix in ("localhost", "127.0.0.1")):
            return False

        return True


    def parse_storage_value(self, value):
        try:
            service, backend, address = value.split(sep="/")

        except ValueError:
            return None

        if not self.debug and not self.validate_service_address(address):
             return None

        return service, backend, address


    @staticmethod
    async def query_asr_service(session, address, data, timeout=None):

        try:
            async with session.post("http://%s/asr" % address, data=data, headers={}, timeout=timeout) as resp:
                return json.loads(await resp.text())

        except Exception as e:
            logging.exception(e)
            return None


    @staticmethod
    async def query_tts_service(session, address, text, voice=None, timeout=None):
        payload = {
            "voice": "Natasha" if voice is None else voice,
            "text": text
        }

        try:
            async with session.post("http://%s/synthesize" % address, json=payload, timeout=timeout) as resp:
                return json.loads(await resp.text())

        except Exception as e:
            logging.exception(e)
            return None


    async def validate_storage_value(self, session, parsed_value):
        service, backend, address = parsed_value
        service = ServiceType(service)

        if service == ServiceType.asr:
            response = await self.query_asr_service(session, address, data={}, timeout=10.0)
            _, value = self.generate_service_item(service, backend, address)

            value = value if response is not None else None

        elif service == ServiceType.tts:
            response = await self.query_tts_service(session, address, text="", timeout=10.0)
            _, value = self.generate_service_item(service, backend, address)

            value = value if response is not None else None

        else:
            value = None

        return value


    @staticmethod
    def generate_service_key(service, backend):
        service, backend = ServiceType(service).value, BackendType(backend).value
        return "%s/%s" % (service, backend)


    @staticmethod
    def generate_service_item(service, backend, address):
        service, backend = ServiceType(service).value, BackendType(backend).value
        return "%s/%s" % (service, backend), "%s/%s/%s" % (service, backend, address)


def parse_addr_list(addr_list_str):
    addr_list = []

    if len(addr_list_str) > 0:
        for neighbour in addr_list_str.split(sep=","):
            address, port = neighbour.split(sep=":")

            if len(neighbour) > 0:
                addr_list.append((address.strip(), int(port)))

    return addr_list


def parse_neighbours(local_port, neighbours_str):
    neighbours = parse_addr_list(neighbours_str)
    neighbours.append(("127.0.0.1", local_port))

    return neighbours


def parse_services(service_list_str):
    storage_items = {}

    if len(service_list_str) > 0:
        for service_str in service_list_str.split(sep=","):
            service, backend, address = service_str.split(sep="/")

            if not DCNode.validate_service_address(address):
                raise ValueError("Invalid service address: %s" % address)

            key, value = DCNode.generate_service_item(service, backend, address)
            storage_items[key] = value

    return storage_items


def create_app(port, neighbours, storage_items):
    node = DCNode(port, neighbours, storage_items, ksize=20)
    app = web.Application()

    app.on_startup.append(node.start_dht)
    app.on_cleanup.append(node.stop_dht)

    app.add_routes([
        web.post("/asr", node.asr),
        web.post("/synthesize", node.synthesize)
    ])

    return app


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--neighbours", type=str, default="")
    parser.add_argument("--services", type=str, help="service/backend/address:port", required=True)

    args = parser.parse_args()

    neighbours = parse_neighbours(args.port, args.neighbours)
    storage_items = parse_services(args.services)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    web.run_app(create_app(args.port, neighbours, storage_items), host="0.0.0.0", port=5600)


if __name__ == "__main__":
    main()
