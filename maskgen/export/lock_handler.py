from maskgen.config import global_config
from multiprocessing import Lock


class LockHandler:
    def __init__(self):
        self.locks = {}

    def new(self, name):
        self.locks[name] = Lock()
        return self.locks[name]

    def get(self, name):
        return self.locks[name] if name in self.locks else None

    def get_all(self):
        return self.locks


def get_lock_handler():
    if "LockHandler" not in global_config:
        global_config["LockHandler"] = LockHandler()
    return global_config["LockHandler"]
