# -*- coding: utf-8 -*-

import errno
import re
import subprocess
from itertools import chain
from unittest import skipIf
from xml.etree.ElementTree import XML, tostring

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import CremeEntity, Language
from creme.documents.tests.base import skipIfCustomDocument
from creme.persons.tests.base import skipIfCustomContact

from .. import registry
from ..backends.models import CrudityBackend
from ..builders.infopath import InfopathFormBuilder, InfopathFormField
from .base import (
    Contact,
    ContactFakeBackend,
    CrudityTestCase,
    Document,
    DocumentFakeBackend,
)

lcabMissing = False
try:
    subprocess.call(['lcab'])
except OSError as e:
    if e.errno == errno.ENOENT:
        lcabMissing = True
        print('It seems that "lcab" is not installed -> skip some tests')


# TODO: use test models instead of skipping

# TODO: factorise with CrudityViewsTestCase
@skipIfCustomContact
class InfopathFormBuilderTestCase(CrudityTestCase):
    _original_crudity_registry = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._original_crudity_registry = registry.crudity_registry

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        registry.crudity_registry = cls._original_crudity_registry

    def setUp(self):
        super().setUp()
        self.login()

        self.request = request = RequestFactory().get('/')  # Url doesn't matter
        request.user = self.user
        request.LANGUAGE_CODE = '1033'  # en

    def _get_builder(self, backend):
        return InfopathFormBuilder(request=self.request, backend=backend)

    def _get_backend(self, backend_klass, **backend_cfg):
        return backend_klass(config=backend_cfg)

    def test_builder_01(self):
        class DummyCrudityBackend(CrudityBackend):
            pass
        self.assertRaises(AssertionError, self._get_builder, DummyCrudityBackend({}))

    def test_builder_02(self):
        backend = self._get_backend(ContactFakeBackend, subject='create_ce')
        builder = self._get_builder(backend)

        now_str = builder.now.strftime('%Y-%m-%dT%H:%M:%S')
        self.assertEqual(
            f'http://schemas.microsoft.com/office/infopath/2003/myXSD/{now_str}',
            builder.namespace,
        )
        self.assertEqual(
            'urn:schemas-microsoft-com:office:infopath:{}:-myXSD-{}'.format(
                'create-create_ce', now_str,
            ),
            builder.urn,
        )

    def test_builder_get_lang(self):
        backend = self._get_backend(ContactFakeBackend, subject='create_ce')
        self.assertEqual('1036', self._get_builder(backend)._get_lang_code('fr'))

    def test_builder_fields_property(self):
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact',
            model=Contact,
            body_map={
                'user_id':     1,
                'first_name':  '',
                'last_name':   '',
                'email':       'none@none.com',
                'description': '',
                'birthday':    '',
            },
            password='creme',
        )
        builder = self._get_builder(backend)

        for field in builder.fields:
            self.assertIn(field.name, backend.body_map)
            self.assertEqual(Contact, field.model)

        for field in builder.fields:  # Two passes because of cache
            self.assertIn(field.name, backend.body_map)
            self.assertEqual(Contact, field.model)

    def test_manifest_xsf_01(self):
        "Test some base values."
        backend = self._get_backend(ContactFakeBackend, subject='create_ce')
        builder = self._get_builder(backend)
        ns  = '{http://schemas.microsoft.com/office/infopath/2003/solutionDefinition}'
        ns2 = '{http://schemas.microsoft.com/office/infopath/2006/solutionDefinition/extensions}'

        content = builder._render_manifest_xsf(self.request)
        xml = XML(content)
        xml_find = xml.find

        namespace = builder.get_namespace()
        self.assertEqual(
            re.search(r'xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content)['ns'],
            namespace,
        )  # Can't be got with ElementTree, because it's a namespace

        self.assertEqual(builder.get_urn(), xml.get('name'))

        self.assertEqual(
            namespace,
            xml_find(
                f'{ns}package/{ns}files/{ns}file/{ns}fileProperties/{ns}property'
            ).get('value')
        )
        self.assertEqual(
            namespace,
            xml_find(
                f'{ns}applicationParameters/{ns}solutionProperties'
            ).get('fullyEditableNamespace')
        )
        self.assertEqual(
            namespace,
            xml_find(
                f'{ns}documentSchemas/{ns}documentSchema'
            ).get('location').split()[0]
        )

        # ElementTree 1.2.6 (shipped with python <= 2.6) doesn't support
        # advanced xpath expressions  TODO: improve
        file_nodes = xml.findall(f'{ns}package/{ns}files/{ns}file')

        for node in file_nodes:
            if node.get('name') == 'view1.xsl':
                found_node = node
                break
        else:
            self.fail('<xsf:file name="view1.xsl"> not found')

        for node in found_node.findall(f'{ns}fileProperties/{ns}property'):
            if node.get('name') == 'lang':
                # property_node = node  # TODO: use ?
                self.assertEqual(
                    builder._get_lang_code(self.request.LANGUAGE_CODE),
                    node.get('value'),
                )
                break
        else:
            self.fail(
                '<xsf:property name="lang" type="string" value=""></xsf:property> not found'
            )

        mail_form_name = backend.subject
        self.assertEqual(
            mail_form_name,
            xml_find(
                f'{ns}extensions/{ns}extension/{ns2}solutionDefinition/'
                f'{ns2}solutionPropertiesExtension/{ns2}mail'
            ).get('formName')
        )

    def test_manifest_xsf_02(self):
        "Test Image fk field."
        body_map = {'user_id': 1, 'image': ''}
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact', body_map=body_map, model=Contact,
        )
        builder = self._get_builder(backend)

        content = builder._render_manifest_xsf(self.request)
        self.assertEqual(
            re.search(r'xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content)['ns'],
            builder.get_namespace()
        )  # Can't be got with ElementTree, because it's a namespace
        xsf = '{http://schemas.microsoft.com/office/infopath/2003/solutionDefinition}'
        xml = XML(content)

        xmlToEdit_node = xml.find(f'{xsf}views/{xsf}view/{xsf}editing/{xsf}xmlToEdit')
        self.assertIsNotNone(xmlToEdit_node)
        self.assertEqual('image', xmlToEdit_node.get('name'))
        self.assertEqual('/my:CremeCRMCrudity/my:image', xmlToEdit_node.get('item'))

        button_nodes = xml.findall(f'{xsf}views/{xsf}view/{xsf}menuArea/{xsf}button')
        self.assertTrue(button_nodes)
        self.assertSetEqual(
            {'image'}, {button_node.get('xmlToEdit') for button_node in button_nodes},
        )

    def test_manifest_xsf_03(self):
        "Test M2M field."
        # body_map = {'user_id': 1, 'language': ''}
        body_map = {'user_id': 1, 'languages': ''}
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact', body_map=body_map, model=Contact,
        )
        builder = self._get_builder(backend)

        content = builder._render_manifest_xsf(self.request)
        self.assertEqual(
            re.search(r'xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content)['ns'],
            builder.get_namespace()
        )  # Can't be got with ElementTree, because it's a namespace

        xsf = '{http://schemas.microsoft.com/office/infopath/2003/solutionDefinition}'
        xml2edit_node = XML(content).find(f'{xsf}views/{xsf}view/{xsf}editing/{xsf}xmlToEdit')
        self.assertIsNotNone(xml2edit_node)
        # self.assertEqual('language', xml2edit_node.get('name'))
        self.assertEqual('languages', xml2edit_node.get('name'))
        self.assertEqual(
            # '/my:CremeCRMCrudity/my:language/my:language_value',
            '/my:CremeCRMCrudity/my:languages/my:languages_value',
            xml2edit_node.get('item')
        )

        self.assertEqual('xTextList', xml2edit_node.find(f'{xsf}editWith').get('component'))

    def test_myschema_xsd01(self):
        body_map = {
            'user_id':     1,
            'first_name':  '',
            'last_name':   '',
            'email':       'none@none.com',
            'description': '',
            'birthday':    '',
            'created':     '',  # TODO: ignore this (editable=False)
            'url_site':    '',
            'image':       '',
            # 'language':    '',
            'languages':    '',
        }
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact', body_map=body_map, model=Contact,
        )
        builder = self._get_builder(backend)
        xsd = '{http://www.w3.org/2001/XMLSchema}'

        content = builder._render_myschema_xsd(self.request)
        xml = XML(content)

        self.assertEqual(builder.namespace, xml.get('targetNamespace'))
        self.assertEqual(
            builder.namespace,
            re.search(r'xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content)['ns'],
        )  # Can't be got with ElementTree, because it's a namespace

        ref_attrs = {
            node.get('ref')
            for node in xml.findall(f'{xsd}element/{xsd}complexType/{xsd}sequence/{xsd}element')
        }
        # chain() because language_value is not declared in body_map, only language has to (m2m)
        # expected_ref_attrs = {f'my:{key}' for key in chain(body_map, ['language_value'])}
        expected_ref_attrs = {f'my:{key}' for key in chain(body_map, ['languages_value'])}
        self.assertEqual(expected_ref_attrs, ref_attrs)

        xsd_elements = {
            'CremeCRMCrudity': {'name': 'CremeCRMCrudity'},

            # <xsd:element name="user_id" type="xsd:integer"/>
            'user_id': {'name': 'user_id', 'type': 'xsd:integer'},

            # # <xsd:element name="is_actived" type="xsd:boolean"/>
            # 'is_actived': {'name': 'is_actived', 'type': 'xsd:boolean'},

            # TODO: check if my:requiredString accepts empty strings
            # # <xsd:element name="first_name" type="xsd:string"/>
            # 'first_name': {'name': 'first_name', 'type': 'xsd:string'},
            # <xsd:element name="first_name" type="my:requiredString"/>
            'first_name': {'name': 'first_name', 'type': 'my:requiredString'},

            # <xsd:element name="last_name" type="xsd:requiredString"/>
            'last_name': {'name': 'last_name', 'type': 'my:requiredString'},

            # TODO: check if my:requiredString accepts empty strings
            # # <xsd:element name="email" type="xsd:string"/>
            # 'email': {'name': 'email', 'type': 'xsd:string'},
            # <xsd:element name="email" type="my:requiredString"/>
            'email': {'name': 'email', 'type': 'my:requiredString'},

            # <xsd:element name="description">
            #   <xsd:complexType mixed="true">
            #     <xsd:sequence>
            #       <xsd:any minOccurs="0" maxOccurs="unbounded"
            #                namespace="http://www.w3.org/1999/xhtml" processContents="lax"/>
            #     </xsd:sequence>
            #   </xsd:complexType>
            # </xsd:element>
            'description': {'name': 'description'},

            # <xsd:element name="birthday" nillable="true" type="xsd:date"/>
            'birthday': {'name': 'birthday', 'type': 'xsd:date', 'nillable': 'true'},

            # <xsd:element name="created" type="xsd:dateTime"/>
            'created': {'name': 'created', 'type': 'xsd:dateTime'},

            # TODO: check if my:requiredAnyURI accepts empty strings
            # 'url_site':       {'name': 'url_site', 'type': 'xsd:anyURI'},
            'url_site': {'name': 'url_site', 'type': 'my:requiredAnyURI'},

            'image': {'name': 'image', 'type': 'xsd:base64Binary', 'nillable': 'true'},

            # 'language': {'name': 'language'},
            'languages': {'name': 'languages'},
            # 'language_value': {
            #     'name': 'language_value', 'type': 'xsd:integer', 'nillable': 'true',
            # },
            'languages_value': {
                'name': 'languages_value', 'type': 'xsd:integer', 'nillable': 'true',
            },
        }

        for element_node in xml.findall(f'{xsd}element'):
            name = element_node.get('name')
            # xsd_element_attrs = xsd_elements.get(name)
            xsd_element_attrs = xsd_elements.pop(name, None)

            if xsd_element_attrs is None:
                self.fail(f'There is at least an extra node named: {name}')

            self.assertSetEqual({*xsd_element_attrs.keys()}, {*element_node.keys()})

            for attr in element_node.keys():
                # self.assertEqual(xsd_element_attrs[attr], element_node.get(attr))
                # TODO: factorise
                expected = xsd_element_attrs[attr]
                value = element_node.get(attr)

                if expected != value:
                    self.fail(
                        f'Value of attribute "{attr}" in node "{name}" is wrong: '
                        f'expected "{expected}", got "{value}".'
                    )

        self.assertFalse(
            xsd_elements,
            f'The elements with the following names have not been found: {xsd_elements}'
        )

    @skipIfCustomDocument
    def test_myschema_xsd02(self):
        "With Document."
        body_map = {
            'user_id': 1, 'title': '',
            'description': '', 'linked_folder': '', 'filedata': '',
        }
        backend = self._get_backend(
            DocumentFakeBackend,
            subject='create_doc', body_map=body_map, model=Document,
        )
        builder = self._get_builder(backend)
        xsd = '{http://www.w3.org/2001/XMLSchema}'

        content = builder._render_myschema_xsd(self.request)
        xml = XML(content)

        self.assertEqual(builder.namespace, xml.get('targetNamespace'))
        self.assertEqual(
            builder.namespace,
            re.search(r'xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content)['ns'],
        )  # Can't be got with ElementTree, because it's a namespace

        ref_attrs = {
            node.get('ref')
            for node in xml.findall(f'{xsd}element/{xsd}complexType/{xsd}sequence/{xsd}element')
        }
        expected_ref_attrs = {f'my:{key}' for key in body_map}
        self.assertEqual(expected_ref_attrs, ref_attrs)

        xsd_elements = {
            'CremeCRMCrudity': {'name': 'CremeCRMCrudity'},
            # <xsd:element name="user_id" type="xsd:integer"/>
            'user_id': {'name': 'user_id', 'type': 'xsd:integer'},
            # <xsd:element name="first_name" type="xsd:requiredString"/>
            'title':   {'name': 'title', 'type': 'my:requiredString'},
            # <xsd:element name="description">
            #   <xsd:complexType mixed="true">
            #       <xsd:sequence>
            #           <xsd:any minOccurs="0" maxOccurs="unbounded"
            #                    namespace="http://www.w3.org/1999/xhtml" processContents="lax"/>
            #       </xsd:sequence>
            #   </xsd:complexType>
            # </xsd:element>
            'description': {'name': 'description'},
            'linked_folder': {'name': 'linked_folder', 'type': 'xsd:integer'},
            'filedata':    {'name': 'filedata', 'type': 'my:requiredBase64Binary'},
        }

        for element_node in xml.findall(f'{xsd}element'):
            xsd_element_attrs = xsd_elements.pop(element_node.get('name'))

            if xsd_element_attrs is None:
                self.fail(
                    f'There is at least an extra node named: {element_node.get("name")}'
                )

            self.assertSetEqual({*xsd_element_attrs.keys()}, {*element_node.keys()})

            for attr in element_node.keys():
                self.assertEqual(xsd_element_attrs[attr], element_node.get(attr))

        self.assertFalse(
            xsd_elements,
            f'The elements with the following names have not been found: {xsd_elements}'
        )

    def test_template_xml01(self):
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact',
            model=Contact,
            body_map={
                'user_id':     1,
                'first_name':  '',
                'last_name':   '',
                'email':       'none@none.com',
                'description': '',
                'birthday':    '',
                'created':     '',
                'url_site':    '',
                'image':       '',
            },
        )
        builder = self._get_builder(backend)

        content = builder._render_template_xml(self.request)
        self.assertEqual(
            re.search(r'xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content)['ns'],
            builder.get_namespace()
        )  # Can't be got with ElementTree, because it's a namespace

        xsi = '{http://www.w3.org/2001/XMLSchema-instance}'
        find = XML(content).find

        for field in builder.fields:
            field_node = find('{%s}%s' % (builder.namespace, field.name))
            self.assertIsNotNone(field_node)  # Beware: bool(field_node) doesn't work !
            if field.is_nillable:
                self.assertEqual('true', field_node.get(f'{xsi}nil'))

    def test_upgrade_xsl01(self):
        body_map = {
            'user_id':     1,
            'first_name':  '',
            'last_name':   '',
            'email':       'none@none.com',
            'description': '',
            'birthday':    '',
            'created':     '',
            'url_site':    '',
            'image':       '',
        }
        builder = self._get_builder(self._get_backend(
            ContactFakeBackend,
            subject='create_contact', model=Contact, body_map=body_map,
        ))

        content = builder._render_upgrade_xsl(self.request)
        self.assertEqual(
            re.search(r'xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content)['ns'],
            builder.namespace
        )  # Can't be got with ElementTree, because it's a namespace

        self.assertSetEqual(
            {f'my:{field_name}' for field_name in body_map},
            {
                node.get('name')
                for node in XML(content).findall(
                    '{xsl}template/{xsl}copy/{xsl}element'.format(
                        xsl='{http://www.w3.org/1999/XSL/Transform}',
                    )
                )
            },
        )

    def test_upgrade_xsl02(self):
        "Many2Many."
        # body_map = {'user_id': 1, 'language': ''}
        body_map = {'user_id': 1, 'languages': ''}
        builder = self._get_builder(self._get_backend(
            ContactFakeBackend,
            subject='create_contact', body_map=body_map, model=Contact,
        ))

        content = builder._render_upgrade_xsl(self.request)
        self.assertEqual(
            re.search(r'xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content)['ns'],
            builder.namespace,
        )

        xsl = '{http://www.w3.org/1999/XSL/Transform}'
        findall = XML(content).findall

        # TODO: use it ??
        # fields_names = set("my:%s" % field_name for field_name in body_map.iterkeys())
        template_nodes = [
            n
            for n in findall(f'{xsl}template')
            if n.get('match') == 'my:CremeCRMCrudity'
        ]
        self.assertTrue(template_nodes)

        when_node = template_nodes[0].find(f'{xsl}copy/{xsl}choose/{xsl}when')
        # self.assertEqual('my:language', when_node.get('test'))
        self.assertEqual('my:languages', when_node.get('test'))

        # expected_names = {'my:language', 'my:language_value'}
        expected_names = {'my:languages', 'my:languages_value'}
        self.assertSetEqual(
            expected_names,
            {
                match
                for match in (n.get('match') for n in findall(f'{xsl}template'))
                if match in expected_names
            },
        )

    def _get_view_xsl(self, backend, body_map):
        backend.body_map = body_map
        builder = self._get_builder(backend)

        content = builder._render_view_xsl(self.request)
        self.assertEqual(
            re.search(r'xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content)['ns'],
            builder.namespace,
        )

        return XML(content.encode('utf-8'))

    def _test_view_xsl_01(self, backend, field_name, attrs, node_type='span'):
        xsl = '{http://www.w3.org/1999/XSL/Transform}'
        xd = '{http://schemas.microsoft.com/office/infopath/2003}'

        xml = self._get_view_xsl(backend, {field_name: ''})
        node_vb = xml.find(f'{xsl}template/div/div/table/tbody/tr/td/div/font/strong')
        self.assertIsNotNone(node_vb)
        self.assertEqual(
            backend.model._meta.get_field(field_name).verbose_name,
            node_vb.text,
        )

        node_content = xml.find(f'{xsl}template/div/div/table/tbody/tr/td/div/font/{node_type}')
        for attr, expected_value in attrs.items():
            self.assertEqual(
                expected_value,
                node_content.get(attr.format(xsl=xsl, xd=xd)),
            )

    def test_view_xsl01(self):
        "Simple attributes verification."
        fields = {
            'first_name': ({
                'class':       'xdTextBox',
                '{xd}CtrlId':  'first_name',
                '{xd}xctname': 'PlainText',
                '{xd}binding': 'my:first_name',
            }, 'span'),
            'last_name': ({
                'class':       'xdTextBox',
                '{xd}CtrlId':  'last_name',
                '{xd}xctname': 'PlainText',
                '{xd}binding': 'my:last_name',
            }, 'span'),
            'email': ({
                'class':       'xdTextBox',
                '{xd}CtrlId':  'email',
                '{xd}xctname': 'PlainText',
                '{xd}binding': 'my:email',
            }, 'span'),
            'url_site': ({
                'class':       'xdTextBox',
                '{xd}CtrlId':  'url_site',
                '{xd}xctname': 'PlainText',
                '{xd}binding': 'my:url_site',
            }, 'span'),
            'description': ({
                'class':           'xdRichTextBox',
                '{xd}CtrlId':      'description',
                '{xd}xctname':     'RichText',
                '{xd}binding':     'my:description',
                'contentEditable': 'true',
            }, 'span'),
            'birthday': ({
                'class':       'xdDTPicker',
                '{xd}CtrlId':  'birthday',
                '{xd}xctname': 'DTPicker',
            }, 'div'),
            'created': ({  # TODO: remove (not editable)
                'class':       'xdDTPicker',
                '{xd}CtrlId':  'created',
                '{xd}xctname': 'DTPicker',
            }, 'div'),
            'image': ({
                'class':       'xdFileAttachment',
                '{xd}CtrlId':  'image',
                '{xd}xctname': 'FileAttachment',
                '{xd}binding': 'my:image',
            }, 'span'),
        }

        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact', body_map={}, model=Contact,
        )

        for field_name, attrs_nodetype in fields.items():
            attrs, node_type = attrs_nodetype
            self._test_view_xsl_01(backend, field_name, attrs, node_type)

    def test_view_xsl02(self):
        "Deeper with DateField"
        xsl = '{http://www.w3.org/1999/XSL/Transform}'
        field_name = 'birthday'
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact', body_map={field_name: ''}, model=Contact,
        )
        xml = self._get_view_xsl(backend, {field_name: ''})
        node_vb = xml.find(f'{xsl}template/div/div/table/tbody/tr/td/div/font/strong')
        self.assertIsNotNone(node_vb)
        self.assertEqual(Contact._meta.get_field(field_name).verbose_name, node_vb.text)

        target_node = xml.find(f'{xsl}template/div/div/table/tbody/tr/td/div/font/div/span')
        self.assertEqual(
            f'my:{field_name}',
            target_node.find(f'{xsl}attribute/{xsl}value-of').get('select')
        )

    def test_view_xsl03(self):
        "Deeper with ForeignKey."
        xsl = '{http://www.w3.org/1999/XSL/Transform}'
        xd  = '{http://schemas.microsoft.com/office/infopath/2003}'

        field_name = 'user_id'
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact', body_map={field_name: ''}, model=Contact,
        )
        xml = self._get_view_xsl(backend, {field_name: ''})

        node_vb = xml.find(f'{xsl}template/div/div/table/tbody/tr/td/div/font/strong')
        self.assertIsNotNone(node_vb)
        self.assertEqual(Contact._meta.get_field('user').verbose_name, node_vb.text)

        attrs = {
            'class':        'xdComboBox xdBehavior_Select',
            f'{xd}xctname': 'dropdown',
            f'{xd}CtrlId':  field_name,
            f'{xd}binding': f'my:{field_name}',
        }
        target_node = xml.find(f'{xsl}template/div/div/table/tbody/tr/td/div/font/select')
        for attr, expected_value in attrs.items():
            self.assertEqual(expected_value, target_node.get(attr))

        options = target_node.findall('option')
        self.assertTrue(options)  # At least, it must have empty choice

        self.assertSetEqual(
            {
                (f'my:{field_name}=""', _('Select...')),
                *(
                    (f'my:{field_name}="{user.pk}"', str(user))
                    for user in get_user_model().objects.all()
                ),
            },
            {
                (
                    option.find(f'{xsl}if').get('test'),
                    re.search(
                        r'if>(?P<username>.*)</option>',
                        tostring(option, encoding='utf8').decode('utf8')
                    )['username']
                )
                for option in options
            },
        )

    @skipIfCustomDocument
    def test_view_xsl04(self):
        "Simple attr verification for Document"
        fields = {
            'title': ({
                'class':       'xdTextBox',
                '{xd}CtrlId':  'title',
                '{xd}xctname': 'PlainText',
                '{xd}binding': 'my:title',
            }, 'span'),
            'description': ({
                'class':           'xdRichTextBox',
                '{xd}CtrlId':      'description',
                '{xd}xctname':     'RichText',
                '{xd}binding':     'my:description',
                'contentEditable': 'true',
            }, 'span'),
            'filedata': ({
                'class':       'xdFileAttachment',
                '{xd}CtrlId':  'filedata',
                '{xd}xctname': 'FileAttachment',
                '{xd}binding': 'my:filedata',
            }, 'span'),
            'linked_folder': ({
                'class':       'xdComboBox xdBehavior_Select',
                '{xd}CtrlId':  'linked_folder',
                '{xd}xctname': 'dropdown',
                '{xd}binding': 'my:linked_folder',
            }, 'select'),
        }

        backend = self._get_backend(
            DocumentFakeBackend,
            subject='create_doc', body_map={}, model=Document,
        )

        for field_name, attrs_nodetype in fields.items():
            attrs, node_type = attrs_nodetype
            self._test_view_xsl_01(backend, field_name, attrs, node_type)

    def test_view_xsl05(self):
        "Deeper with Many2Many."
        languages = Language.objects.all()
        self.assertTrue(languages)

        xsl = '{http://www.w3.org/1999/XSL/Transform}'
        xd = '{http://schemas.microsoft.com/office/infopath/2003}'

        # field_name = 'language'
        field_name = 'languages'
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact', body_map={field_name: ''}, model=Contact,
        )
        xml = self._get_view_xsl(backend, {field_name: ''})

        node_vb = xml.find(f'{xsl}template/div/div/table/tbody/tr/td/div/font/strong')
        self.assertIsNotNone(node_vb)
        self.assertEqual(
            Contact._meta.get_field(field_name).verbose_name,
            node_vb.text
        )

        target_node = xml.find(f'{xsl}template/div/div/table/tbody/tr/td/div/font/div')
        self.assertIsNotNone(target_node)

        input_nodes = target_node.findall(f'{xsl}choose/{xsl}when/span/span/input')
        self.assertTrue(input_nodes)

        self.assertSetEqual(
            {str(language) for language in languages},
            {input_node.get('title') for input_node in input_nodes}
        )
        self.assertSetEqual(
            # {f'my:language/my:language_value[.="{lang.id}"][1]' for lang in languages},
            {f'my:languages/my:languages_value[.="{lang.id}"][1]' for lang in languages},
            {input_node.get(f'{xd}binding') for input_node in input_nodes},
        )
        self.assertEqual(
            # {f'my:language/my:language_value[.="{lang.id}"][1]' for lang in languages},
            {f'my:languages/my:languages_value[.="{lang.id}"][1]' for lang in languages},
            {
                input_node.get('select')
                for input_node in target_node.findall(
                    f'{xsl}choose/{xsl}when/span/span/input/{xsl}attribute/{xsl}value-of'
                )
            },
        )

        self.assertSetEqual(
            # {f'my:language/my:language_value="{lang.id}"' for lang in languages},
            {f'my:languages/my:languages_value="{lang.id}"' for lang in languages},
            {
                input_node.get('test')
                for input_node in target_node.findall(
                    f'{xsl}choose/{xsl}when/span/span/input/{xsl}if'
                )
            },
        )

        for_each_node = target_node.find(f'{xsl}choose/{xsl}when/span/{xsl}for-each')
        self.assertIsNotNone(for_each_node)
        self.assertEqual(
            # 'my:language/my:language_value[{}]'.format(
            'my:languages/my:languages_value[{}]'.format(
                ' and '.join(f'.!="{lang.id}"' for lang in languages)
            ),
            for_each_node.get('select'),
        )

    @skipIf(lcabMissing, 'Lcab seems not installed')
    def test_render01(self):
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact',
            body_map={
                'user_id':     1,
                'first_name':  '',
                'last_name':   '',
                'email':       'none@none.com',
                'description': '',
                'birthday':    '',
                'created':     '',
                'url_site':    '',
            },
        )
        builder = self._get_builder(backend)
        content = builder.render().content

        self.longMessage = False
        error_msg = 'Not found in (truncated): {}'.format(content[:100])
        self.assertIn(b'<my:first_name></my:first_name>',            content, error_msg)
        self.assertIn(b'<my:last_name></my:last_name>',              content, error_msg)
        self.assertIn(b'<my:birthday xsi:nil="true"></my:birthday>', content, error_msg)

    def test_get_create_form_view01(self):
        "Backend not registered"
        registry.crudity_registry = crudity_registry = registry.CRUDityRegistry()
        crudity_registry.autodiscover()
        registry.crudity_registry.dispatch([
            {
                'fetcher':     'email',
                'input':       'raw',  # not 'infopath',
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATE CONTACT',
            },
        ])
        self.assertGET404(reverse(
            'crudity__dl_infopath_form',
            args=(CrudityBackend.normalize_subject('CREATE CONTACT'),)
        ))

    def test_get_create_form_view02(self):
        registry.crudity_registry = crudity_registry = registry.CRUDityRegistry()
        crudity_registry.autodiscover()
        registry.crudity_registry.dispatch([
            {
                'fetcher':     'email',
                'input':       'infopath',
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATE CONTACT',
            },
        ])
        self.assertGET404(reverse(
            'crudity__dl_infopath_form',
            args=(CrudityBackend.normalize_subject('CREATE UNKNOWN'),)
        ))

    @skipIf(lcabMissing, 'Lcab seems not installed')
    def test_get_create_form_view03(self):
        subject = 'CREATE CONTACT'

        registry.crudity_registry = crudity_registry = registry.CRUDityRegistry()
        crudity_registry.autodiscover()
        registry.crudity_registry.dispatch([
            {
                'fetcher':     'email',
                'input':       'infopath',
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     subject,
            },
        ])

        response = self.assertGET200(reverse(
            'crudity__dl_infopath_form',
            args=(CrudityBackend.normalize_subject(subject),)
        ))
        self.assertEqual('application/vnd.ms-infopath', response['Content-Type'])


