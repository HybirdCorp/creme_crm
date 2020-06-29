# -*- coding: utf-8 -*-

from creme.creme_core.utils import chunktools

from ..base import CremeTestCase


class ChunkToolsTestCase(CremeTestCase):
    DATA_UNIX = """04 05 99 66 54
055 6 5322 1 2

98

    456456 455 12
        45 156
dfdsfds
s556"""

    DATA_WINDOWS = DATA_UNIX.replace('\n', '\r\n')
    DATA_MAC = DATA_UNIX.replace('\n', '\r')

    DATA_RANDOM_LINESEP = (
        '04 05 99 66 54\r\n055 6 5322 1 2\r\r\n98\n\n    '
        '456456 455 12\r        45 156\rdfdsfds\r\ns556'
    )

    def assertFilteredEntries(self, entries):
        self.assertListEqual(
            ['0405996654', '0556532212', '98', '45645645512', '45156', '556'],
            entries
        )

    def assertSplitEntries(self, entries):
        self.assertListEqual(
            [
                '04 05 99 66 54',
                '055 6 5322 1 2',
                '98',
                '    456456 455 12',
                '        45 156',
                'dfdsfds',
                's556'
            ],
            entries
        )

    def chunks(self, chunk_size, source=None):
        source = source if source is not None else self.DATA_UNIX
        for chunk in chunktools.iter_as_chunk(source, chunk_size):
            yield ''.join(chunk)

    @staticmethod
    def filter(entry):
        return ''.join(char for char in entry if char.isdigit())

    def test_iter_as_slices01(self):
        chunks = [*chunktools.iter_as_slices(self.DATA_UNIX, 1000)]

        self.assertEqual(1, len(chunks))
        self.assertEqual(self.DATA_UNIX, ''.join(chunks))

    def test_iter_as_slices02(self):
        assert len(self.DATA_UNIX) % 5 == 0
        chunks = [*chunktools.iter_as_slices(self.DATA_UNIX, 5)]

        self.assertEqual(16, len(chunks))

        for i, chunk in enumerate(chunks):
            self.assertEqual(5, len(chunk), f'Bad size for chunk {i}: {chunk}')

        self.assertEqual(self.DATA_UNIX, ''.join(chunks))

    def test_iter_as_slices03(self):
        data = self.DATA_UNIX + '9'
        assert len(data) % 5 == 1
        chunks = [*chunktools.iter_as_slices(data, 5)]

        self.assertEqual(17, len(chunks))

        for i, chunk in enumerate(chunks[:-1]):
            self.assertEqual(5, len(chunk), f'Bad size for chunk {i}: {chunk}')

        self.assertEqual('9', chunks[-1])
        self.assertEqual(data, ''.join(chunks))

    def test_iter_as_chunks01(self):
        chunks = [*chunktools.iter_as_chunk(self.DATA_UNIX, 1000)]
        self.assertEqual(1, len(chunks))
        self.assertEqual(self.DATA_UNIX, ''.join(chunks[0]))

    def test_iter_as_chunks02(self):
        assert len(self.DATA_UNIX) % 5 == 0
        chunks = [*chunktools.iter_as_chunk(self.DATA_UNIX, 5)]

        self.assertEqual(16, len(chunks))

        for i, chunk in enumerate(chunks):
            self.assertEqual(5, len(chunk), f'Bad size for chunk {i}: {chunk}')
            self.assertIsInstance(chunk, list)

        self.assertEqual(self.DATA_UNIX, ''.join(''.join(chunk) for chunk in chunks))

    def test_iter_as_chunks03(self):
        data = self.DATA_UNIX + '9'
        assert len(data) % 5 == 1
        chunks = [*chunktools.iter_as_chunk(data, 5)]

        self.assertEqual(17, len(chunks))

        for i, chunk in enumerate(chunks[:-1]):
            self.assertEqual(5, len(chunk), f'Bad size for chunk {i}: {chunk}')

        self.assertEqual(['9'], chunks[-1])
        self.assertEqual(data, ''.join(''.join(chunk) for chunk in chunks))

    def test_iter_splitchunks_size_under_linesize(self):
        "Tests small_chunks"
        chunk_size = 5
        entries = [
            *chunktools.iter_splitchunks(
                self.chunks(chunk_size), '\n', ChunkToolsTestCase.filter
            ),
        ]
        self.assertFilteredEntries(entries)

    def test_iter_splitchunks_linesize_over_limit(self):
        "Tests small_chunks."
        chunk_size = 5
        chunks = self.chunks(chunk_size, '0405996654\n0405996653\n0405996652')

        entries = [*chunktools.iter_splitchunks(chunks, '\n', ChunkToolsTestCase.filter, limit=10)]
        self.assertListEqual(['0405996654', '0405996653', '0405996652'], entries)

        chunks = self.chunks(chunk_size, '7777788888\n9999900000555\n1111122222')

        with self.assertRaises(ValueError) as error:
            [*chunktools.iter_splitchunks(chunks, '\n', ChunkToolsTestCase.filter, limit=10)]

        self.assertEqual(str(error.exception), 'line length is over %d characters' % 10)

    def test_iter_splitchunks_size_1(self):
        "Tests small_chunks."
        self.assertFilteredEntries([
            *chunktools.iter_splitchunks(
                self.chunks(chunk_size=1), '\n', ChunkToolsTestCase.filter,
            )
        ])

    def test_iter_splitchunks_size_over_linesize(self):
        "Test big_chunks."
        chunk_size = len(self.DATA_UNIX) / 2
        self.assertFilteredEntries([
            *chunktools.iter_splitchunks(
                self.chunks(chunk_size), '\n', ChunkToolsTestCase.filter,
            )
        ])

    def test_iter_splitchunks_one_chunk(self):
        "Test with one chunk."
        chunk_size = len(self.DATA_UNIX) * 2
        self.assertFilteredEntries([
            *chunktools.iter_splitchunks(
                self.chunks(chunk_size), '\n', ChunkToolsTestCase.filter,
            ),
        ])

    def test_iter_splitchunks_no_filter(self):
        self.assertSplitEntries([
            *chunktools.iter_splitchunks(self.chunks(5), '\n', None),
        ])

    def test_iter_splitchunks_nbytes_key(self):
        data = self.DATA_WINDOWS
        self.assertFilteredEntries([
            *chunktools.iter_splitchunks(
                self.chunks(5, data), '\r\n', ChunkToolsTestCase.filter,
            )
        ])
        self.assertFilteredEntries([
            *chunktools.iter_splitchunks(
                self.chunks(len(data) / 2, data), '\r\n', ChunkToolsTestCase.filter,
            )
        ])
        self.assertFilteredEntries([
            *chunktools.iter_splitchunks(
                self.chunks(len(data) * 2, data), '\r\n', ChunkToolsTestCase.filter,
            ),
        ])

    def test_iter_splitchunks_nbytes_key_chunk_limits(self):
        self.assertListEqual(
            ['1234', '56789012', '345', '12'],
            [
                *chunktools.iter_splitchunks(
                    ['1234\r', '\n5678', '9012\r\n', '345\r\n', '12'],
                    '\r\n', ChunkToolsTestCase.filter,
                ),
            ]
        )
