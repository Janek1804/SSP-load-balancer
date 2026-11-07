import math

from mininet.clean import cleanup
from mininet.cli import CLI
from mininet.net import Containernet
from mininet.log import setLogLevel, info

# TODO: Link setup
# TODO: Controller setup
# TODO: Reconsider addressing

def setup_network(
    client_count: int = 2,
    server_count: int = 4,
    client_image: str = "ubuntu:trusty",
    server_image: str = "ubuntu:trusty",
    servers_per_access_switch: int = 2,
):
    net = Containernet()

    info('*** Adding switches\n')
    s1 = net.addSwitch("s1") # Core

    distribution_switches = []
    s2 = net.addSwitch("s2") # Distribution
    distribution_switches.append(s2)
    net.addLink(
        s1,
        s2,
        1,
        1,
    )
    s3 = net.addSwitch("s3") # Distribution
    distribution_switches.append(s3)
    net.addLink(
        s1,
        s3,
        2,
        1,
    )

    access_switch_count = math.ceil(server_count / servers_per_access_switch)
    access_switches = []
    first_access_switch_id = 1 + len(distribution_switches) + 1
    for access_switch_number, access_switch_id in enumerate(range(first_access_switch_id, first_access_switch_id + access_switch_count)):
        access_switch = net.addSwitch(f"s{access_switch_id}")
        access_switches.append(access_switch)
        net.addLink(
            distribution_switches[access_switch_id % len(distribution_switches)],
            access_switch,
            (access_switch_number // len(distribution_switches)) + 2,
            1,
        )

    info("*** Adding hosts\n")
    for host_id in range(1, client_count + 1):
        host = net.addDocker(
            f"h_client{host_id}",
            dimage = client_image
        )
        net.addLink(
            s1,
            host,
            len(distribution_switches) + host_id,
            1
        )


    info("*** Adding servers\n")
    for server_id in range(1, server_count + 1):
        server = net.addDocker(
            f"h_server{server_id}",
            dimage = server_image
        )
        net.addLink(
            access_switches[(server_id - 1) % len(access_switches)],
            server,
            (server_id - 1) // len(access_switches) + 2,
            1,
        )

    return net


if __name__ == "__main__":
    setLogLevel("info")

    net = setup_network()
    
    info('*** Starting network\n')
    net.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network')
    net.stop()

    info('*** Cleaning up')
    cleanup()
