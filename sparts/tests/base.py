# Copyright (c) 2014, Facebook, Inc.  All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import logging
import os.path

from sparts.vservice import VService


# Import a Skip exception class that works with both pytest and unittest2
try:
    from _pytest.runner import Skipped
    class Skip(Skipped, unittest.SkipTest):
        pass

except ImportError:
    class Skip(unittest.SkipTest):
        pass


# Base test case for all sparts jonx
class BaseSpartsTestCase(unittest.TestCase):
    def assertNotNone(self, o, msg=''):
        self.assertTrue(o is not None, msg)

    def assertEmpty(self, arr, msg=''):
        return self.assertEquals(len(arr), 0, msg)

    def assertNotEmpty(self, o, msg=''):
        self.assertTrue(len(o) > 0, msg)

    def assertExists(self, path, msg=''):
        self.assertTrue(os.path.exists(path), msg)

    def assertNotExists(self, path, msg=''):
        self.assertFalse(os.path.exists(path), msg)

    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger('sparts.%s' % cls.__name__)
        super(BaseSpartsTestCase, cls).setUpClass()

    def setUp(self):
        if not hasattr(unittest.TestCase, 'setUpClass'):
            cls = self.__class__
            if not hasattr(cls, '_unittest2_setup'):
                cls.setUpClass()
                cls._unittest2_setup = 0
            cls._unittest2_setup += 1

    def tearDown(self):
        if not hasattr(unittest.TestCase, 'tearDownClass'):
            cls = self.__class__
            if not hasattr(cls, '_unittest2_setup'):
                cls._unittest2_setup = 0
            else:
                cls._unittest2_setup -= 1
            if cls._unittest2_setup == 0:
                cls.tearDownClass()

    def assertContains(self, item, arr, msg=''):
        return self.assertIn(item, arr, msg)

    @property
    def mock(self, *args, **kwargs):
        try:
            import mock
            return mock
        except ImportError:
            raise Skip("the mock module is required to run this test")


class ServiceTestCase(BaseSpartsTestCase):
    def getServiceClass(self):
        return VService

    def setUp(self):
        super(ServiceTestCase, self).setUp()

        TestService = self.getServiceClass()
        TestService.test = self

        ap = TestService._buildArgumentParser()
        ns = ap.parse_args(['--level', 'DEBUG'])
        self.service = TestService(ns)
        self.runloop = self.service.startBG()

    def tearDown(self):
        self.service.stop()
        self.runloop.join()
        super(ServiceTestCase, self).tearDown()


class MultiTaskTestCase(ServiceTestCase):
    TASKS = []

    def requireTask(self, task_name):
        self.assertNotNone(self.service)
        return self.service.requireTask(task_name)

    def getServiceClass(self):
        self.assertNotEmpty(self.TASKS)
        class TestService(VService):
            TASKS=self.TASKS
        return TestService

    def setUp(self):
        super(MultiTaskTestCase, self).setUp()
        for t in self.TASKS:
            self.service.requireTask(t.__name__)


class SingleTaskTestCase(MultiTaskTestCase):
    TASK = None

    @classmethod
    def setUpClass(cls):
        super(SingleTaskTestCase, cls).setUpClass()
        if cls.TASK:
            cls.TASKS = [cls.TASK]

    def setUp(self):
        self.assertNotNone(self.TASK)
        super(SingleTaskTestCase, self).setUp()
        self.task = self.service.requireTask(self.TASK.__name__)
