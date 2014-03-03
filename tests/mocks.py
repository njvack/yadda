# coding: utf8
# Part of yadda -- a simple dicom file upload tool

class FakeDicom(object):

    def __init__(self, key):
        self.key = key

    @property
    def series_unique_key(self):
        return self.key

    @property
    def InstanceNumber(self):
        return 0

    def __str__(self):
        return "FakeDicom(%s)" % (self.key)