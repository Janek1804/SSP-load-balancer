from mininet.cli import CLI
from mininet.net import Containernet
from mininet.log import setLogLevel, info

# TODO: Link setup
# TODO: Controller setup
# TODO: Reconsider addressing

def setup_network(
    client_count: int = 2,
    server_count: int = 2,
    client_image: str = "ubuntu:trusty",
    server_image: str = "ubuntu:trusty",
    servers_per_access_switch: int = 2,
):
    net = Containernet()

    info('*** Adding switches\n')
    s1 = net.addSwitch("s1") # Core

    distribution_switches = set()
    s2 = net.addSwitch("s2") # Distribution
    distribution_switches.add(s2)
    s3 = net.addSwitch("s3") # Distribution
    distribution_switches.add(s3)

    # TODO: Access switches


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

        # TODO: Link to access switches

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