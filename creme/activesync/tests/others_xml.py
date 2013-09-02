# -*- coding: utf-8 -*-

from xml.etree.ElementTree import fromstring

from django.contrib.auth.models import User

from creme.creme_core.tests.base import CremeTestCase
from creme.persons.models import Contact

from ..mappings import CREME_AS_MAPPING
from ..commands.airsync import AirSync


class XMLTestCase(CremeTestCase):

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'persons')
        cls.autodiscover()

    def test_contact_xmldecode(self):
        string_xml="""<ns0:Sync xmlns:ns0="AirSync:" xmlns:ns1="Contacts:"><ns0:Collections><ns0:Collection><ns0:Class>Contacts</ns0:Class><ns0:SyncKey>0000000001993B6875ABFA7B8CA20C130827T121925.610130827T121925.603</ns0:SyncKey><ns0:CollectionId>2:0</ns0:CollectionId><ns0:Status>1</ns0:Status><ns0:Commands><ns0:Add><ns0:ServerId>2:b0eed97c-0000-0000-0000-000000000000</ns0:ServerId><ns0:ApplicationData><ns1:LastName>NomSyncTest</ns1:LastName><ns1:FirstName>PrenomSyncTest</ns1:FirstName><ns1:FileAs>NomSyncTest, PrenomSyncTest</ns1:FileAs></ns0:ApplicationData></ns0:Add></ns0:Commands></ns0:Collection></ns0:Collections></ns0:Sync>"""
        xml = fromstring(string_xml)

        ns0 = "{AirSync:}"
        d_ns = {'ns0': ns0}
        user = User.objects.get(pk=1)
        creme_model_AS_values = CREME_AS_MAPPING.get(Contact)
        mapping = creme_model_AS_values['mapping']

        xml_collection = xml.find('%(ns0)sCollections/%(ns0)sCollection' % d_ns)
        commands_node = xml_collection.find('%(ns0)sCommands' % d_ns)
        add_nodes = commands_node.findall('%(ns0)sAdd' % d_ns)
        app_data = add_nodes[0].find('%(ns0)sApplicationData' % d_ns)

        airsync = AirSync("url", "login", "pwd", "device_id", user)
        data = airsync._parse_xml_for_create(user, app_data, mapping)
        self.assertNoException(data.get('UID', None))
