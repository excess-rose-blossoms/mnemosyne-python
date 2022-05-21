from ndn.app import NDNApp
from ndn.svs import SVSync
from ndn.encoding import *
from ndn.security import Keychain, Validator

class MnemosyneDagSync:

    # Config should look like:
    # {
    #     preceding_record_num: int,  # num of preceding records each record should reference (we're doing 2)
    #     num_genesis_blocks: int,     # the number of genesis blocks we need
    #     ancestor_fetch_timeout: time in ms,  # the timeout for fetching ancestor records
    #     group_prefix: Name,        # the multicast prefix under which an Interest can reach all peers in the multicast group 
    #     interface_prefix: Name,    # the interface pub/sub prefix, under which a publication can reach all Mnemosyne loggers
    #     node_prefix: Name,         # Producer's unique name prefix, under which an Interest can reach the producer
    #     database_path: string      # The path to the database (might not need)
    # }
    def __init__(self, config:dict, keychain:Keychain, network:NDNApp, record_validator:Validator) -> None:
        self.config = config
        self.keychain = keychain
        self.backend = config.database_path # won't need this for now
        self.record_validator = record_validator
        # API: SVSync(app:NDNApp (the face), groupPrefix:Name, nodePrefix:Name, UpdateCallback:Callable, storage:Optional[Storage]=None, securityOptions:Optional[SecurityOptions]=None)
        # note - both names should be FormalName (as opposed to NonStrictName) 
        self.svsync:SVSync = SVSync(
            network, config.group_prefix, config.node_prefix, self.on_update,
            self.getSecurityOption(
                keychain, record_validator, config.node_prefix))
        self.last_name_tops = 0 # TODO: change this based on our method of keeping track of tails
        self.last_names = [] # TODO:  change this based on our method of keeping track of tails

        if (config.num_genesis_blocks < config.preceding_record_num or config.preceding_record_num <= 1):
            print("Error! Bad config")
            # TODO: Throw error (NDN_THROW?)
            return

        # Make genesis blocks.
        # The first real block needs previous blocks to link to.
        # Note - we'll have to redo all the code in this for loop for our record structure.
        for i in range(self.config.num_genesis_blocks):
            # TODO: figure out python-ndn equivalent of Data
            # TODO: implement GenesisRecord and get_record_name()
            # note - GenesisRecord is a subclass of record used for the genesis blocks
            genesis_record = GenesisRecord(i)
            data = Data(genesis_record.get_record_name())
            # MakeEmptyBlock provided by ndn-cxx/encoding/block-helpers.cpp
            # TODO: figure out the python-ndn equivalent (TlvModel?)
            content_block = makeEmptyBlock(130)
            # TODO: implement wire_encode (in Record class)
            genesis_record.wire_encode(content_block)
            # https://named-data.net/doc/ndn-cxx/0.6.1/doxygen/d4/d83/classndn_1_1Data.html#a12b67c635114f0caae2ba467be81916e
            data.setContent(content_block)
            # TODO: look at python-ndn Keychain API
            self.keychain.sign()
            genesis_record.data = data
            # TODO: replace with whatever code stores a new record
            self.backend.put_record()
            # TODO: implement get_record_full_name
            self.last_names.append(genesis_record.get_record_full_name())

        print(f'SVS count client started | {self.config.group_prefix} - {self.config.node_prefix} |')

            


# Sample code
class Program:
        
    async def run(self) -> None:
        num:int = 0
        while 1:
            num = num+1
            try:
                print("YOU: "+str(num))
                self.svs.publishData(str(num).encode())
            except KeyboardInterrupt:
                sys.exit()
            await aio.sleep(self.args["interval"])
    def on_update(self, missing_list:List[MissingData]) -> None:
        aio.ensure_future(self.on_missing_data(missing_list))
    async def on_missing_data(self, missing_list:List[MissingData]) -> None:
        for i in missing_list:
            while i.lowSeqno <= i.highSeqno:
                content_str:Optional[bytes] = await self.svs.fetchData(Name.from_str(i.nid), i.lowSeqno, 2)
                if content_str:
                    output_str:str = i.nid + ": " + content_str.decode()
                    sys.stdout.write("\033[K")
                    sys.stdout.flush()
                    print(output_str)
                i.lowSeqno = i.lowSeqno + 1