class InfopathFormFieldTestCase(CrudityTestCase):
    def setUp(self):
        super().setUp()
        # TODO: factorise
        self.request = request = RequestFactory().get('/')  # Url doesn't matter
        request.user = self.login()

    def _get_backend(self, backend_klass, **backend_cfg):
        return backend_klass(config=backend_cfg)

    def test_uuid01(self):
        "uuid for a field has to be unique and the same BY FORM (so by backend)"
        request = self.request

        # Backend 1
        backend1 = self._get_backend(ContactFakeBackend, subject='create_ce')
        builder1 = InfopathFormBuilder(request=request, backend=backend1)
        uuid1 = InfopathFormField(builder1.urn, CremeEntity, 'user_id', request).uuid
        for i in range(10):
            self.assertEqual(
                uuid1,
                InfopathFormField(builder1.urn, CremeEntity, 'user_id', request).uuid,
            )

        # Backend 2
        backend2 = self._get_backend(ContactFakeBackend, subject='create_ce2')
        builder2 = InfopathFormBuilder(request=request, backend=backend2)

        uuid2 = InfopathFormField(builder2.urn, CremeEntity, 'user_id', request).uuid
        for i in range(10):
            self.assertEqual(
                uuid2,
                InfopathFormField(builder2.urn, CremeEntity, 'user_id', request).uuid,
            )

        self.assertNotEqual(uuid2, uuid1)

        # Backend 3
        backend3 = self._get_backend(ContactFakeBackend, subject='create_contact', model=Contact)
        builder3 = InfopathFormBuilder(request=request, backend=backend3)

        uuid3 = InfopathFormField(builder3.urn, Contact, 'user_id', request).uuid
        for i in range(10):
            self.assertEqual(
                uuid3,
                InfopathFormField(builder3.urn, Contact, 'user_id', request).uuid,
            )

        self.assertNotEqual(uuid1, uuid3)
        self.assertNotEqual(uuid2, uuid3)

        uuid4 = InfopathFormField(builder1.urn, CremeEntity, 'user_id', request).uuid
        self.assertEqual(uuid1, uuid4)

    def test_get_field01(self):
        request = self.request
        body_map = {
            'user_id': 1,
            'first_name': '', 'last_name': '',
            'email': 'none@none.com', 'description': '', 'birthday': '',
        }

        backend = self._get_backend(
            ContactFakeBackend, subject='create_contact', body_map=body_map,
        )
        urn = InfopathFormBuilder(request=request, backend=backend).urn

        def get_model_field(fname):
            return InfopathFormField(urn, Contact, fname, request)._get_model_field()

        get_field = Contact._meta.get_field
        self.assertEqual(get_field('user'),        get_model_field('user_id'))
        self.assertEqual(get_field('first_name'),  get_model_field('first_name'))
        self.assertEqual(get_field('last_name'),   get_model_field('last_name'))
        self.assertEqual(get_field('email'),       get_model_field('email'))
        self.assertEqual(get_field('description'), get_model_field('description'))
        self.assertEqual(get_field('birthday'),    get_model_field('birthday'))

        self.assertRaises(FieldDoesNotExist, get_model_field, 'email_id')

    def test_get_choices01(self):
        request = self.request
        backend = self._get_backend(
            ContactFakeBackend,
            subject='create_contact', body_map={'user_id': 1},
        )
        urn = InfopathFormBuilder(request=request, backend=backend).urn
        self.assertSetEqual(
            {(user.pk, str(user)) for user in get_user_model().objects.all()},
            {*InfopathFormField(urn, Contact, 'user_id', request)._get_choices()},
        )
