import logging

def initLogging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='{asctime} {levelname:8} {message}', # 2017-05-25 00:58:28 INFO     An info message
        # datefmt="{0:04d}-{1:02d}-{2:02d} {3:02d}:{4:02d}:{5:02d} -",
        style="{"
    )

# SAMPLE USAGE:
#
# import logging, logger
# logger.initLogger()
#
# logging.info('An info message')
# logging.debug('A debug message')

# LOGGING LEVELS:
#
# CRITICAL
# ERROR
# WARNING
# INFO
# DEBUG
# NOTSET