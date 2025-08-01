from datetime import date, datetime
from os import listdir, makedirs
from os import remove as delete_file
from os.path import exists, join
from shutil import rmtree

from django.conf import settings

from creme.creme_core.utils.file_handling import (
    DateFileNameSuffixGenerator,
    DatetimeFileNameSuffixGenerator,
    FileCreator,
    IncrFileNameSuffixGenerator,
    RandomFileNameSuffixGenerator,
)

from ..base import CremeTestCase


class FileHandlingTestCase(CremeTestCase):
    dir_path = ''

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        utils_dir_path = join(settings.MEDIA_ROOT, 'creme_core-tests', 'utils')

        if not exists(utils_dir_path):
            makedirs(utils_dir_path, 0o755)

        cls.dir_path = dir_path = join(utils_dir_path, 'file_handling')

        if exists(dir_path):
            rmtree(dir_path)

    def tearDown(self):
        dir_path = self.dir_path

        if exists(dir_path):
            for filename in listdir(dir_path):
                delete_file(join(dir_path, filename))

    def test_incr_generator(self):
        fng = IncrFileNameSuffixGenerator()

        with self.assertNoException():
            it = iter(fng)

        with self.assertNoException():
            name1 = next(it)

        self.assertEqual('_1', name1)

        with self.assertNoException():
            name2 = next(it)

        self.assertEqual('_2', name2)

    def test_random_generator(self):
        fng = RandomFileNameSuffixGenerator()

        with self.assertNoException():
            it = iter(fng)

        with self.assertNoException():
            name1 = next(it)

        self.assertStartsWith(name1, '_')

        with self.assertNoException():
            int(name1[1:], base=16)

        name2 = next(it)
        self.assertNotEqual(name1, name2)

    def test_date_generator(self):
        fng = DateFileNameSuffixGenerator()

        with self.assertNoException():
            it = iter(fng)

        with self.assertNoException():
            name1 = next(it)

        self.assertEqual(name1, '_%s' % date.today().strftime('%d%m%Y'))

        with self.assertRaises(StopIteration):
            next(it)

    def test_datetime_generator(self):
        fng = DatetimeFileNameSuffixGenerator()

        with self.assertNoException():
            it = iter(fng)

        with self.assertNoException():
            name1 = next(it)

        self.assertStartsWith(name1, '_')

        dt_str = name1[1:]

        with self.assertNoException():
            dt = datetime.strptime(dt_str, '%d%m%Y_%H%M%S')

        self.assertDatetimesAlmostEqual(datetime.now(), dt)

    def test_file_creator01(self):
        "With 1 generator (IncrFileNameGenerator)."
        dir_path = self.dir_path

        name1 = 'foobar.txt'
        fcreator = FileCreator(dir_path, name1, generators=[IncrFileNameSuffixGenerator])
        path1 = fcreator.create()
        self.assertTrue(exists(dir_path))
        self.assertListEqual([name1], listdir(dir_path))
        self.assertEqual(join(dir_path, name1), path1)

        path2 = fcreator.create()
        name2 = 'foobar_1.txt'
        self.assertCountEqual([name1, name2], listdir(dir_path))
        self.assertEqual(join(dir_path, name2), path2)

    def test_file_creator02(self):
        "With 1 generator (DateFileNameGenerator)."
        dir_path = self.dir_path

        name1 = 'stuff.txt'
        fcreator = FileCreator(
            dir_path, name1, generators=[DateFileNameSuffixGenerator],
        )
        fcreator.create()
        self.assertEqual([name1], listdir(dir_path))

        fcreator.create()
        name2 = 'stuff_{}.txt'.format(date.today().strftime('%d%m%Y'))
        self.assertCountEqual([name1, name2], listdir(dir_path))

        with self.assertRaises(FileCreator.Error):
            fcreator.create()

    def test_file_creator03(self):
        "2 generators"
        dir_path = self.dir_path

        name1 = 'stuff.txt'
        fcreator = FileCreator(
            dir_path, name1,
            generators=(
                DateFileNameSuffixGenerator,
                IncrFileNameSuffixGenerator,
            ),
        )

        fcreator.create()
        self.assertEqual([name1], listdir(dir_path))

        fcreator.create()
        date_str = date.today().strftime('%d%m%Y')
        name2 = f'stuff_{date_str}.txt'
        self.assertCountEqual([name1, name2], listdir(dir_path))

        fcreator.create()
        name3 = f'stuff_{date_str}_1.txt'
        self.assertCountEqual([name1, name2, name3], listdir(dir_path))

    def test_file_creator04(self):
        "Max trials"
        dir_path = self.dir_path

        name1 = 'foobar.txt'
        fcreator = FileCreator(
            dir_path, name1, generators=[IncrFileNameSuffixGenerator], max_trials=2,
        )
        fcreator.create()
        fcreator.create()

        with self.assertRaises(FileCreator.Error):
            fcreator.create()

    def test_file_creator05(self):
        "Max length."
        dir_path = self.dir_path

        name = 'foobar.txt'  # len == 10
        fcreator = FileCreator(
            dir_path, name, generators=[DateFileNameSuffixGenerator], max_length=15,
        )
        fcreator.create()

        fcreator.create()
        self.assertCountEqual(
            [name, f'fo_{date.today().strftime("%d%m%Y")}.txt'],
            listdir(dir_path),
        )

    def test_file_creator06(self):
        "Max length (suffix is too long even alone)."
        dir_path = self.dir_path

        name = 'foobar.txt'  # len == 10
        fcreator = FileCreator(
            dir_path, name, generators=[DateFileNameSuffixGenerator], max_length=12,
        )
        fcreator.create()

        with self.assertRaises(FileCreator.Error):
            fcreator.create()

    def test_file_creator07(self):
        "Max length (length too short for extension...)."
        dir_path = self.dir_path

        fcreator = FileCreator(
            dir_path, 'foobar.txt', generators=[DateFileNameSuffixGenerator], max_length=3,
        )

        with self.assertRaises(FileCreator.Error):
            fcreator.create()

    def test_file_creator08(self):
        "Secure filename."
        dir_path = self.dir_path

        fcreator = FileCreator(
            dir_path, 'foo bar.txt', generators=[IncrFileNameSuffixGenerator],
        )
        path1 = fcreator.create()
        self.assertEqual(join(dir_path, 'foo_bar.txt'), path1)

    def test_file_creator09(self):
        "Default 'generators' argument."
        dir_path = self.dir_path

        fcreator = FileCreator(dir_path, 'foobar.txt')
        path1 = fcreator.create()

        with self.assertNoException():
            path2 = fcreator.create()

        self.assertNotEqual(path1, path2)
