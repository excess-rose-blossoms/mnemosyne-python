import asyncio as aio
import logging
import sys
from argparse import ArgumentParser, SUPPRESS
from typing import List, Optional
# NDN Imports
from ndn.app import NDNApp
from ndn.encoding import Name
# Custom Imports
sys.path.insert(0,'.')
from src.ndn.svs import SVSync, SVSyncLogger, MissingData

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

class Program:
    def __init__(self, args:dict) -> None:
        self.args = args
        self.group_prefix = "/svs/log_events"
        self.svs:SVSync = SVSync(app, Name.from_str(self.group_prefix), Name.from_str(self.args["node_id"]), self.missing_callback)
        self.records_list = []
        self.tails_list = []
        print(f'CONSUMER STARTED! | GROUP PREFIX: {self.group_prefix} | NODE ID: {self.args["node_id"]} |')
    
    async def run(self) -> None:
        return

    # Given a log event, create and return an NDN record packet.
    # TODO: This is a temporary implementation. Should actually convert the stuff to packets
    def create_record(self, log_event, record_1, record_2):
        return {"log":log_event, "r1": record_1, "r2": record_2}
    
    # Takes care of the behavior of storing the relevant record to the tails and records lists.
    def store_record(self, content_str):
        record_1 = self.tails_list.pop()["log"] if (len(self.tails_list) > 0) else None
        record_2 = self.tails_list.pop()["log"] if (len(self.tails_list) > 0) else None
        new_record = self.create_record(content_str.decode(), record_1, record_2)
        self.records_list.append(new_record)
        self.tails_list.append(new_record)
        print("------------")
        print("added log event " + content_str.decode())
        print("record_list: " + str(self.records_list))
        print("tails_list: " + str(self.tails_list))
        print("------------")

    def missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.on_missing_data(missing_list))

    async def on_missing_data(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str:
                    if (content_str and (int(content_str.decode()) % 2 == 0)):
                        self.store_record(content_str)
                i.lowSeqno = i.lowSeqno + 1

async def start(args:dict) -> None:
    prog = Program(args)
    await prog.run()

def main() -> int:
    args = parse_cmd_args()
    args["node_id"] = Name.to_str(Name.from_str(args["node_id"]))

    SVSyncLogger.config(True if args["verbose"] else False, None, logging.INFO)

    try:
        app.run_forever(after_start=start(args))
    except (FileNotFoundError, ConnectionRefusedError):
        print('Error: could not connect to NFD for SVS.')

    return 0

if __name__ == "__main__":
    sys.exit(main())
