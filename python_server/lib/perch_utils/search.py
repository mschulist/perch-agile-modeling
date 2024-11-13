from python_server.lib.db.db import AccountsDB


class PrecomputeSearch:
    def __init__(self, db: AccountsDB):
        self.db = db
