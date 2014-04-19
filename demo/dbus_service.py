# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
from __future__ import absolute_import

from sparts.vservice import VService
from sparts.tasks.dbus import DBusMainLoopTask, DBusServiceTask
from sparts.tasks.fb303 import FB303HandlerTask


class MyDBusServiceTask(DBusServiceTask):
    BUS_NAME = 'org.sparts.DBusDemo'

class MyDBusService(VService):
    TASKS=[DBusMainLoopTask, MyDBusServiceTask, FB303HandlerTask]


if __name__ == '__main__':
    MyDBusService.initFromCLI()
