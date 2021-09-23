# -*- coding: utf-8 -*-

from django.test.utils import override_settings

from creme.creme_core.tests.base import CremeTestCase

from ..decoders import CrudityDecoderManager
from ..decoders.ini import IniDecoder
from ..decoders.xls import XLSDecoder


class DecoderManagerTestCase(CremeTestCase):
    def test_empty(self):
        "Empty."
        mngr = CrudityDecoderManager([])
        self.assertFalse([*mngr.decoder_classes])
        self.assertIsNone(mngr.decoder(IniDecoder.id))

    def test_direct_settings(self):
        "Settings passed directly."
        mngr = CrudityDecoderManager([
            'creme.crudity.decoders.ini.IniDecoder',
            'creme.crudity.decoders.xls.XLSDecoder',
        ])
        self.assertCountEqual([IniDecoder, XLSDecoder], [*mngr.decoder_classes])
        self.assertIsInstance(mngr.decoder(IniDecoder.id), IniDecoder)
        self.assertIsInstance(mngr.decoder(XLSDecoder.id), XLSDecoder)
        self.assertIsNone(mngr.decoder('invalid'), XLSDecoder)

    @override_settings(CRUDITY_DECODERS=[
        'creme.crudity.decoders.ini.IniDecoder',
    ])
    def test_default_settings(self):
        "Settings passed directly."
        mngr = CrudityDecoderManager()
        self.assertListEqual([IniDecoder], [*mngr.decoder_classes])

    def test_errors01(self):
        "Invalid path."
        mngr = CrudityDecoderManager([
            'creme.crudity.decoders.doesnotexist.UnknownDecoder',
        ])

        with self.assertRaises(CrudityDecoderManager.InvalidDecoderClass):
            _ = [*mngr.decoder_classes]

        # TODO: decoder() => exception/None ?

    def test_errors02(self):
        "Invalid class."
        mngr = CrudityDecoderManager(['creme.crudity.models.WaitingAction'])

        with self.assertRaises(CrudityDecoderManager.InvalidDecoderClass):
            _ = [*mngr.decoder_classes]


# TODO:
# class IniDecoderTestCase(CremeTestCase):
# class XLSDecoderTestCase(CremeTestCase):
