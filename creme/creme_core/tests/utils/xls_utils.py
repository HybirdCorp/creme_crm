# -*- coding: utf-8 -*-

try:
    import os
    from datetime import datetime
    from tempfile import NamedTemporaryFile

    from django.utils.unittest.case import skipIf

    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

try:
    from creme.creme_core.utils.xlwt_utils import XlwtWriter
except Exception:
    XlwtMissing = True
else:
    XlwtMissing = False

try:
    from xlrd import XLRDError
    from creme.creme_core.utils.xlrd_utils import XlrdReader
except Exception:
    XlrdMissing = True
else:
    XlrdMissing = False


class XLSUtilsTestCase(CremeTestCase):
    files = ('data-xls5.0-95.xls',
             'data-xls97-2003.xls',
             'data-xlsx.xlsx'
             )
    current_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
    data = [[u"Prénom", u"Nom", u'Taille1', u'Taille2', u'Send_Date'],
            [u"Gérard", u"Bouchard", 0.5, 0.5, datetime(2014, 8, 6, 20, 57, 32)],
            [u"Hugo", u"Smett", 122, 122, ''],
            [u"Rémy", u"Rakic", 12, 12, datetime(2014, 8, 6, 19, 48, 32)],
            [u"Florian", u"Fabre", 0.004, 0.004, u'51/08/2014 00:00:00'],
            [u"Jean-Michel", u"Armand", 42, 42, datetime(2014, 8, 6, 19, 48, 32)],
            [u"Guillaume", u"Englert", 50, 50, datetime(2014, 8, 6, 19, 48, 32)],
            [u"Jonathan", u"Caruana", -50, -50, datetime(2014, 8, 6, 20, 57, 32)]]

    def get_file_path(self, filename):
        return os.path.join(self.current_path, filename)

    @skipIf(XlrdMissing, "Skip tests, couldn't find xlrd libs")
    def test_unknown_filename(self):
        with self.assertRaises(IOError):
            XlrdReader(filedata=self.get_file_path('unknown.xls'))

    @skipIf(XlrdMissing, "Skip tests, couldn't find xlrd libs")
    def test_invalid_file(self):
        with self.assertRaises(XLRDError) as error:
            XlrdReader(filedata=self.get_file_path('data-invalid.xls'))

        self.assertEquals(str(error.exception), "Unsupported format, or corrupt file: Expected BOF record; found 'this is '")

    @skipIf(XlrdMissing, "Skip tests, couldn't find xlrd libs")
    def test_sheet(self):
        rd = XlrdReader(filedata=self.get_file_path(self.files[0]))
        self.assertIsNotNone(rd.book)
        self.assertIsNotNone(rd.sheet) 
        self.assertEquals(rd.sheet.nrows, len(self.data))

    @skipIf(XlrdMissing, "Skip tests, couldn't find xlrd libs")
    def test_read_next(self):
        for filename in self.files:
            rd = XlrdReader(filedata=self.get_file_path(filename))
            for element in self.data:
                self.assertEqual(element, rd.next())

    @skipIf(XlrdMissing, "Skip tests, couldn't find xlrd libs")
    def test_as_list(self):
        for filename in self.files:
            rd = XlrdReader(filedata=self.get_file_path(filename))
            self.assertEqual(self.data, list(rd))

    @skipIf(XlrdMissing, "Skip tests, couldn't find xlrd libs")
    def test_open_file(self):
        for filename in self.files:
            with open(self.get_file_path(filename)) as filename:
                file_content = filename.read()
                rd = XlrdReader(file_contents=file_content)
                self.assertEqual(list(rd), self.data)

    @skipIf(XlrdMissing or XlwtMissing, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_write_and_read(self):
        file = NamedTemporaryFile(suffix=".xls")

        wt = XlwtWriter()
        writerow = wt.writerow
        for element in self.data:
            writerow(element)
        wt.save(file.name)

        rd = XlrdReader(filedata=file.name)
        self.assertEqual(list(rd), self.data)

        with open(file.name) as file_content:
            file_content = file_content.read()
            rd = XlrdReader(file_contents=file_content)
            self.assertEqual(list(rd), self.data)
