import pytest
import yadda
from yadda import managers


class DummyHandler(object):

    def __init__(self, name, manager):
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
    mgr = managers.ThreadedDicomManager(0, str, DummyHandler)
    assert mgr


def test_manager_starts_and_stops():
    mgr = managers.ThreadedDicomManager(0, str, DummyHandler)
    mgr.handle_dicom("foo")
    handler = mgr._series_handlers['foo']
    assert handler
    assert handler.started
    assert handler.handle_count == 1
    mgr.wait_for_handlers()
    assert not handler.started

    with pytest.raises(KeyError):
        handler = mgr._series_handlers['foo']