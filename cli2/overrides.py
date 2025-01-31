class Overrides(dict):
    """
    Lazy overrides dict
    """
    def __getitem__(self, key):
        if key not in self:
            self[key] = dict()
        return super().__getitem__(key)
