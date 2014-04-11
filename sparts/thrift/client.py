# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
"""Helpers for easily creating thrift clients"""
from __future__ import absolute_import

from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TFramedTransport
from thrift.protocol.TBinaryProtocol import TBinaryProtocol

from functools import partial


class ThriftClient(object):
    """Base Class for easy interfacing with thrift services.

    `ThriftClient` can be used directly, or subclassed.  If subclassed,
    you can override a variety of attributes in order to make instantiation
    more natural:

        MODULE - The generated thrift module.  Should include Iface and Client
        HOST - A default host to connect to.  Possibly a vip.
        PORT - A default port to connect to.
        TRANSPORT_CLASS - By default, `TFramedTransport`
        PROTOCOL_CLASS - By default, `TBinaryProtocol`
        CONNECT_TIMEOUT - By default, 3.0 seconds

    Instantiation should be done via the class methods, `for_hostport()`, and
    `for_localhost()` as appropriate.  These helpers more aggressively require
    `port` and `host` arguments as appropriate.  Generic construction arguments
    override the class attribute defaults:

        `module` - Generated thrift module.
        `host` - IP address to connect to.
        `port` - Port to connect to.
        `connect_Timeout` - Socket connection timeout
        `transport_class` - Thrift transport class
        `protocol_class` - Thrift protocol class

    Additional features are configurable with other arguments:

        `lazy` - Default: True, connect on first RPC invocation, instead of
                 at construction time.

    Connections are made lazily, when the first rpc invocation occurs, so you
    do need to wrap client instantiation with a try-catch.
    """
    MODULE = None
    HOST = None
    PORT = None
    TRANSPORT_CLASS = TFramedTransport
    PROTOCOL_CLASS = TBinaryProtocol
    CONNECT_TIMEOUT = 3.0

    @classmethod
    def for_hostport(cls, host=None, port=None, **kwargs):
        assert host or cls.HOST, "You must define a host!"
        assert port or cls.PORT, "You must define a port!"
        return cls(host=host, port=port, **kwargs)

    @classmethod
    def for_localhost(cls, port=None, **kwargs):
        assert port or cls.PORT, "You must define a port!"
        return cls(host='127.0.0.1', port=port, **kwargs)

    def _initAttribute(self, name, value, default):
        if value is None:
            value = default
        setattr(self, name, value)

    def __init__(self, host=None, port=None, module=None, lazy=True,
                 connect_timeout=None, transport_class=None,
                 protocol_class=None):

        self._initAttribute('host', host, self.HOST)
        self._initAttribute('port', port, self.PORT)
        self._initAttribute('module', module, self.MODULE)
        self._initAttribute('connect_timeout', connect_timeout,
                            self.CONNECT_TIMEOUT)
        self._initAttribute('transport_class', transport_class,
                            self.TRANSPORT_CLASS)
        self._initAttribute('protocol_class', protocol_class,
                            self.PROTOCOL_CLASS)
        self.lazy = lazy

        assert self.module is not None, "You must define a thrift module!"

        if self.lazy:
            self._client = None
        else:
            self._connect()

    def _connect(self):
        # TODO: Add some kind of support for HTTP or SSLSocket
        self._socket = TSocket(self.host, self.port)
        self._socket.setTimeout(int(self.connect_timeout * 1000))
        self._transport = self.transport_class(self._socket)
        self._protocol = self.protocol_class(self._transport)
        self._client = self.module.Client(self._protocol)
        self._transport.open()

    def _lazyCall(self, name, *args, **kwargs):
        if self._client is None:
            self._connect()
        # TODO: Automatically connect on timed out connections
        return getattr(self._client, name)(*args, **kwargs)

    def __getattr__(self, name):
        getattr(self.module.Client, name)
        return partial(self._lazyCall, name)
