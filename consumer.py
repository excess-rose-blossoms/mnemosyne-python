import asyncio as aio
import dbm
import logging
import sys
import random
from argparse import ArgumentParser, SUPPRESS
from typing import List, Optional, Set, Tuple
# NDN Imports
from ndn.app import NDNApp
from ndn.encoding import Name, FormalName
# Custom Imports
sys.path.insert(0,'.')
from ndn.svs import SVSync, SVSyncLogger, MissingData
from record import Record, GenesisRecord
import hashlib

app = NDNApp()

def parse_cmd_args() -> dict:
    # Command Line Parser
    parser = ArgumentParser(add_help=False,description="Logger node receiving log events and putting them into a DAG as records.")
    requiredArgs = parser.add_argument_group("required arguments")
    optionalArgs = parser.add_argument_group("optional arguments")
    informationArgs = parser.add_argument_group("information arguments")
    # Adding all Command Line Arguments
    requiredArgs.add_argument("-n", "--nodename",action="store",dest="node_name",required=True,help="id of this node in svs")
    optionalArgs.add_argument("-v","--verbose",action="store_true",dest="verbose",default=False,required=False,help="when set, svsync info is displayed as well")
    informationArgs.add_argument("-h","--help",action="help",default=SUPPRESS,help="show this help message and exit")
    # Getting all Arguments
    argvars = parser.parse_args()
    args = {}
    args["node_id"] = argvars.node_name
    args["verbose"] = argvars.verbose
    return args

# Records are stored as {Name (str): encoded TLV packet}
class RecordStorage:
    # If another process is using the DB, wait for it to be done.
    def get_db(self, db_name):
        while True:
            try:
                db = dbm.open(db_name, 'c')
                return db
            except:
                pass

    def store_record(self, record_name: str, encoded_record: bytearray):
        db = self.get_db('record_store')
        db[record_name] = bytes(encoded_record)
        db.close()

    def get_record(self, record_name):
        db = self.get_db('record_store')
        ret = None
        if record_name in db:
            ret = Record(data=db[record_name])
        db.close()
        return ret

record_storage = RecordStorage()

