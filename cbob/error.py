class CbobError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class NotInitializedError(CbobError):
    def __init__(self):
        super().__init__("Project not initialized.\nType 'cbob init' to initialize cbob here.")

class TargetDoesntExistError(CbobError):
    def __init__(self, target_name):
        super().__init__("Target '{}' doesn't exist.\nType 'cbob info --targets' to show existing targets.".format(target_name))

class SubprojectDoesntExistError(CbobError):
    def __init__(self, subproject_name):
        super().__init__("Subproject '{}' doesn't exist.\nType 'cbob info --subprojects' to show existing targets.".format(subproject_name))

class NotConfiguredError(CbobError):
    def __init__(self, target_name):
        super().__init__("Target '{0}' is not configured.\nType 'cbob configure {0}' to configure target.".format(target_name))

class OptionDoesntExistError(CbobError):
    def __init__(self, target_name, option_name):
        super().__init__("Target '{0}' doesn't have an option named '{1}'.\nType 'cbob options info --target {0}' to show existing options.".format(target_name, option_name))

class ChoiceDoesntExistError(CbobError):
    def __init__(self, target_name, option_name, choice_name):
        super().__init__("Option {0} of target '{1}' doesn't have a choice named '{2}'.\nType 'cbob options list --target {1} {0} list' to show existing options.".format(option_name, target_name, choice_name))

