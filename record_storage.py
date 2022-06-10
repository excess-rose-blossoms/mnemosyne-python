import dbm
from record import Record

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
