# coding: utf8
# Part of yadda -- a simple dicom file uploader
#
# Copyright 2014 Board of Regents of the University of Wisconsin System

import pytest
from yadda import managers


class DummyManager(managers.ThreadedDicomManager):

    def handler_key(self, obj):
        return obj

    def build_handler(self, dcm):
        return DummyHandler(self, str(dcm), 0)


class DummyHandler(object):

    def __init__(self, manager, name, timeout):
        self.name = name
        self.manager = manager
        self.handle_count = 0
        self.started = False

    def start(self):
        self.started = True

    def run(self):
        pass

    def handle_dicom(self, dicom):
        self.handle_count += 1

    def join(self, seconds):
        self.started = False
        self.manager.remove_handler(self)


def test_creating_manager():
    mgr = DummyManager(0)
    assert mgr


def test_manager_starts_and_stops():
    mgr = DummyManager(0)
    mgr.handle_dicom("foo")
    handler = mgr._series_handlers['foo']
    assert handler
    assert handler.started
    assert handler.handle_count == 1
    mgr.wait_for_handlers()
    assert not handler.started

    with pytest.raises(KeyError):
        handler = mgr._series_handlers['foo']
