import abc


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def row_factory(cursor, data):
    keys = [col[0] for col in cursor.description]
    d = {k: v for k, v in zip(keys, data)}
    return dotdict(d)

class DatabaseInterface(abc.ABC):
    @abc.abstractmethod
    async def connect(self):
        pass
    
    @abc.abstractmethod
    async def disconnect(self):
        pass
    
    @abc.abstractmethod
    async def query_execute(self, query, params=None):
        pass
