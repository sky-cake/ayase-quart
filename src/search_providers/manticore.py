from .baseprovider import BaseSearch, SearchQuery


class ManticoreSearch(BaseSearch):
    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
