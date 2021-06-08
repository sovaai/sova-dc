import logging, asyncio, random

from client_dc import DCNode, MultiValueNode, ServiceType, BackendType


async def sequential_network_test():
    node_addr, port = "127.0.0.1", 5678
    service_addr = "127.0.0.1:5000"

    num_nodes = 50
    nodes = {}

    for i in range(num_nodes):
        node_port = port + i
        neighbours = [(node_addr, node_port)]

        if i + 1 < num_nodes:
            neighbours.append((node_addr, node_port + 1))

        nodes[node_port] = neighbours

    tasks = []

    for port, neighbours in nodes.items():
        storage_items = {}

        if random.randint(0, 1):
            service = ServiceType.asr if random.randint(0, 1) else ServiceType.tts
            backend = BackendType.cpu if random.randint(0, 1) else BackendType.gpu

            key, value = DCNode.generate_service_item(service, backend, service_addr)
            storage_items[key] = value

        tasks.append(asyncio.get_event_loop().create_task(
            MultiValueNode(port, neighbours, storage_items, ksize=10).run())
        )

    await asyncio.gather(*tasks)


def unittest():
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    asyncio.get_event_loop().run_until_complete(sequential_network_test())


if __name__ == "__main__":
    unittest()
