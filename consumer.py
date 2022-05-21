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
        print(f'CONSUMER STARTED! | GROUP PREFIX: {self.group_prefix} | NODE ID: {self.args["node_id"]} |')
    
    async def run(self) -> None:
        return
    
    def missing_callback(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.on_missing_data(missing_list))
    
    async def on_missing_data(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str:
                    self.records_list.append(content_str.decode())
                    print(self.records_list)
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
