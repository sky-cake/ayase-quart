from .baseprovider import BaseSearch, SearchQuery


class TypesenseSearch(BaseSearch):
    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
