# coding: utf8
# Part of yadda -- a simple dicom file uploader
#
# Copyright 2014 Board of Regents of the University of Wisconsin System

import pytest
import time
from yadda import handlers


class DummyManager(object):

    def remove_handler(self, h):
        pass


class TestHandler(handlers.ThreadedDicomHandler):
    def __init__(self, timeout, name, manager):
        super(TestHandler, self).__init__(timeout, name, manager)
        self.startered = False
        self.handlered = False
        self.finished = False

    def on_start(self):
        super(TestHandler, self).on_start()
        self.startered = True

    def on_handle(self, dcm):
        super(TestHandler, self).on_handle(dcm)
        self.handlered = True

    def on_finish(self):
        super(TestHandler, self).on_finish()
        self.finished = True


def test_threaded_handler_joins():
    mgr = DummyManager()
    h = TestHandler(0.1, "test", mgr)
    with pytest.raises(RuntimeError):
        h.handle_dicom("foo")
    assert not h.handlered
    h.start()
    assert h.startered
    h.handle_dicom("Foo")
    assert h.handlered
    h.join()
    assert h.finished

def test_threaded_handler_terminates():
    timeout=10
    start = time.clock()
    mgr = DummyManager()
    h = TestHandler(timeout, "test", mgr)
    h.start()
    assert h.startered
    h.terminate()
    h.join()
    assert h.finished
    assert (time.clock() - start) < timeout
    assert not h.handlered



