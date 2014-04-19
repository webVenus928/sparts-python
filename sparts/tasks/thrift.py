# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
"""thrift-related helper tasks"""
from __future__ import absolute_import

from ..vtask import VTask

from sparts.sparts import option
from thrift.server.TNonblockingServer import TNonblockingServer
from thrift.transport.TSocket import TServerSocket

import time


class ThriftHandlerTask(VTask):
    """A loopless task that handles thrift requests.

    You will need to subclass this task, set MODULE, and implement the
    necessary methods in order for requests to be mapped here."""
    LOOPLESS = True
    MODULE = None

    _processor = None

    def initTask(self):
        super(ThriftHandlerTask, self).initTask()
        assert self.MODULE is not None

    def _makeProcessor(self):
        return self.MODULE.Processor(self)

    @property
    def processor(self):
        if self._processor is None:
            self._processor = self._makeProcessor()
        return self._processor


class ThriftServerTask(VTask):
    MODULE = None

    def initTask(self):
        super(ThriftServerTask, self).initTask()
        processors = self._findProcessors()
        assert len(processors) > 0, "No processors found for %s" % (self.MODULE)
        assert len(processors) == 1, "Too many processors found for %s" % \
                (self.MODULE)
        self.processorTask = processors[0]

    @property
    def processor(self):
        return self.processorTask.processor

    def _checkTaskModule(self, task):
        """Returns True if `task` implements the appropriate MODULE Iface"""
        # Skip non-ThriftHandlerTasks
        if not isinstance(task, ThriftHandlerTask):
            return False

        # If self.MODULE is None, then connect *any* ThriftHandlerTask
        if self.MODULE is None:
            return True

        iface = self.MODULE.Iface
        # Verify task has all the Iface methods.
        for method_name in dir(iface):
            method = getattr(iface, method_name)

            # Skip field attributes
            if not callable(method):
                continue

            # Check for this method on the handler task
            handler_method = getattr(task, method_name, None)
            if handler_method is None:
                self.logger.debug("Skipping Task %s (missing method %s)",
                                  task.name, method_name)
                return False

            # And make sure that attribute is actually callable
            if not callable(handler_method):
                self.logger.debug("Skipping Task %s (%s not callable)",
                                  task.name, method_name)
                return False

        # If all the methods are there, the shoe fits.
        return True

    def _findProcessors(self):
        """Returns all processors that match this tasks' MODULE"""
        processors = []
        for task in self.service.tasks:
            if self._checkTaskModule(task):
                processors.append(task)
        return processors


class NBServerTask(ThriftServerTask):
    """Spin up a thrift TNonblockingServer in a sparts worker thread"""
    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 0
    OPT_PREFIX = 'thrift'

    bound_host = bound_port = None

    host = option(default=lambda cls: cls.DEFAULT_HOST, metavar='HOST',
                  help='Address to bind server to [%(default)s]')
    port = option(default=lambda cls: cls.DEFAULT_PORT,
                  type=int, metavar='PORT',
                  help='Port to run server on [%(default)s]')
    num_threads = option(name='threads', default=10, type=int, metavar='N',
                         help='Server Worker Threads [%(default)s]')

    def initTask(self):
        """Overridden to bind sockets, etc"""
        super(NBServerTask, self).initTask()

        self._stopped = False
        self.socket = TServerSocket(self.host, self.port)
        self.server = TNonblockingServer(self.processor, self.socket,
                                         threads=self.num_threads)
        self.server.prepare()
        self.bound_host, self.bound_port = \
            self.server.socket.handle.getsockname()
        self.logger.info("%s Server Started on %s:%s",
                         self.name, self.bound_host, self.bound_port)

    def stop(self):
        """Overridden to tell the thrift server to shutdown asynchronously"""
        self.server.stop()
        self.server.close()
        self._stopped = True

    def _runloop(self):
        """Overridden to execute TNonblockingServer's main loop"""
        while not self.server._stop:
            self.server.serve()
        while not self._stopped:
            time.sleep(0.1)
