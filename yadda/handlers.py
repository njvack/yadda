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

logger = logging.getLogger(__name__)


class ThreadedDicomHandler(threading.Thread):

    def __init__(self, manager, name, timeout):
        super(ThreadedDicomHandler, self).__init__(name=name)
        self.timeout = timeout
        self.manager = manager
        self.notifier = threading.Condition()

    def start(self):
        self._stop = False
        logger.info(
            "%s: waiting for dicoms. Timeout: %s" %
            (self, self.timeout))
        self.on_start()
        super(ThreadedDicomHandler, self).start()

    def on_start(self):
        """
        Synchronous code to run before handling any dicoms.

        This will run before the thread has started (technically, in start())
        so it should ben able to take a while to run without
        dicoms piling up and biting us.

        Override this in subclasses.

        """
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
        Actually finish handling dicoms.

        Override this method in subclasses.

        """
        logger.debug("%s - finishing" % (self))

    def terminate(self):
        with self.notifier:
            self._stop = True
            self.notifier.notify()

    def handle_dicom(self, dcm, *args, **kwargs):
        if not self.is_alive():
            raise RuntimeError("%s got handle_dicom before alive!" % (self))
        with self.notifier:
            self._stop = False
            self.on_handle(dcm, *args, **kwargs)
            self.notifier.notify()

    def on_handle(self, dcm, *args, **kwargs):
        """
        Do the internal handling of the dicom. Override this method in
        subclasses.
        """
        logger.debug("%s - handling dicom" % (self))

    def __str__(self):
        return "%s" % (self.name)
