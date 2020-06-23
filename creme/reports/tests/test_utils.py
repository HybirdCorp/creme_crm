# -*- coding: utf-8 -*-

from creme.creme_core.tests.base import CremeTestCase

from ..utils import expand_sparse_iterator, sparsezip


class SparsezipTestCase(CremeTestCase):
    def assertExpandsTo(
            self,
            sparse_collection,
            expected_result,
            default_value=-1):
        expanded_collection = [
            *expand_sparse_iterator(iter(sparse_collection), default_value),
        ]
        self.assertListEqual(expanded_collection, expected_result)

    def assertSparsezipsTo(
            self,
            full_collection,
            sparse_collection,
            expected_result,
            default_value=-1):
        zipped_sequence = [
            *sparsezip(full_collection, sparse_collection, default_value),
        ]
        self.assertListEqual(zipped_sequence, expected_result)

    def test_expand_empty_collection(self):
        self.assertExpandsTo([], [])

    def test_expand_singular_collection(self):
        sparse_collection = [(0, 666)]
        expanded_collection = [666]

        self.assertExpandsTo(sparse_collection, expanded_collection)

    def test_expand_sparse_bounds(self):
        sparse_collection = [(0, 1), (5, 5)]
        expanded_collection = [1, -1, -1, -1, -1, 5]

        self.assertExpandsTo(sparse_collection, expanded_collection)

    def test_expand_sparse_collection(self):
        sparse_collection = [(0, 1), (4, 3), (5, 5)]
        expanded_collection = [1, 0, 0, 0, 3, 5]

        self.assertExpandsTo(sparse_collection, expanded_collection, 0)

    def test_sparsezip_singular_collections(self):
        keys = ['A']
        values = [(0, 100)]

        self.assertSparsezipsTo(keys, values, [('A', 100)])

    def test_sparsezip_similar_collections(self):
        keys = ['A', 'B', 'C']
        values = [(0, 100), (1, 200), (2, 300)]

        self.assertSparsezipsTo(keys, values, [('A', 100), ('B', 200), ('C', 300)])

    def test_sparsezip_expands_sparse_collection(self):
        # More keys -> the missing 'values' have to be filled using expand_sparse_iterator
        keys = ['A', 'B', 'C']
        sparse_values = [(0, 100), (1, 200)]

        self.assertSparsezipsTo(keys, sparse_values, [('A', 100), ('B', 200), ('C', -1)])

    def test_sparsezip_zips_longest_collection(self):
        # More values -> the missing 'keys' have to be filled with the default value
        keys = ['A', 'B']
        values = [(0, 100), (1, 200), (2, 300)]

        self.assertSparsezipsTo(keys, values, [('A', 100), ('B', 200), (0, 300)], 0)
