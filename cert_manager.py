from ndn.encoding import Name, FormalName
from ndn.security import *
from typing import Dict, List, Set
from record import Record

class DefaultCertificateManager:
    def __init__(self,
                 node_prefix: Name, 
                 anchor_cert: Certificate,
                 starting_peers: List[Certificate]):
        self.node_prefix: FormalName = node_prefix
        self.anchor_cert: Certificate = anchor_cert
        self.peer_certificates: Dict[FormalName,List[Certificate]] = {}
        self.revoked_certificates: Set[FormalName] = set()


    # TODO: figure out parameter type (Data in Mnemosyne)
    def verify_signature(data) -> bool:
        # TODO
        return false

    def verify_record_format(record: Record) -> bool:
        # TODO
        return false

    # TODO: figure out parameter type (Data in Mnemosyne)
    def endorse_signature(data) -> bool:
        # TODO
        return false

    # TODO: figure out parameter type (Interest in Mnemosyne)
    def verify_signature(interest) -> bool:
        # TODO
        return false

    def accept_record(record: Record) -> None:
        # TODO
        pass

    def authorized_to_generate() -> bool:
        # TODO
        return false

    def get_certificate_name_identity(cert_name: FormalName) -> FormalName:
        # TODO
        pass
