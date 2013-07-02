class CbobError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class NotInitializedError(CbobError):
    def __init__(self):
        super().init(self, "project not initialized")
