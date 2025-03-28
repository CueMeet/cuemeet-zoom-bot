import logging


class LogConfig:
    def __init__(self):
        self.logger = None
        
    def get_logger(self, logger_name):
        if self.logger is None:
            # Set bellow components to WARNING level
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
            logging.getLogger('selenium').setLevel(logging.WARNING)
            logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('highlight_io').setLevel(logging.WARNING)
            
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)

            self.logger = logger
        
        return self.logger