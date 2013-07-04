class CbobError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class NotInitializedError(CbobError):
    def __init__(self):
        super().__init__("project not initialized.\nType 'cbob init' to initialize cbob here.")

class TargetDoesntExistError(CbobError):
    def __init__(self, target_name):
        super().__init__("target '{}' doesn't exist.\nType 'cbob info --targets' to show existing targets.".format(target_name))

class SubprojectDoesntExistError(CbobError):
    def __init__(self, subproject_name):
        super().__init__("subproject '{}' doesn't exist.\nType 'cbob info --subprojects' to show existing targets.".format(subproject_name))
