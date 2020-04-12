import os, time, glob

__all__ = [ os.path.basename(f)[:-3] for f in glob.glob(os.path.dirname(__file__)+"/*.py") if os.path.basename(f)[0] != '_']

for x in __all__:
    __import__(x, locals(), globals(), level=1)

class Timer(object):
    """
    context manager used to time the operations
    """

    def __init__(self, logger=None, step = 'undef.', operation = 'undef.'):
        """
        log: is a logging istance to print the correct log format
        if nothing is passed, root is used
        """
        if logger is None: self.logger = logging
        else: self.logger = logger
        self.step = step
        self.operation = operation

    def __enter__(self):
        self.logger.info("--> Starting \'" + self.step + "\' step (operation: " + self.operation + ").")
        self.start = time.time()
        self.startcpu = time.clock()

    def __exit__(self, exit_type, value, tb):

        # if not an error
        if exit_type is None:
            self.logger.info("Time for %s step: %i s (cpu: %i s)." % ( self.step, ( time.time() - self.start), (time.clock() - self.startcpu) ))
