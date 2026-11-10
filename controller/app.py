from ryu.base import app_manager
from ryu.controller import handler, ofp_event
from ryu.ofproto import ofproto_v1_3


class LoadBalancer(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # Random (empty) handler to trick ryu-manager into not exiting immediately
    @handler.set_ev_cls(
        ofp_event.EventOFPPacketIn,
        [
            handler.MAIN_DISPATCHER,
        ]
    )
    def packet_in_handler(self, ev):
        pass