# -*- coding: utf-8 -*-

import os
from datetime import datetime
from tempfile import NamedTemporaryFile

from xlrd import XLRDError

from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils.xlrd_utils import XlrdReader
from creme.creme_core.utils.xlwt_utils import XlwtWriter


class XLSUtilsTestCase(CremeTestCase):
    files = ('data-xls5.0-95.xls',
             'data-xls97-2003.xls',
             'data-xlsx.xlsx'
             )
    current_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
    data = [
        ['Prénom', 'Nom', 'Taille1', 'Taille2', 'Send_Date'],
        ['Gérard', 'Bouchard', 0.5, 0.5, datetime(2014, 8, 6, 20, 57, 32)],
        ['Hugo', 'Smett', 122, 122, ''],
        ['Rémy', 'Rakic', 12, 12, datetime(2014, 8, 6, 19, 48, 32)],
        ['Florian', 'Fabre', 0.004, 0.004, '51/08/2014 00:00:00'],
        ['Jean-Michel', 'Armand', 42, 42, datetime(2014, 8, 6, 19, 48, 32)],
        ['Guillaume', 'Englert', 50, 50, datetime(2014, 8, 6, 19, 48, 32)],
        ['Jonathan', 'Caruana', -50, -50, datetime(2014, 8, 6, 20, 57, 32)],
    ]

    def get_file_path(self, filename):
        return os.path.join(self.current_path, filename)

    def test_unknown_filename(self):
        with self.assertRaises(IOError):
            XlrdReader(filedata=self.get_file_path('unknown.xls'))

    def test_invalid_file(self):
        with self.assertRaises(XLRDError) as error:
            XlrdReader(filedata=self.get_file_path('data-invalid.xls'))

        self.assertEqual(
            str(error.exception),
            "Unsupported format, or corrupt file: Expected BOF record; found b'this is '"
        )

    def test_sheet(self):
        rd = XlrdReader(filedata=self.get_file_path(self.files[0]))
        self.assertIsNotNone(rd.book)
        self.assertIsNotNone(rd.sheet)
        self.assertEqual(rd.sheet.nrows, len(self.data))

    def test_read_next(self):
        for filename in self.files:
            rd = XlrdReader(filedata=self.get_file_path(filename))
            for element in self.data:
                self.assertEqual(element, next(rd))

    def test_as_list(self):
        for filename in self.files:
            rd = XlrdReader(filedata=self.get_file_path(filename))
            self.assertListEqual(self.data, [*rd])

    def test_open_file(self):
        for filename in self.files:
            with open(self.get_file_path(filename), mode='rb') as file_obj:
                file_content = file_obj.read()
                rd = XlrdReader(file_contents=file_content)
                self.assertEqual([*rd], self.data)

    def test_write_and_read(self):
        file = NamedTemporaryFile(suffix=".xls")

        wt = XlwtWriter()
        writerow = wt.writerow
        for element in self.data:
            writerow(element)
        wt.save(file.name)

        rd = XlrdReader(filedata=file.name)
        self.assertEqual([*rd], self.data)

        with open(file.name, mode='rb') as file_obj:
            file_content = file_obj.read()
            rd = XlrdReader(file_contents=file_content)
            self.assertEqual([*rd], self.data)

    def test_truncate(self):
        content = """Lôrèm ipsum dolor sit amet, consectetur adipiscing elit. Proin ac odio libero.
Praesent sollicitudin, mauris non sagittis tincidunt, magna libero malesuada lectus,
sit amet dictum nulla mi ac justo.
Vivamus laoreet metus eu purus tincidunt, et consectetur justo mattis.
Phasellus egestas a lacus nec pulvinar.
Sed a lectus eleifend, hendrerit ligula nec, aliquet sem.
Quisque nec tortor nec ante pharetra cursus sed facilisis lorem.
Praesent blandit pharetra nulla, id ultrices diam molestie sed.
""" * 100
        self.assertGreater(len(content), 32767)

        file = NamedTemporaryFile(suffix='.xls')

        wt = XlwtWriter()
        wt.writerow([content])

        with self.assertNoException():
            wt.save(file.name)

        read_content = [*XlrdReader(filedata=file.name)]
        self.assertEqual(1, len(read_content))

        elt = read_content[0]
        self.assertEqual(1, len(elt))
        self.assertEqual(32767, len(elt[0]))
