import math
import sys
from typing import Optional

from mininet.clean import cleanup
from mininet.cli import CLI
from mininet.net import Containernet
from mininet.node import RemoteController
from mininet.link import TCIntf
from mininet.log import setLogLevel, info
from mininet.util import custom

# TODO: Reconsider addressing

def setup_network(
    client_count: int = 2,
    server_count: int = 4,
    client_image: str = "ubuntu:resolute",
    server_image: str = "ubuntu:resolute",
    servers_per_access_switch: int = 2,
    link_bandwidth_mbit: Optional[int] = None,
    link_delay: Optional[str] = None,
    controller_address: str = "127.0.0.1",
    controller_port: int = 6653,
):
    net = Containernet(
        controller = custom(
            RemoteController,
            ip = controller_address,
            port = controller_port,
        ),
        intf = custom(
            TCIntf,
            bw = link_bandwidth_mbit,
            delay = link_delay,
        )
    )
    info('*** Adding controller\n')
    net.addController()

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
    import argparse

    parser = argparse.ArgumentParser(
        add_help = True,
    )

    client_group = parser.add_argument_group(
        "Client config options"
    )
    client_group.add_argument(
        "--client-count",
        type = int,
        default = 2,
        help = "Number of client hosts to launch",
    )
    client_group.add_argument(
        "--client-image",
        type = str,
        default = "ubuntu:resolute",
        help = "Docker image to use for client hosts",
    )

    server_group = parser.add_argument_group(
        "Server config options"
    )
    server_group.add_argument(
        "--server-count",
        type = int,
        default = 4,
        help = "Number of server hosts to launch",
    )
    server_group.add_argument(
        "--server-image",
        type = str,
        default = "ubuntu:resolute",
        help = "Docker image to use for server hosts",
    )
    server_group.add_argument(
        "--servers-per-access-switch",
        type = int,
        default = 2,
        help = "Maximum number of server hosts to attach to a single access layer switch",
    )

    link_group = parser.add_argument_group(
        "Link config options"
    )
    link_group.add_argument(
        "--link-bw_mbit",
        type = int,
        help = "Link bandwidth in Mbit",
    )
    link_group.add_argument(
        "--link-delay",
        type = str,
        help = "Link delay, [us, ns, ms] supported as units",
    )

    controller_group = parser.add_argument_group(
        "Controller config options"
    )   
    controller_group.add_argument(
        "--controller-addr",
        type = str,
        default = "127.0.0.1",
        help = "OpenFlow controller address",
    )
    
    controller_group.add_argument(
        "--controller-port",
        type = int,
        default = 6653,
        help = "OpenFlow controller TCP port",
    )

    args = parser.parse_args()

    setLogLevel("info")

    net = setup_network(
        client_count = args.client_count,
        server_count = args.server_count,
        client_image = args.client_image,
        server_image = args.server_image,
        servers_per_access_switch = args.servers_per_access_switch,
        link_bandwidth_mbit = args.link_bw_mbit,
        link_delay = args.link_delay,
        controller_address = args.controller_addr,
        controller_port = args.controller_port,
    )
    
    info('*** Starting network\n')
    net.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network')
    net.stop()

    info('*** Cleaning up')
    cleanup()