class Logger:
    def __init__(self, args:dict) -> None:
        self.args = args
        # The last record this logger produced.
        self.last_record_name: FormalName = None
        # Some recently-received records (same length as num. genesis records).
        self.last_names: List[FormalName] = []
        # An index into self.last_names.
        self.last_name_tops: int = 0
        # The records we've received but haven't been able to verify yet.
        self.no_prev_records: Set[str] = set()
        self.waiting_referenced_records: List[Tuple[str, str]] = []
        self.num_record_links: int = 2
        # log_events group related (communication between producer and loggers)
        self.log_events_group_prefix = "/svs/mnemosyne/log_events"
        self.svs_log_events:SVSync = SVSync(app, Name.from_str(self.log_events_group_prefix), Name.from_str(self.args["node_id"]), self.log_events_missing_callback)
        # records_group related (communication between loggers)
        self.records_group_prefix = "/svs/mnemosyne/records"
        self.svs_records:SVSync = SVSync(app, Name.from_str(self.records_group_prefix), Name.from_str(self.args["node_id"]), self.records_missing_callback)
        print(f'CONSUMER STARTED! | LOG GROUP PREFIX: {self.log_events_group_prefix} | RECORDS GROUP PREFIX {self.records_group_prefix} | NODE ID: {self.args["node_id"]} |')
        self.node_prefix = self.records_group_prefix + self.args['node_id']

        # Make genesis data
        for i in range(self.num_record_links):
            gen_rec = GenesisRecord(i)
            gen_rec_packet = gen_rec.wire_encode()
            # TODO: sign the packet

            record_storage.store_record(
                gen_rec.get_record_name_str(), gen_rec_packet)
            self.last_names.append(gen_rec.get_record_name())

    def is_record_valid(self, record_name, record_hash):
        return True
        # current_record:Record = record_storage.get_record(Name.to_str(record_name))
        # if (current_record == None): 
        #     return False
        # if (current_record.is_genesis_record()):
        #     return True
        # else:
        #     if (record_hash != current_record.get_record_hash()):
        #         return False
        #     else:
        #         isValid = True
        #         pointers = current_record.get_pointers_from_header()
        #         pointer_hashes = current_record.get_pointer_hashes_from_header()
        #         if (len(pointers) > 0):
        #             isValid = True
        #             for count, pointer in pointers:
        #                 isValid = isValid and self.is_record_valid(pointers[count], pointer_hashes[count])
        #             return isValid
        #         else:
        #             return False

    # Given a log event, create and return an NDN record packet.
    def create_record(self, log_event, event_name):
        record = Record(producer_name=self.node_prefix,
                        log_event=log_event,
                        event_name=event_name)
        if (self.last_record_name is not None):
            prospective_link_record: Record = record_storage.get_record(Name.to_str(self.last_record_name))
            if (self.is_record_valid(self.last_record_name, prospective_link_record.get_record_hash())):
                record.add_pointer(self.last_record_name, prospective_link_record.get_record_hash())
        record_list = [
            rec_name for rec_name in self.last_names if (
                Name.to_str(rec_name) not in self.no_prev_records)]
        random.shuffle(record_list)
        for tail_rec in record_list:
            prospective_link_record: Record = record_storage.get_record(Name.to_str(tail_rec))
            if (self.is_record_valid(tail_rec, prospective_link_record.get_record_hash())):
                record.add_pointer(tail_rec, prospective_link_record.get_record_hash())
            if (len(record.get_pointers_from_header())
                    >= self.num_record_links):
                break
        return record

    def log_events_missing_callback(self, missing_list: List[MissingData]) -> None:
        aio.ensure_future(self.on_missing_events(missing_list))

    async def on_missing_events(self, missing_list: List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = (await
                    self.svs_log_events.fetchData(
                        Name.from_str(i.nid), i.lowSeqno, 2))
                if content_str:
                    self.receive_log_event(
                        content_str, self.svs_log_events.getDataName(
                            Name.from_str(i.nid), i.lowSeqno))
                    # if ((self.args["node_id"] == "/even" and int(content_str.decode()) % 2 == 0)
                    #     or (self.args["node_id"] == "/odd" and int(content_str.decode()) % 2 == 1)):
                    #     self.receive_log_event(content_str)
                i.lowSeqno = i.lowSeqno + 1

    # Creates, stores, and publishes a record.
    def receive_log_event(self, content_str, data_name):
        # TODO: authenticate log event
        # Create record.
        new_record = self.create_record(content_str.decode(), data_name)
        # Encode for sending/storage.
        record_packet = new_record.wire_encode()

        # TODO: Sign the data packet

        record_storage.store_record(
            new_record.get_record_name_str(), record_packet)
        self.last_record_name = new_record.get_record_name()

        print("publishing record:")
        new_record.print()

        self.svs_records.publishData(record_packet)

    def records_missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.on_missing_records(missing_list))

    async def on_missing_records(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs_records.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str:
                    self.receive_records(content_str)
                i.lowSeqno = i.lowSeqno + 1

    def receive_records(self, received_data):
        received_record = Record(data=received_data)
        print("received record:")
        received_record.print()

        # Verify record
        received_record.check_pointer_count(self.num_record_links)
        self.verify_previous_record(received_record)

        # Save record
        record_storage.store_record(
            received_record.get_record_name_str(), received_data)

        self.last_names[self.last_name_tops] = received_record.get_record_name()
        self.last_name_tops = (self.last_name_tops + 1) % len(self.last_names)

        # TODO: get event out of received record and verify it then add it to a set of seen events so users can see it

    # Verify a record by tracing back to the root.
    # TODO: Recursive verification. Right now, this just checks that each of the links is there, not that they're also verified.
    def verify_previous_record(self, record: Record) -> None:
        for ptr in record.get_pointers_from_header():
            if (Name.to_str(ptr) in self.no_prev_records
                    or record_storage.get_record(Name.to_str(ptr)) is None):
                self.waiting_referenced_records.append((Name.to_str(ptr), record.get_record_name_str()))
                self.no_prev_records.add(record.get_record_name_str())

        waiting_list: List[str] = []
        wrr_copy = self.waiting_referenced_records
        self.waiting_referenced_records = []
        for pair in wrr_copy:
            if (pair[0] == record.get_record_name_str()):
                waiting_list.append(pair[1])
                self.no_prev_records.discard(pair[1])
            else:
                self.waiting_referenced_records.append(pair)

        for record_name in waiting_list:
            self.verify_previous_record(record_storage.get_record(record_name))

async def start(args:dict) -> None:
    logger = Logger(args)

def main() -> int:
    args = parse_cmd_args()
    args["node_id"] = Name.to_str(Name.from_str(args["node_id"]))

    SVSyncLogger.config(True if args["verbose"] else False, None, logging.INFO)

    try:
        app.run_forever(after_start=start(args))
    except (FileNotFoundError, ConnectionRefusedError):
        print('Error: could not connect to NFD for SVS.')
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
