class NixarError(Exception):

    def __init__(self, error):
        self.code = error['code']
        self.message = error['value']
