# A trust schema for Mnemosyne and some preliminary security code.

import os
from ndn.security import TpmFile, KeychainSqlite3
from ndn.app_support.light_versec import Checker, compile_lvs, lvs_validator

lvs_text = r'''
// Mnemosyne prefix is "/svs/mnemosyne"
#mnemosyne: "svs"/"mnemosyne"
// The trust anchor name is of pattern /svs/mnemosyne/KEY/<key-id>/<issuer>/<cert-id>
#root: #mnemosyne/#KEY
// Records are signed by some logger's key
#record: #mnemosyne/"records"/logger/"RECORD"/#event/ <= #logger
// A logger's key is signed by the root key
#logger: #mnemosyne/"logger"/logger/#KEY <= #root
// Events are signed by some producer's key
#event: producer/#mnemosyne/"log_events"/"data"/data <= #producer
// A producer's key is signed by the root key
#producer: #mnemosyne/"producer"/producer/#KEY <= #root

#KEY: "KEY"/_/_/_
'''

# basedir = os.path.dirname(os.path.abspath("."))
# tpm_path = os.path.join(basedir, 'privKeys')
# pib_path = os.path.join(basedir, 'pib.db')
# keychain = KeychainSqlite3(pib_path, TpmFile(tpm_path))
# trust_anchor = keychain['/svs/mnemosyne'].default_key().default_cert()
# app = NDNApp(keychain=keychain)
# validator = lvs_validator(checker, app, trust_anchor.data)

class Security:
    def __init__(self):
        self.lvs_model = compile_lvs(lvs_text)
        self.checker = Checker(self.lvs_model, {})
    
    def check_sig(self, data_name: str, key_name: str) -> bool:
        return self.checker.check(data_name, key_name)
