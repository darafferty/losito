# -*- coding: utf-8 -*-
"""
Libraries for operations
"""
import os, multiprocessing, sys
from .lib_io import logger

class Scheduler():
    def __init__(self, qsub = None, maxThreads = None, max_processors = None, log_dir = 'logs', dry = False):
        """
        qsub:           if true call a shell script which call qsub and then wait
                        for the process to finish before returning
        maxThreads:    max number of parallel processes
        dry:            don't schedule job
        max_processors: max number of processors in a node (ignored if qsub=False)
        """
        self.cluster = self.get_cluster()
        self.log_dir = log_dir
        self.qsub    = qsub
        # if qsub/max_thread/max_processors not set, guess from the cluster
        # if they are set, double check number are reasonable
        if (self.qsub == None):
            if (self.cluster == "Hamburg"):
                self.qsub = True
            else:
                self.qsub = False
        else:
            if self.qsub == False and self.cluster == "Hamburg":
                logger.warning('qsub is set to false and cluster is Hamburg.')
            elif (self.qsub == True and (self.cluster in ["Leiden", "CEP3", "Hamburg_fat"])):
                logger.critical('qsub set to %s and cluster is %s.' % (str(qsub), self.cluster))
                sys.exit(1)

        if (maxThreads == None):
            if   (self.cluster == "Hamburg"):
                self.maxThreads = 32
            else:
                self.maxThreads = multiprocessing.cpu_count()
        else:
            self.maxThreads = maxThreads

        if (max_processors == None or max_processors == 0):
            if   (self.cluster == "Hamburg"):
                self.max_processors = 6
            else:
                self.max_processors = multiprocessing.cpu_count()
        else:
            self.max_processors = max_processors

        self.dry = dry
        logger.info("Scheduler initialised for cluster " + self.cluster + " (maxThreads: " + str(self.maxThreads) + ", qsub (multinode): " +
                    str(self.qsub) + ", max_processors: " + str(self.max_processors) + ").")

        self.action_list = []
        self.log_list    = [] # list of 2-tuples of the type: (log filename, type of action)


    def get_cluster(self):
        """
        Find in which computing cluster the pipeline is running
        """
        import socket
        hostname = socket.gethostname()
        dnsdomain = socket.getfqdn().split('.', 1)[1]
        if (hostname in ['node31','node32','node33','node34','node35']):
            return "Hamburg_fat"
        elif dnsdomain == 'lofar.gpu.cluster':
              return "Hamburg"
        elif ('leidenuniv' in hostname):
            return "Leiden"
        elif (hostname[0 : 3] == 'lof'):
            return "CEP3"
        else:
            logger.warning('Hostname %s unknown.' % hostname)
            return "Unknown"


    def add(self, cmd = '', log = '', logAppend = True, commandType = '', processors = None):
        """
        Add a command to the scheduler list
        cmd:         the command to run
        log:         log file name that can be checked at the end
        logAppend:  if True append, otherwise replace
        commandType: can be a list of known command types as "BBS", "DPPP", ...
        processors:  number of processors to use, can be "max" to automatically use max number of processors per node
        """
        if (log != ''):
            log = self.log_dir + '/' + log

            if (logAppend):
                cmd += " >> "
            else:
                cmd += " > "
            cmd += log + " 2>&1"

        # if running wsclean add the string
        if commandType == 'wsclean':
            logger.debug('Running wsclean: %s' % cmd)
        elif commandType == 'DPPP':
            logger.debug('Running DPPP: %s' % cmd)
        elif commandType == 'python':
            logger.debug('Running python: %s' % cmd)

        if (processors != None and processors == 'max'):
            processors = self.max_processors

        if self.qsub:
            # if number of processors not specified, try to find automatically
            if (processors == None):
                processors = 1 # default use single CPU
                # if ("DPPP" == cmd[ : 4]):
                #     processors = 1
                # if ("wsclean" == cmd[ : 7]):
                #     processors = self.max_processors
            if (processors > self.max_processors):
                processors = self.max_processors

            self.action_list.append([str(processors), '\'' + cmd + '\''])
        else:
            self.action_list.append(cmd)

        if (log != ""):
            self.log_list.append((log, commandType))


    def run(self, check = False, maxThreads = None):
        """
        If 'check' is True, a check is done on every log in 'self.log_list'.
        If max_thread != None, then it overrides the global values, useful for special commands that need a lower number of threads.
        """
        from threading import Thread
        from queue import Queue
        import subprocess
        import gc

        def worker(queue):
            for cmd in iter(queue.get, None):
                if self.qsub and self.cluster == "Hamburg":
                    cmd = 'salloc --job-name LoSiTo --time=24:00:00 --nodes=1 --tasks-per-node='+cmd[0]+ \
                          ' /usr/bin/srun --ntasks=1 --nodes=1 --preserve-env \''+cmd[1]+'\''
                gc.collect()
                subprocess.call(cmd, shell = True)

        # limit threads only when qsub doesn't do it
        if (maxThreads == None):
            maxThreads_run = self.maxThreads
        else:
            maxThreads_run = min(maxThreads, self.maxThreads)

        q       = Queue()
        threads = [Thread(target = worker, args=(q,)) for _ in range(maxThreads_run)]

        for i, t in enumerate(threads): # start workers
            t.daemon = True
            t.start()

        for action in self.action_list:
            if (self.dry):
                continue # don't schedule if dry run
            q.put_nowait(action)
        for _ in threads:
            q.put(None) # signal no more commands
        for t in threads:
            t.join()

        # check outcomes on logs
        if (check):
            for log, commandType in self.log_list:
                self.check_run(log, commandType)

        # reset list of commands
        self.action_list = []
        self.log_list    = []


    def check_run(self, log = "", commandType = ""):
        """
        Produce a warning if a command didn't close the log properly i.e. it crashed
        NOTE: grep, -L inverse match, -l return only filename
        """
        import subprocess

        if (not os.path.exists(log)):
            logger.warning("No log file found to check results: " + log)
            return 1

        if (commandType == "DPPP"):
            out = subprocess.check_output('grep -L "Finishing processing" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -l "Exception" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -l "**** uncaught exception ****" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -l "error" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -l "misspelled" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)

        elif (commandType == "CASA"):
            out = subprocess.check_output('grep -l "[a-z]Error" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -l "An error occurred running" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -l "\*\*\* Error \*\*\*" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)

        elif (commandType == "wsclean"):
            out = subprocess.check_output('grep -l "exception occured" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -l "Segmentation fault" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -L "Cleaning up temporary files..." '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)

        elif (commandType == "python"):
            out = subprocess.check_output('grep -l "Traceback (most recent call last):" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -i -l \'(?=^((?!error000).)*$).*Error.*\' '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)
            out += subprocess.check_output('grep -i -l "Critical" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)

        elif (commandType == "general"):
            out = subprocess.check_output('grep -l -i "error" '+log+' ; exit 0', shell = True, stderr = subprocess.STDOUT)

        else:
            logger.warning("Unknown command type for log checking: '" + commandType + "'")
            return 1

        if out != b'':
            out = out.split(b'\n')[0].decode()
            logger.error(commandType+' run problem on:\n'+out)
            return 1

        return 0


class multiprocManager(object):

    class multiThread(multiprocessing.Process):
        """
        This class is a working thread which load parameters from a queue and
        return in the output queue
        """

        def __init__(self, inQueue, outQueue, funct):
            multiprocessing.Process.__init__(self)
            self.inQueue = inQueue
            self.outQueue = outQueue
            self.funct = funct

        def run(self):

            while True:
                parms = self.inQueue.get()

                # poison pill
                if parms is None:
                    self.inQueue.task_done()
                    break

                self.funct(*parms, outQueue=self.outQueue)
                self.inQueue.task_done()

    def __init__(self, procs=0, funct=None):
        """
        Manager for multiprocessing
        procs: number of processors, if 0 use all available
        funct: function to parallelize / note that the last parameter of this function must be the outQueue
        and it will be linked to the output queue
        """
        if procs == 0:
            procs = multiprocessing.cpu_count()
        self.procs = procs
        self._threads = []
        self.inQueue = multiprocessing.JoinableQueue()
        manager = multiprocessing.Manager()
        self.outQueue = manager.Queue()
        self.runs = 0

        logger.debug('Spawning %i threads...' % self.procs)
        for proc in range(self.procs):
            t = self.multiThread(self.inQueue, self.outQueue, funct)
            self._threads.append(t)
            t.start()

    def put(self, args):
        """
        Parameters to give to the next jobs sent into queue
        """
        self.inQueue.put(args)
        self.runs += 1

    def get(self):
        """
        Return all the results as an iterator
        """
        # NOTE: do not use queue.empty() check which is unreliable
        # https://docs.python.org/2/library/multiprocessing.html
        for run in range(self.runs):
            yield self.outQueue.get()

    def wait(self):
        """
        Send poison pills to jobs and wait for them to finish
        The join() should kill all the processes
        """
        for t in self._threads:
            self.inQueue.put(None)

        # wait for all jobs to finish
        self.inQueue.join()
