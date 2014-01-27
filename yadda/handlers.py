# coding: utf8
# Part of yadda -- a simple dicom file uploader
#
# Copyright 2014 Board of Regents of the University of Wisconsin System

"""
Handlers are responsible for taking a dicoms and doing something with them.
In general, you'll want to subclass ThreadedDicomHandler and override
the on_start(), on_handle(), and on_finish() methods in your subclass.
"""

import threading
import logging
import os

logger = logging.getLogger(__name__)


class ThreadedDicomHandler(threading.Thread):

    def __init__(self, timeout, name, manager):
        super(ThreadedDicomHandler, self).__init__(name=name)
        self.timeout = timeout
        self.manager = manager
        self.notifier = threading.Condition()

    def start(self):
        self._stop = False
        logger.info("%s: waiting for dicoms. Timeout: %s" %
            (self, self.timeout))
        self.on_start()
        super(ThreadedDicomHandler, self).start()

    def on_start(self):
        logger.debug("{0} on_start".format(self))

    def run(self):
        logger.debug("%s - running" % (self))
        with self.notifier:
            while not self._stop:
                self._stop = True
                self.notifier.wait(self.timeout)
            self.on_finish()
            self.manager.remove_handler(self)
        logger.debug("%s: successfully shut down" % (self))

    def on_finish(self):
        """
        Actually finish handling dicoms. Override this method in subclasses.
        """
        logger.debug("%s - finishing" % (self))

    def terminate(self):
        with self.notifier:
            self._stop = True
            self.notifier.notify()

    def handle_dicom(self, dcm):
        if not self.is_alive():
            raise RuntimeError("%s got handle_dicom before alive!" % (self))
        with self.notifier:
            self._stop = False
            self.on_handle(dcm)
            self.notifier.notify()

    def on_handle(self, dcm):
        """
        Do the internal handling of the dicom. Override this method in
        subclasses.
        """
        logger.debug("%s - handling dicom" % (self))

    def __str__(self):
        return "%s" % (self.name)


if __name__ == '__main__':
    # Easy testing test!
    import sys
    import glob
    import file_dicom
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)

    timeout = int(sys.argv[1])
    in_dir = sys.argv[2]

    def key_fx(dcm):
        return "%s-%s-%s" % (dcm.StudyDate, dcm.StudyID, dcm.SeriesNumber)

    def handler_factory(example_dicom, manager):
        name = key_fx(example_dicom)
        return DicomSeriesHandler(timeout, name, manager)

    mgr = ThreadedDicomManager(timeout, key_fx, handler_factory)
    for f in glob.iglob("%s/*" % (in_dir)):
        dcm = file_dicom.read_file(f)
        mgr.handle_dicom(dcm)
    mgr.wait_for_handlers()
