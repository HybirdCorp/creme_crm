# -*- coding: utf-8 -*-

try:
    from xml.etree.ElementTree import XML

    from ..base import CremeTestCase
    from creme.creme_core.utils.xml_utils import _element_iterator, xml_diff
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('XMLUtilsTestCase',)


class XMLUtilsTestCase(CremeTestCase):
    def test_iter(self):
        def make_tuples(xml):
            return [(deep_change, elt.tag) for (deep_change, elt) in _element_iterator(XML(xml))]

        self.assertEqual([(0, 'commands')],
                         make_tuples('<?xml version="1.0" encoding="UTF-8"?>'
                                     '<commands></commands>'
                                    )
                        )
        self.assertEqual([(0, 'commands'), (1, 'create')],
                         make_tuples('<commands><create /></commands>')
                        )
        self.assertEqual([(0, 'commands'), (1, 'create'), (1, 'entity')],
                         make_tuples('<commands><create><entity /></create></commands>')
                        )
        self.assertEqual([(0, 'commands'), (1, 'create'), (1, 'entity'), (0, 'entity'), (-1, 'update')],
                         make_tuples('<commands>'
                                     '  <create><entity /><entity />'
                                     '  </create>'
                                     '  <update />'
                                     '</commands>'
                                    )
                        )
        self.assertEqual([(0, 'commands'), (1, 'create'), (1, 'entity'),
                          (0, 'entity'), (1, 'field'), (-2, 'update'),
                         ],
                         make_tuples('<commands>'
                                     '  <create><entity /><entity><field id="5" /></entity></create>'
                                     '  <update />'
                                     '</commands>'
                                    )
                        )
        self.assertEqual([(0, 'commands'), (1, 'create'), (1, 'entity'), (0, 'entity'),
                          (1, 'field'), (-1, 'entity'), (-1, 'update'), (1, 'entity'),
                         ],
                         make_tuples('<commands>'
                                     '  <create>'
                                     '      <entity />'
                                     '      <entity><field id="5" /></entity>'
                                     '      <entity />'
                                     '  </create>'
                                     '  <update><entity /></update>'
                                     '</commands>'
                                    )
                        )

    def test_xml_diff01(self):
        xml01 = '<?xml version="1.0" encoding="UTF-8"?><commands></commands>'
        xml02 = '<?xml version="1.0" encoding="UTF-8"?><commands />'
        self.assertIsNone(xml_diff(xml01, xml02))

        xml01 = u'<?xml version="1.0" encoding="utf-8"?><créer></créer>'
        xml02 = u'<?xml version="1.0" encoding="UTF-8"?><créer />'
        self.assertIsNone(xml_diff(xml01, xml02))

    def test_xml_diff02(self): # attributes order can vary
        xml01 = ('<?xml version="1.0" encoding="UTF-8"?>'
                 '<commands attr1="foo" attr2="bar"></commands>'
                )
        self.assertIsNone(xml_diff(xml01, '<commands attr2="bar" attr1="foo" />'))

    def test_xml_diff03(self): #attributes value difference
        diff = xml_diff('<commands attr1="foo" attr2="bar"></commands>',
                        '<commands attr2="bar" attr1="stuff" />'
                       )
        self.assertIsNotNone(diff)
        self.assertEqual('<commands> ===> Attribute "attr1": "foo" != "stuff"', diff.short_msg)
        self.assertEqual('<commands attr1="foo" attr2="bar">'
                         ' -================= HERE : Attribute "attr1": "foo" != "stuff" ==========</commands>',
                         diff.long_msg
                        )
        #self.assertEqual('<commands attr1="foo" attr2="bar" /> -================= HERE : Attribute "attr1": "foo" != "stuff" ==========',
                         #diff.long_msg
                        #)

    def test_xml_diff04(self): #additional attribute
        xml01 = ('<commands attr1="foo">\n'
                 '    <create />\n'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 ' <create />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<commands> ===> Attribute "attr2" is missing in the first document',
                         diff.short_msg
                        )
        self.assertEqual('<commands attr1="foo"> -================= HERE : '
                         'Attribute "attr2" is missing in the first document ==========\n'
                         '    <create />\n'
                         '</commands>',
                         diff.long_msg
                        )
        #self.assertEqual('<commands attr1="foo">\n'
                         #'    <create />\n'
                         #'</commands> -================= HERE : Attribute "attr2" is missing in the first document ==========',
                         #diff.long_msg
                        #)

    def test_xml_diff05(self): #missing attribute
        diff = xml_diff('<commands attr1="bar" attr2="stuff" />', '<commands attr2="stuff" />')
        self.assertIsNotNone(diff)
        self.assertEqual('<commands> ===> Attribute "attr1" is missing in the second document',
                         diff.short_msg
                        )
        self.assertEqual('<commands attr1="bar" attr2="stuff"> -================= HERE : '
                         'Attribute "attr1" is missing in the second document ==========</commands>',
                         diff.long_msg
                        )

    def test_xml_diff06(self):
        xml01 = ('<commands attr1="foo" attr2="bar">'
                    '<create attr3="xxx" >'
                    '</create>'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '</commands>'
                )
        self.assertIsNone(xml_diff(xml01, xml02))

    def test_xml_diff07(self): #tag difference
        xml01 = ('<commands attr1="foo" attr2="bar">\n'
                 '   <create attr3="xxx" >\n'
                 '   </create>\n'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<create> ===> Tag "create" != "update"', diff.short_msg)
        self.assertEqual('<commands attr1="foo" attr2="bar">\n'
                         '   <create attr3="xxx"> -================= HERE : Tag "create" != "update" ==========\n'
                         '   </create>\n'
                         '</commands>',
                         diff.long_msg
                        )

    def test_xml_diff08(self): #missing child
        xml01 = ('<commands attr1="foo" attr2="bar">\n'
                 '   <create attr3="xxx" >\n'
                 '      <update />'
                 '   </create>\n'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<update> ===> Does not exist', diff.short_msg)

    def test_xml_diff09(self): # child becomes sibling
        xml01 = ('<commands attr1="foo" attr2="bar">\n'
                 '   <create attr3="xxx" >\n'
                 '      <field name="uuid" />\n'
                 '      <update />'
                 '   </create>\n'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" >\n'
                 '      <field name="uuid" />\n'
                 '   </create>\n'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<update> ===> Does not exist', diff.short_msg)

    def test_xml_diff10(self): #additional child
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        xml02 = ('<commands attr1="foo" attr2="bar">\n'
                 '   <create attr3="xxx" >\n'
                 '      <update />'
                 '   </create>\n'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<create> ===> Additional sibling or child element in the second document',
                         diff.short_msg
                        )

    def test_xml_diff11(self): #text difference
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update>Text element</update>'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<update> ===> Text "" != "Text element"', diff.short_msg)

    def test_xml_diff12(self): #missing tag
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, '<commands attr2="bar" attr1="foo" />')
        self.assertIsNotNone(diff)
        self.assertEqual('<create> ===> Does not exist in second document', diff.short_msg)

    def test_xml_diff13(self): #additional tags
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff('<commands attr2="bar" attr1="foo" />', xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<commands> ===> Additional sibling or child element in the second document',
                         diff.short_msg
                        )

    def test_xml_diff14(self): #tail difference
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />My Tail'
                 '   <update />'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<create> ===> Tail "My Tail" != ""', diff.short_msg)

    def test_assert_xml_equal(self):
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        self.assertXMLEqual(xml01,
                            '<commands attr1="foo" attr2="bar" >'
                            ' <create attr3="xxx" />'
                            ' <update></update>'
                            '</commands>'
                           )

        self.assertRaises(AssertionError, self.assertXMLEqual, xml01,
                          '<commands attr2="bar" >'
                          '   <create attr3="xxx" />'
                          '   <update />'
                          '</commands>'
                         )
        self.assertRaises(AssertionError, self.assertXMLEqual,
                          '<commands attr2="bar" attr1="foo" >', #syntax error
                          '<commands attr2="bar" attr1="foo" />',
                         )

