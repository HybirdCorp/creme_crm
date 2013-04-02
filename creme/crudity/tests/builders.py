# -*- coding: utf-8 -*-

try:
    from itertools import chain
    import re
    import os
    from xml.etree.ElementTree import XML, tostring # Element

    from django.contrib.auth.models import User
    from django.db.models.fields import FieldDoesNotExist
    #from django.utils import translation
    from django.utils.translation import ugettext as _
    from django.test.client import RequestFactory

    from creme.creme_core.models import CremeEntity, Language

    from creme.crudity.backends.models import CrudityBackend
    from creme.crudity.builders.infopath import InfopathFormBuilder, InfopathFormField
    from creme.crudity.registry import crudity_registry #CRUDityRegistry
    from creme.crudity.tests.base import CrudityTestCase, ContactFakeBackend, DocumentFakeBackend, FakeFetcher, FakeInput

    from creme.documents.models import Document

    from creme.persons.models import Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class InfopathFormBuilderTestCase(CrudityTestCase):
    def setUp(self):
        super(InfopathFormBuilderTestCase, self).setUp()
#        crudity_registry = CRUDityRegistry()
        #self.response = self.client.get('/')#Url doesn't matter
        #self.request  = self.response.context['request']
        self.request = RequestFactory().get('/') #Url doesn't matter
        self.request.LANGUAGE_CODE = '1033' #en

    def _get_builder(self, backend):
        return InfopathFormBuilder(request=self.request, backend=backend)

    def _get_backend(self, backend_klass, **backend_cfg):
        return backend_klass(config=backend_cfg)

    def test_builder_01(self):
        class DummyCrudityBackend(CrudityBackend):
            pass
        self.assertRaises(AssertionError, self._get_builder, DummyCrudityBackend({}))

    def test_builder_02(self):
        backend = self._get_backend(ContactFakeBackend, subject="create_ce")
        builder = self._get_builder(backend)

        now = builder.now
        now_str = now.strftime('%Y-%m-%dT%H:%M:%S')

        expected_urn = "urn:schemas-microsoft-com:office:infopath:%s:-myXSD-%s" % ("create-create_ce", now_str)

        self.assertEqual("http://schemas.microsoft.com/office/infopath/2003/myXSD/%s" % now_str, builder.namespace)
        self.assertEqual(expected_urn, builder.urn)

    def test_builder_get_lang(self):
        backend = self._get_backend(ContactFakeBackend, subject="create_ce")
        builder = self._get_builder(backend)

        #translation.activate("fr")
        #response = self.client.get('/')
        #request  = response.context['request']

        #self.assertEqual("1036", builder._get_lang_code(request.LANGUAGE_CODE))
        self.assertEqual("1036", builder._get_lang_code('fr'))

    def test_builder_fields_property(self):
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    model=Contact,
                                    body_map={'user_id': 1, 'is_actived': True, "first_name":"",
                                              "last_name":"", "email": "none@none.com",
                                              "description": "", "birthday":""
                                             },
                                    password="creme"
                                   )
        builder = self._get_builder(backend)

        for field in builder.fields:
            self.assertIn(field.name, backend.body_map)
            self.assertEqual(Contact, field.model)

        for field in builder.fields:#Two passes because of cache
            self.assertIn(field.name, backend.body_map)
            self.assertEqual(Contact, field.model)

    def test_manifest_xsf_01(self):#Test some base values
        backend = self._get_backend(ContactFakeBackend, subject="create_ce")
        builder = self._get_builder(backend)
        xsf_ns  = "{http://schemas.microsoft.com/office/infopath/2003/solutionDefinition}"
        d_ns    = {'ns': xsf_ns, 'ns2': "{http://schemas.microsoft.com/office/infopath/2006/solutionDefinition/extensions}"}

        content = builder._render_manifest_xsf(self.request)
        xml = XML(content)
        xml_find = xml.find

        self.assertEqual(re.search('xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content).groupdict()['ns'], builder.get_namespace())#Can't be got with ElementTree, because it's a namespace

        self.assertEqual(builder.get_urn(), xml.get('name'))
        self.assertEqual(builder.get_namespace(), xml_find('%(ns)spackage/%(ns)sfiles/%(ns)sfile/%(ns)sfileProperties/%(ns)sproperty' % d_ns).get('value'))
        self.assertEqual(builder.get_namespace(), xml_find('%(ns)sapplicationParameters/%(ns)ssolutionProperties' % d_ns).get('fullyEditableNamespace'))
        self.assertEqual(builder.get_namespace(), xml_find('%(ns)sdocumentSchemas/%(ns)sdocumentSchema' % d_ns).get('location').split()[0])

        #file_nodes = xml.findall('%(ns)spackage/%(ns)sfiles/%(ns)sfile/' % d_ns)#ElementTree 1.2.6 (shipped with python <= 2.6) doesn't support advanced xpath expressions
        file_nodes = xml.findall('%(ns)spackage/%(ns)sfiles/%(ns)sfile' % d_ns)#ElementTree 1.2.6 (shipped with python <= 2.6) doesn't support advanced xpath expressions
        found_node = None
        for node in file_nodes:
            if node.get('name') == "view1.xsl":
                found_node = node
                break
        else:
            self.fail('<xsf:file name="view1.xsl"> not found')

        property_node = None
        for node in found_node.findall('%(ns)sfileProperties/%(ns)sproperty' % d_ns):
            if node.get('name') == "lang":
                property_node = node
                self.assertEqual(builder._get_lang_code(self.request.LANGUAGE_CODE), node.get('value'))
                break
        else:
            self.fail('<xsf:property name="lang" type="string" value=""></xsf:property> not found')

        #TODO: use 'property_node'

        mail_form_name = backend.subject
        self.assertEqual(mail_form_name, xml_find('%(ns)sextensions/%(ns)sextension/%(ns2)ssolutionDefinition/%(ns2)ssolutionPropertiesExtension/%(ns2)smail' % d_ns).get('formName'))

    def test_manifest_xsf_02(self):#Test Image fk field
        body_map= {'user_id': 1, "image":""}
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map=body_map, model=Contact
                                   )
        builder = self._get_builder(backend)

        content = builder._render_manifest_xsf(self.request)
        self.assertEqual(re.search('xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content).groupdict()['ns'], builder.get_namespace())#Can't be got with ElementTree, because it's a namespace
        d_ns = {'xsf': "{http://schemas.microsoft.com/office/infopath/2003/solutionDefinition}"}
        xml  = XML(content)

        xmlToEdit_node = xml.find('%(xsf)sviews/%(xsf)sview/%(xsf)sediting/%(xsf)sxmlToEdit' % d_ns)
        self.assertIsNotNone(xmlToEdit_node)
        self.assertEqual("image", xmlToEdit_node.get('name'))
        self.assertEqual("/my:CremeCRMCrudity/my:image", xmlToEdit_node.get('item'))

        button_nodes = xml.findall('%(xsf)sviews/%(xsf)sview/%(xsf)smenuArea/%(xsf)sbutton' % d_ns)
        self.assertTrue(button_nodes)
        xmlToEdit_set = set(['image',])
        self.assertEqual(xmlToEdit_set, set(button_node.get('xmlToEdit') for button_node in button_nodes))

    def test_manifest_xsf_03(self):#Test m2m field
        body_map= {'user_id': 1, "language":""}
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map=body_map, model=Contact
                                   )
        builder = self._get_builder(backend)

        content = builder._render_manifest_xsf(self.request)
        self.assertEqual(re.search('xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content).groupdict()['ns'], builder.get_namespace())#Can't be got with ElementTree, because it's a namespace

        d_ns = {'xsf': "{http://schemas.microsoft.com/office/infopath/2003/solutionDefinition}"}
        xml  = XML(content)

        xmlToEdit_node = xml.find('%(xsf)sviews/%(xsf)sview/%(xsf)sediting/%(xsf)sxmlToEdit' % d_ns)
        self.assertIsNotNone(xmlToEdit_node)
        self.assertEqual("language", xmlToEdit_node.get('name'))
        self.assertEqual("/my:CremeCRMCrudity/my:language/my:language_value", xmlToEdit_node.get('item'))

        editWith_node = xmlToEdit_node.find('%(xsf)seditWith' % d_ns)
        self.assertEqual("xTextList", editWith_node.get('component'))

    def test_myschema_xsd01(self):
        body_map = {'user_id': 1, 'is_actived': True, "first_name": "", "last_name": "",
                    'email': 'none@none.com', 'description': "", "birthday": "",
                    "created":"", 'url_site': "", "image": "", "language": ""
                   }
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map=body_map, model=Contact
                                   )
        builder = self._get_builder(backend)
        d_ns    = {'xsd': "{http://www.w3.org/2001/XMLSchema}"}

        content = builder._render_myschema_xsd(self.request)
        xml     = XML(content)

        self.assertEqual(builder.namespace, xml.get('targetNamespace'))
        self.assertEqual(builder.namespace, re.search('xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content).groupdict()['ns'])#Can't be got with ElementTree, because it's a namespace

        ref_attrs = set(node.get('ref') for node in xml.findall('%(xsd)selement/%(xsd)scomplexType/%(xsd)ssequence/%(xsd)selement' % d_ns))
        expected_ref_attrs = set('my:%s' % key for key in chain(body_map.iterkeys(), ['language_value']))#chain because language_value is not declared in body_map, only language has to (m2m)
        self.assertEqual(expected_ref_attrs, ref_attrs)

        xsd_elements = {'CremeCRMCrudity': {'name': 'CremeCRMCrudity'},
                        'user_id':         {'name': 'user_id',    'type': 'xsd:integer'},#"""<xsd:element name="user_id" type="xsd:integer"/>""",
                        'is_actived':      {'name': 'is_actived', 'type': 'xsd:boolean'},#"""<xsd:element name="is_actived" type="xsd:boolean"/>""",
                        'first_name':      {'name': 'first_name', 'type': 'xsd:string'},#"""<xsd:element name="first_name" type="xsd:requiredString"/>""",
                        'last_name':       {'name': 'last_name',  'type': 'my:requiredString'},#"""<xsd:element name="last_name" type="xsd:requiredString"/>""",
                        'email':           {'name': 'email',      'type': 'xsd:string'},#"""<xsd:element name="email" type="xsd:string"/>""",
                        'description':     {'name': 'description'},#"""<xsd:element name="description"><xsd:complexType mixed="true"><xsd:sequence><xsd:any minOccurs="0" maxOccurs="unbounded" namespace="http://www.w3.org/1999/xhtml" processContents="lax"/></xsd:sequence></xsd:complexType></xsd:element>""",
                        'birthday':        {'name': 'birthday',   'type': 'xsd:date',         'nillable': 'true'},#"""<xsd:element name="birthday" nillable="true" type="xsd:date"/>""",
                        'created':         {'name': 'created',    'type': 'xsd:dateTime'},#"""<xsd:element name="created" type="xsd:dateTime"/>""",
                        'url_site':        {'name': 'url_site',   'type': 'xsd:anyURI'},
                        'image':           {'name': 'image',      'type': 'xsd:base64Binary', 'nillable': 'true'},
                        'language':        {'name': 'language'},
                        'language_value':  {'name': 'language_value', "type": "xsd:integer", "nillable": "true"},
                       }

        for element_node in xml.findall('%(xsd)selement' % d_ns):
            name = element_node.get('name')
            xsd_element_attrs = xsd_elements.get(name)

            if xsd_element_attrs is None:
                self.fail("There is at least an extra node named: %s" % name)

            self.assertEqual(set(xsd_element_attrs.keys()), set(element_node.keys()))

            for attr in element_node.keys():
                self.assertEqual(xsd_element_attrs[attr], element_node.get(attr))

    def test_myschema_xsd02(self):#test with Document
        body_map = {'user_id': 1, "title": "",
                    "description": "", "folder":"", "filedata": ""
                   }
        backend = self._get_backend(DocumentFakeBackend, subject="create_doc",
                                    body_map=body_map, model=Document
                                   )
        builder = self._get_builder(backend)
        d_ns    = {'xsd': "{http://www.w3.org/2001/XMLSchema}"}

        content = builder._render_myschema_xsd(self.request)
        xml     = XML(content)

        self.assertEqual(builder.namespace, xml.get('targetNamespace'))
        self.assertEqual(builder.namespace, re.search('xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content).groupdict()['ns'])#Can't be got with ElementTree, because it's a namespace

        ref_attrs = set(node.get('ref') for node in xml.findall('%(xsd)selement/%(xsd)scomplexType/%(xsd)ssequence/%(xsd)selement' % d_ns))
        expected_ref_attrs = set('my:%s' % key for key in body_map.iterkeys())
        self.assertEqual(expected_ref_attrs, ref_attrs)

        xsd_elements = {'CremeCRMCrudity': {'name': 'CremeCRMCrudity'},
                        'user_id':     {'name': 'user_id', 'type': 'xsd:integer'},#"""<xsd:element name="user_id" type="xsd:integer"/>""",
                        "title":       {'name': 'title', 'type': 'my:requiredString'},#"""<xsd:element name="first_name" type="xsd:requiredString"/>""",
                        "description": {'name': 'description'},#"""<xsd:element name="description"><xsd:complexType mixed="true"><xsd:sequence><xsd:any minOccurs="0" maxOccurs="unbounded" namespace="http://www.w3.org/1999/xhtml" processContents="lax"/></xsd:sequence></xsd:complexType></xsd:element>""",
                        'folder':      {'name': 'folder', 'type': 'xsd:integer'},
                        "filedata":    {'name': 'filedata', 'type': 'my:requiredBase64Binary'},
                        }

        for element_node in xml.findall('%(xsd)selement' % d_ns):
            xsd_element_attrs = xsd_elements.get(element_node.get('name'))
            if xsd_element_attrs is not None:
                self.assertEqual(set(xsd_element_attrs.keys()), set(element_node.keys()))
                for attr in element_node.keys():
                    self.assertEqual(xsd_element_attrs[attr], element_node.get(attr))
            else:
                self.fail("There is at least an extra node named: %s" % element_node.get('name'))

    def test_template_xml01(self):
        body_map = {'user_id': 1, 'is_actived': True, "first_name": "",
                    "last_name": "", "email": "none@none.com", "description": "",
                    "birthday": "", "created": "", 'url_site': "", "image": ""
                   }
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map=body_map, model=Contact
                                   )
        builder = self._get_builder(backend)

        content = builder._render_template_xml(self.request)
        self.assertEqual(re.search('xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content).groupdict()['ns'], builder.get_namespace())#Can't be got with ElementTree, because it's a namespace

        d_ns    = {'my': builder.namespace, 'xsi': "{http://www.w3.org/2001/XMLSchema-instance}"}
        xml     = XML(content)

        for field in builder.fields:
            field_node = xml.find('{%s}%s' % (builder.namespace, field.name))
            self.assertIsNotNone(field_node)#Beware : bool(field_node) doesn't work !
            if field.is_nillable:
                self.assertEqual("true", field_node.get('%(xsi)snil' % d_ns))

    def test_upgrade_xsl01(self):
        body_map = {'user_id': 1, 'is_actived': True, "first_name":"",
                    "last_name":"", "email": "none@none.com", "description": "",
                    "birthday": "", "created": "", 'url_site': "", "image": ""
                   }
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map=body_map, model=Contact
                                   )
        builder = self._get_builder(backend)

        content = builder._render_upgrade_xsl(self.request)
        self.assertEqual(re.search('xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content).groupdict()['ns'],
                         builder.namespace
                        )#Can't be got with ElementTree, because it's a namespace

        d_ns = {'xsl': "{http://www.w3.org/1999/XSL/Transform}"}
        xml  = XML(content)
        self.assertEqual(set("my:%s" % field_name for field_name in body_map.iterkeys()),
                         #set(element_node.get('name') for element_node in xml.findall("%(xsl)stemplate/%(xsl)scopy/%(xsl)selement/" % d_ns))
                         set(node.get('name') for node in xml.findall("%(xsl)stemplate/%(xsl)scopy/%(xsl)selement" % d_ns))
                        )

    def test_upgrade_xsl02(self):#m2m
        body_map = {'user_id': 1, "language": ""}
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map=body_map, model=Contact
                                   )
        builder = self._get_builder(backend)

        content = builder._render_upgrade_xsl(self.request)
        self.assertEqual(re.search('xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content).groupdict()['ns'], builder.namespace)#Can't be got with ElementTree, because it's a namespace

        d_ns = {'xsl': "{http://www.w3.org/1999/XSL/Transform}"}
        xml  = XML(content)

        fields_names = set("my:%s" % field_name for field_name in body_map.iterkeys()) #TODO: use it ??
        template_nodes = filter(lambda x: x.get('match') == "my:CremeCRMCrudity", xml.findall("%(xsl)stemplate" % d_ns))
        self.assertTrue(template_nodes)
        when_node = template_nodes[0].find("%(xsl)scopy/%(xsl)schoose/%(xsl)swhen" % d_ns)
        self.assertEqual("my:language", when_node.get('test'))

        exptected_template_nodes_name = set(['my:language', 'my:language_value'])
        template_nodes_names = filter(lambda x: x.get('match') in exptected_template_nodes_name, xml.findall('%(xsl)stemplate' % d_ns))
        self.assertEqual(exptected_template_nodes_name, set(template_nodes_name.get('match') for template_nodes_name in template_nodes_names))

    def _get_view_xsl(self, backend, body_map):
        backend.body_map = body_map
        builder = self._get_builder(backend)

        content = builder._render_view_xsl(self.request)
        self.assertEqual(re.search('xmlns:my="(?P<ns>[\w\d\-:/\.]*)"', content).groupdict()['ns'],
                         builder.namespace
                        )#Can't be got with ElementTree, because it's a namespace

        return XML(content.encode('utf-8'))

    def _test_view_xsl_01(self, backend, field_name, attrs={}, node_type="span"):
        d_ns    = {'xsl': "{http://www.w3.org/1999/XSL/Transform}", 'xd': "{http://schemas.microsoft.com/office/infopath/2003}"}
        xml     = self._get_view_xsl(backend, {field_name: ""})
        node_vb =  xml.find('%(xsl)stemplate/div/div/table/tbody/tr/td/div/font/strong' % d_ns)
        self.assertIsNotNone(node_vb)
        self.assertEqual(backend.model._meta.get_field(field_name).verbose_name, node_vb.text)

        node_content =  xml.find(('%(xsl)stemplate/div/div/table/tbody/tr/td/div/font/' % d_ns)+node_type)
        for attr, expected_value in attrs.items():
            self.assertEqual(expected_value, node_content.get(attr % d_ns))

    def test_view_xsl01(self):#Simple attr verification
        fields = {
            "first_name": ({
                "class":         "xdTextBox",
                "%(xd)sCtrlId":  "first_name",
                "%(xd)sxctname": "PlainText",
                "%(xd)sbinding": "my:first_name",
            }, "span"),
            "last_name": ({
                "class":         "xdTextBox",
                "%(xd)sCtrlId":  "last_name",
                "%(xd)sxctname": "PlainText",
                "%(xd)sbinding": "my:last_name",
            },"span"),
            "email": ({
                "class":         "xdTextBox",
                "%(xd)sCtrlId":  "email",
                "%(xd)sxctname": "PlainText",
                "%(xd)sbinding": "my:email",
            },"span"),
            "url_site": ({
                "class":         "xdTextBox",
                "%(xd)sCtrlId":  "url_site",
                "%(xd)sxctname": "PlainText",
                "%(xd)sbinding": "my:url_site",
            },"span"),
            "description": ({
                "class":         "xdRichTextBox",
                "%(xd)sCtrlId":  "description",
                "%(xd)sxctname": "RichText",
                "%(xd)sbinding": "my:description",
                "contentEditable": "true",
            },"span"),
            "is_actived": ({
                "class":           "xdBehavior_Boolean",
                "%(xd)sCtrlId":    "is_actived",
                "%(xd)sxctname":   "CheckBox",
                "%(xd)sbinding":   "my:is_actived",
                "%(xd)sboundProp": "xd:value",
                "%(xd)soffValue":  "false",
                "%(xd)sonValue":   "true",
                "type":            "checkbox",
            },"input"),
            "birthday": ({
                "class":           "xdDTPicker",
                "%(xd)sCtrlId":    "birthday",
                "%(xd)sxctname":   "DTPicker",
            },"div"),
            "created": ({
                "class":           "xdDTPicker",
                "%(xd)sCtrlId":    "created",
                "%(xd)sxctname":   "DTPicker",
            },"div"),
            "image": ({
                "class":           "xdFileAttachment",
                "%(xd)sCtrlId":    "image",
                "%(xd)sxctname":   "FileAttachment",
                "%(xd)sbinding":   "my:image",
            },"span"),
        }

        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map={}, model=Contact
                                   )

        for field_name, attrs_nodetype in fields.iteritems():
            attrs, node_type = attrs_nodetype
            self._test_view_xsl_01(backend, field_name, attrs, node_type)

    def test_view_xsl02(self):#Deeper with DateField
        d_ns    = {'xsl': "{http://www.w3.org/1999/XSL/Transform}", 'xd': "{http://schemas.microsoft.com/office/infopath/2003}"}
        field_name = "birthday"
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map={field_name: ""}, model=Contact
                                   )
        xml     = self._get_view_xsl(backend, {field_name: ""})
        node_vb =  xml.find('%(xsl)stemplate/div/div/table/tbody/tr/td/div/font/strong' % d_ns)
        self.assertIsNotNone(node_vb)
        self.assertEqual(Contact._meta.get_field(field_name).verbose_name, node_vb.text)

        target_node = xml.find('%(xsl)stemplate/div/div/table/tbody/tr/td/div/font/div/span' % d_ns)
        self.assertEqual("my:%s" % field_name, target_node.find('%(xsl)sattribute/%(xsl)svalue-of' % d_ns).get('select'))

    def test_view_xsl03(self):#Deeper with ForeignKey
        d_ns    = {'xsl': "{http://www.w3.org/1999/XSL/Transform}", 'xd': "{http://schemas.microsoft.com/office/infopath/2003}"}
        field_name = "user_id"
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map={field_name: ""}, model=Contact
                                   )
        xml     = self._get_view_xsl(backend, {field_name: ""})

        node_vb =  xml.find('%(xsl)stemplate/div/div/table/tbody/tr/td/div/font/strong' % d_ns)
        self.assertIsNotNone(node_vb)
        self.assertEqual(Contact._meta.get_field("user").verbose_name, node_vb.text)

        attrs = {"class":"xdComboBox xdBehavior_Select", "%(xd)sxctname": "dropdown", "%(xd)sCtrlId": field_name, "%(xd)sbinding": "my:%s" % field_name}
        target_node =  xml.find('%(xsl)stemplate/div/div/table/tbody/tr/td/div/font/select' % d_ns)
        for attr, expected_value in attrs.iteritems():
            self.assertEqual(expected_value, target_node.get(attr % d_ns))

        options = target_node.findall('option')
        self.assertTrue(options)#At least, it must have empty choice

        default_choice_set = set([('my:%s=""' % field_name, _(u"Select..."))])
        users_set = set(('my:%s="%s"' % (field_name, user.pk), unicode(user)) for user in User.objects.all()) | default_choice_set

        options_set = set((option.find('%(xsl)sif' % d_ns).get('test'), re.search(r'if>(?P<username>.*)</option>', tostring(option, encoding='utf8').decode('utf8')).groupdict()['username']) for option in options)
        self.assertEqual(users_set, options_set)

    def test_view_xsl04(self):#Simple attr verification for Document
        fields = {
            "title": ({
                "class":         "xdTextBox",
                "%(xd)sCtrlId":  "title",
                "%(xd)sxctname": "PlainText",
                "%(xd)sbinding": "my:title",
            }, "span"),
            "description": ({
                "class":         "xdRichTextBox",
                "%(xd)sCtrlId":  "description",
                "%(xd)sxctname": "RichText",
                "%(xd)sbinding": "my:description",
                "contentEditable": "true",
            },"span"),
            "filedata": ({
                "class":           "xdFileAttachment",
                "%(xd)sCtrlId":    "filedata",
                "%(xd)sxctname":   "FileAttachment",
                "%(xd)sbinding":   "my:filedata",
            },"span"),
            "folder": ({
                "class":           "xdComboBox xdBehavior_Select",
                "%(xd)sCtrlId":    "folder",
                "%(xd)sxctname":   "dropdown",
                "%(xd)sbinding":   "my:folder",
            },"select"),
        }

        backend = self._get_backend(DocumentFakeBackend, subject="create_doc",
                                    body_map={}, model=Document
                                   )

        for field_name, attrs_nodetype in fields.iteritems():
            attrs, node_type = attrs_nodetype
            self._test_view_xsl_01(backend, field_name, attrs, node_type)

    def test_view_xsl05(self):#Deeper with m2m
        languages = Language.objects.all()
        self.populate('creme_core')
        self.assertTrue(languages)

        d_ns    = {'xsl': "{http://www.w3.org/1999/XSL/Transform}", 'xd': "{http://schemas.microsoft.com/office/infopath/2003}"}
        field_name = "language"
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map={field_name: ""}, model=Contact
                                   )
        xml     = self._get_view_xsl(backend, {field_name: ""})

        node_vb =  xml.find('%(xsl)stemplate/div/div/table/tbody/tr/td/div/font/strong' % d_ns)
        self.assertIsNotNone(node_vb)
        self.assertEqual(Contact._meta.get_field(field_name).verbose_name, node_vb.text)

        target_node =  xml.find('%(xsl)stemplate/div/div/table/tbody/tr/td/div/font/div' % d_ns)
        self.assertIsNotNone(target_node)

        input_nodes = target_node.findall('%(xsl)schoose/%(xsl)swhen/span/span/input' % d_ns)
        self.assertTrue(input_nodes)
        expected_titles = set(unicode(language) for language in languages)
        self.assertEqual(expected_titles, set(input_node.get('title') for input_node in input_nodes))

        expected_bindings = set('my:language/my:language_value[.="%s"][1]' % l.id for l in languages)
        self.assertEqual(expected_bindings, set(input_node.get('%(xd)sbinding' % d_ns) for input_node in input_nodes))

        self.assertEqual(set('my:language/my:language_value[.="%s"][1]' % language.id for language in languages),
                         set(input_node.get("select") for input_node in target_node.findall('%(xsl)schoose/%(xsl)swhen/span/span/input/%(xsl)sattribute/%(xsl)svalue-of' % d_ns))
                        )

        self.assertEqual(set('my:language/my:language_value="%s"' % language.id for language in languages),
                         set(input_node.get("test") for input_node in target_node.findall('%(xsl)schoose/%(xsl)swhen/span/span/input/%(xsl)sif' % d_ns))
                         )

        for_each_node = target_node.find('%(xsl)schoose/%(xsl)swhen/span/%(xsl)sfor-each' % d_ns)
        self.assertIsNotNone(for_each_node)
        self.assertEqual("my:language/my:language_value[%s]" % " and ".join(['.!="%s"' % l.id for l in languages]),
                         for_each_node.get('select')
                        )

    def test_render01(self):
        body_map = {'user_id': 1, 'is_actived': True, "first_name": "",
                    "last_name": "", "email": "none@none.com", "description": "",
                    "birthday": "", "created": "", 'url_site': ""
                   }
        backend = self._get_backend(ContactFakeBackend, subject="create_contact",
                                    body_map=body_map
                                   )
        builder = self._get_builder(backend)
        list(builder.render())#list is really not useful in reality, but as builder.render() create a generator it has to be parsed once

        backend_dir = builder._get_backend_dir()
        dir_exists = os.path.exists
        join = os.path.join

        self.assertTrue(dir_exists(backend_dir))
        self.assertTrue(dir_exists(join(backend_dir, 'creme.png')))
        self.assertTrue(dir_exists(join(backend_dir, 'manifest.xsf')))
        self.assertTrue(dir_exists(join(backend_dir, 'myschema.xsd')))
        self.assertTrue(dir_exists(join(backend_dir, 'template.xml')))
        self.assertTrue(dir_exists(join(backend_dir, 'upgrade.xsl')))
        self.assertTrue(dir_exists(join(backend_dir, 'view1.xsl')))

        self.assertTrue(dir_exists(join(backend_dir, '%s.xsn' % backend.subject)))

    def test_get_create_form_view01(self):
        """Backend not registered"""
        subject="create_contact"
        self._get_backend(ContactFakeBackend, subject=subject,
                          body_map={}, model=Contact
                         )

        response = self.client.get('/crudity/infopath/create_form/%s' % subject)
        self.assertEqual(404, response.status_code)

    def test_get_create_form_view02(self):
        subject="create_contact"
        backend = self._get_backend(ContactFakeBackend, subject=subject, body_map={})

        crudity_registry.register_fetchers("test", [FakeFetcher()])
        input = FakeInput()
        input.method = "create"
        input.name = "infopath"
        input.add_backend(backend)
        crudity_registry.register_inputs("test", [input])

        response = self.client.get('/crudity/infopath/create_form/%s' % subject)
        self.assertEqual(200, response.status_code)


class InfopathFormFieldTestCase(CrudityTestCase):
    def setUp(self):
        super(InfopathFormFieldTestCase, self).setUp()
        self.request = RequestFactory().get('/') #Url doesn't matter
        #self.request.LANGUAGE_CODE = '1033' #en

    def _get_backend(self, backend_klass, **backend_cfg):
        return backend_klass(config=backend_cfg)

    def test_uuid01(self):#uuid for a field has to be unique and the same BY FORM (so by backend)
        #request  = self.client.get('/').context['request']
        request  = self.request

        #Backend 1
        backend1 = self._get_backend(ContactFakeBackend, subject="create_ce")
        builder1 = InfopathFormBuilder(request=request, backend=backend1)
        uuid1 = InfopathFormField(builder1.urn, CremeEntity, 'user_id', request).uuid
        for i in xrange(10):
            self.assertEqual(uuid1, InfopathFormField(builder1.urn, CremeEntity, 'user_id', request).uuid)

        #Backend 2
        backend2 = self._get_backend(ContactFakeBackend, subject="create_ce2")
        builder2 = InfopathFormBuilder(request=request, backend=backend2)

        uuid2 = InfopathFormField(builder2.urn, CremeEntity, 'user_id', request).uuid
        for i in xrange(10):
            self.assertEqual(uuid2, InfopathFormField(builder2.urn, CremeEntity, 'user_id', request).uuid)

        self.assertNotEqual(uuid2, uuid1)

        #Backend 3
        backend3 = self._get_backend(ContactFakeBackend, subject="create_contact", model=Contact)
        builder3 = InfopathFormBuilder(request=request, backend=backend3)

        uuid3 = InfopathFormField(builder3.urn, Contact, 'user_id', request).uuid
        for i in xrange(10):
            self.assertEqual(uuid3, InfopathFormField(builder3.urn, Contact, 'user_id', request).uuid)

        self.assertNotEqual(uuid1, uuid3)
        self.assertNotEqual(uuid2, uuid3)

        uuid4 = InfopathFormField(builder1.urn, CremeEntity, 'user_id', request).uuid
        self.assertEqual(uuid1, uuid4)

    def test_get_field01(self):
        #request  = self.client.get('/').context['request']
        request  = self.request
        body_map = {'user_id': 1, 'is_actived': True, "first_name": "", "last_name": "",
                    "email": "none@none.com", "description": "", "birthday": ""
                   }

        backend = self._get_backend(ContactFakeBackend, subject="create_contact", body_map=body_map)
        builder = InfopathFormBuilder(request=request, backend=backend)

        model_get_field = Contact._meta.get_field
        self.assertEqual(model_get_field('user'),        InfopathFormField(builder.urn, Contact, 'user_id', request)._get_model_field())
        self.assertEqual(model_get_field('first_name'),  InfopathFormField(builder.urn, Contact, 'first_name', request)._get_model_field())
        self.assertEqual(model_get_field('last_name'),   InfopathFormField(builder.urn, Contact, 'last_name', request)._get_model_field())
        self.assertEqual(model_get_field('email'),       InfopathFormField(builder.urn, Contact, 'email', request)._get_model_field())
        self.assertEqual(model_get_field('description'), InfopathFormField(builder.urn, Contact, 'description', request)._get_model_field())
        self.assertEqual(model_get_field('birthday'),    InfopathFormField(builder.urn, Contact, 'birthday', request)._get_model_field())

        self.assertRaises(FieldDoesNotExist, InfopathFormField, builder.urn, Contact, 'email_id', request)

    def test_get_choices01(self):
        #request  = self.client.get('/').context['request']
        request  = self.request
        body_map = {'user_id': 1,}
        backend = self._get_backend(ContactFakeBackend, subject="create_contact", body_map=body_map)
        builder = InfopathFormBuilder(request=request, backend=backend)

        self.assertEqual(set((user.pk, unicode(user)) for user in User.objects.all()),
                         set(InfopathFormField(builder.urn, Contact, 'user_id', request)._get_choices())
                        )
