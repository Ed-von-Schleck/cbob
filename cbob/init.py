import logging
import os
from os.path import join, abspath, isdir

def init():
    cbob_path = abspath(".cbob") + os.sep
    if isdir(".cbob"):
        from cbob.error import CbobError
        raise CbobError("cbob is already initialized in '{}'".format(cbob_path))
    os.makedirs(".cbob")
    logging.info("initialized cbob in '{}'".format(cbob_path))
