import cffi
import logging

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

class NixarLogging(object):
    # 0 is off
    # 1 is ERR
    # 2 is warn
    # 3 is info
    # 4 is debug
    # 5 and more is trace
    def log(self, level, message):
        ffi = cffi.FFI()
        try:
            message = ffi.string(message).decode('utf-8')
            message = 'libnixar-core ' + message
            if level == 1:
                logging.error(message)
            elif level == 2:
                logging.warning(message)
            elif level == 3:
                logging.info(message)
            elif level == 4:
                logging.debug(message)
            elif level == 5:
                logging.debug(message)
        except Exception as e:
            logging.error("logging fail for level {}, message {}".format(level,e))
