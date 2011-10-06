# -*- coding: utf-8 -*-

#Code based on code from the official Python documentation :
# http://docs.python.org/release/2.5.4/lib/csv-examples.html

import csv, codecs, cStringIO


class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    __slots__ = ('reader',)

    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """
    __slots__ = ('reader',)

    def __init__(self, f, guess_dialect=True, dialect=csv.excel, encoding="utf-8", **kwargs):
        if guess_dialect:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)

        self.reader = csv.reader(UTF8Recoder(f, encoding), dialect=dialect, **kwargs)

    def __iter__(self):
        return self

    def next(self):
        return [unicode(s, "utf-8") for s in self.reader.next()]


class UnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """
    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwargs):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwargs)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
