import os.path

def init():
    cbob_path = os.path.abspath(".cbob") + os.sep
    is_initialized = os.path.isdir(".cbob")
    if is_initialized:
        print("ERROR: cbob is already initialized in", cbob_path)
        exit(1)
    os.makedirs(".cbob/targets")
    print("Initialized cbob in", cbob_path)
