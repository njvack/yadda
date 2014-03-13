# coding: utf8
# Part of yadda -- a simple dicom file uploader
#
# Copyright 2014 Board of Regents of the University of Wisconsin System

"""
Managers manage a pool of handlers, taking care of creation and destruction
as well as handing off incoming files to the appropriate one.
"""

import threading
import logging

logger = logging.getLogger(__name__)


class ThreadedDicomManager(object):
    """
    Superclass for dicom managers -- the things that will get dicoms,
    build handlers for them, and pass the dicoms on to them.

    """

    def __init__(self, timeout):
        """
        Build a new DicomManager.
        timeout: The time this manager should wait for handlers to finish.
        dicom_key_fx: Returns a string uniquely identifying a dicom's series,
        given a dicom object
        """
        self.timeout = timeout
        self._stop = False
        self._series_handlers = {}
        self._mutex = threading.Condition()

    def wait(self):
        with self._mutex:
            while not self._stop:
                self._mutex.wait(self.timeout)

    def handle_dicom(self, dcm, *args, **kwargs):
        with self._mutex:
            if self._stop:
                logger.warn("Trying to process while stopped!")
                return
        key = self.handler_key(dcm)
        with self._mutex:
            if key not in self._series_handlers:
                logger.debug("Setting up handler for key: {0}".format(key))
                self._series_handlers[key] = self._setup_handler(
                    dcm, *args, **kwargs)
            self._mutex.notify()
        handler = self._series_handlers[key]
        handler.handle_dicom(dcm, *args, **kwargs)

    def handler_key(self, dcm):
        """
        A string to group a set of dicoms (eg, series number).

        You must override this in a subclass.

        """
        raise NotImplementedError()

    def build_handler(self, dcm, *args, **kwargs):
        """
        Build a new DicomSeriesHandler.

        You must override this in a subclass.

        """
        raise NotImplementedError()

    def _setup_handler(self, dcm, *args, **kwargs):
        dsh = self.build_handler(dcm, *args, **kwargs)
        dsh.start()
        return dsh

    def remove_handler(self, handler):
        logger.debug("Removing handler %s" % (handler.name))
        with self._mutex:
            del self._series_handlers[handler.name]

    def wait_for_handlers(self):
        for handler in self._series_handlers.values():
            handler.join(self.timeout)

    def stop(self):
        with self._mutex:
            self._stop = True
            self._mutex.notify()
        for handler in self._series_handlers.values():
            handler.terminate()
            handler.join()
