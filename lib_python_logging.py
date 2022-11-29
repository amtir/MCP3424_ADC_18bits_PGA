import logging
import sys
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

'''
Level	      When it’s used
DEBUG	      Detailed information, typically of interest only when diagnosing problems.
INFO	      Confirmation that things are working as expected.
WARNING	    An indication that something unexpected happened, or indicative of some problem in the near future (e.g. ‘disk space low’). The software is still working as expected.
ERROR	      Due to a more serious problem, the software has not been able to perform some function.
CRITICAL	  A serious error, indicating that the program itself may be unable to continue running.

'''

FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(filename)s — %(funcName)s — %(lineno)s  — %(threadName)s — %(message)s")
#LOG_FILE = "/home/drinkotec/pulseinside/logs/pulseinside.log"
LOG_FILE = "/var/log/drinkotec/drinkotec.log"


def get_console_handler():
   console_handler = logging.StreamHandler(sys.stdout)
   console_handler.setFormatter(FORMATTER)
   return console_handler

def get_file_handler():
   #file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
   file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=3 )
   file_handler.setFormatter(FORMATTER)
   return file_handler

def get_logger(logger_name):
   logger = logging.getLogger(logger_name)
   logger.setLevel(logging.DEBUG) # better to have too much log than not enough
   logger.addHandler(get_console_handler())
   logger.addHandler(get_file_handler())
   # with this pattern, it's rarely necessary to propagate the error up to parent
   logger.propagate = False
   return logger


