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
import os

logger = logging.getLogger(__name__)


class ThreadedDicomManager(object):
    """
    Generic wrapper for all incoming dicoms -- reads a dicom, gets its
    series_unique_key, and builds a DicomSeriesHandler for it.
    """

    def __init__(self, timeout, dicom_key_fx, handler_factory):
        """
        Build a new DicomManager.
        timeout: The time this manager should wait for handlers to finish.
        dicom_key_fx: Returns a string uniquely identifying a dicom's series,
        given a dicom object
        handler_factory: Creates a new dicom handler, is passed an example
        dicom, name, and self.
        """
        self.timeout = timeout
        self.dicom_key_fx = dicom_key_fx
        self.handler_factory = handler_factory
        self._series_handlers = {}
        self._mutex = threading.Condition()

    def handle_dicom(self, dcm):
        key = self.dicom_key_fx(dcm)
        with self._mutex:
            if key not in self._series_handlers:
                logger.debug("Setting up handler for key: %s" % (key))
                self._series_handlers[key] = self._setup_handler(dcm)
        handler = self._series_handlers[key]
        handler.handle_dicom(dcm)

    def _setup_handler(self, dcm):
        dsh = self.handler_factory(dcm, self)
        dsh.start()
        return dsh

    def remove_handler(self, handler):
        logger.debug("Removing handler %s" % (handler.name))
        with self._mutex:
            del self._series_handlers[handler.name]

    def wait_for_handlers(self):
        for handler in self._series_handlers.values():
            handler.join(self.timeout)


