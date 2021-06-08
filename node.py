import asyncio, logging

from kademlia.storage import IStorage
from kademlia.network import Server
from kademlia.crawling import ValueSpiderCrawl
from kademlia.node import Node
from kademlia.utils import digest

from aiohttp import ClientSession


class MultiStorage(IStorage):
    def __init__(self):
        self.data = {}


    def overwrite(self, key, value):
        value = set(value)

        if len(value) > 0:
            self.data[key] = set(value)
        else:
            del self.data[key]


    def __setitem__(self, key, value):
        value_set = self.data.get(key, set())

        if isinstance(value, list):
            value_set = value_set.union(value)
        else:
            value_set.add(value)

        self.data[key] = value_set


    def __getitem__(self, key):
        return list(self.data[key])


    def get(self, key, default=None):
        value = self.data.get(key, default)
        return list(value) if value is not default else default


    def iter_older_than(self, seconds_old):
        return ((key, list(value)) for key, value in self.data.items())


    def __iter__(self):
        return ((key, list(value)) for key, value in self.data.items())


class MultiValueSpiderCrawl(ValueSpiderCrawl):
    async def _handle_found_values(self, values):
        value_set = set(values[0])

        for value in values[1:]:
            value_set.update(value)

        value = list(value_set)
        peer = self.nearest_without_value.popleft()

        if peer:
            await self.protocol.call_store(peer, self.node.id, value)

        return value


class MultiValueNode:
    def __init__(self, port, neighbours, storage_items, ksize):
        self.logger = logging.getLogger(type(self).__name__)

        self.logger.warning(
            "Starting dht node with port=%s, neighbours=%s, storage=%s, ksize=%s" %
            (port, neighbours, storage_items, ksize)
        )

        self.port, self.neighbours, self.storage_items = port, neighbours, storage_items
        self.node = Server(ksize=ksize, storage=MultiStorage())


    async def run_local(self):
        await self.node.listen(self.port)
        await self.node.bootstrap(self.neighbours)

        for key, value in self.storage_items.items():
            await self.node.set(key, value)

        return self


    async def run(self, ping=True):
        await self.run_local()

        while True:
            if ping:
                await self.ping_node_storage()

            await asyncio.sleep(30.0)
            await self.node.bootstrap(self.neighbours)


    async def get_multi_value(self, key, shallow=True):
        dkey = digest(key)

        local_value = self.node.storage.get(dkey)
        local_value = set() if local_value is None else set(local_value)

        if len(local_value) > 0 and shallow:
            return list(local_value)

        node = Node(dkey)
        nearest = self.node.protocol.router.find_neighbors(node)

        spider = MultiValueSpiderCrawl(self.node.protocol, node, nearest, self.node.ksize, self.node.alpha)

        remote_value = await spider.find()
        remote_value = set() if remote_value is None else remote_value

        return list(local_value.union(remote_value))


    async def ping_node_storage(self):
        item_dict, sum_list = {}, set()

        for key, value in self.node.storage:
            item_dict[key] = value
            sum_list.update(value)

        async with ClientSession() as session:
            tasks = []

            for value in sum_list:
                self.logger.info("Validating value %s ..." % value)
                parsed_value = self.parse_storage_value(value)

                if parsed_value is not None:
                    tasks.append(asyncio.get_event_loop().create_task(
                        self.validate_storage_value(session, parsed_value))
                    )
                else:
                    self.logger.warning("Value %s is invalid" % value)

            values = await asyncio.gather(*tasks)
            checked_list = set()

            for source_value, value in zip(sum_list, values):
                if value is not None:
                    checked_list.add(value)
                else:
                    self.logger.warning("Value %s is invalid" % source_value)

        for key, value in item_dict.items():
            self.node.storage.overwrite(key, (item for item in value if item in checked_list))


    def parse_storage_value(self, value):
        return value


    async def validate_storage_value(self, session, parsed_value):
        return parsed_value
