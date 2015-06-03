# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import CremePropertyType

    from .base import CommercialBaseTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class MarketSegmentTestCase(CommercialBaseTestCase):
#    ADD_URL = '/commercial/market_segment/add'

    def test_create01(self):
        url = self.ADD_SEGMENT_URL
        self.assertGET200(url)

        name = 'Industry'
        segment = self._create_segment(name)

        self.assertEqual(_(u'is in the segment "%s"') % name,
                         segment.property_type.text
                        )

    def test_create02(self):
        "A segment with the same name already exists"
        name = 'Industry'
        url = self.ADD_SEGMENT_URL
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        response = self.assertPOST200(url, data={'name': name})
        self.assertFormError(response, 'form', 'name',
                             _(u'A segment with this name already exists')
                            )

    def test_create03(self):
        "A property with the same name already exists"
        name = 'Industry'
        pname = _(u'is in the segment "%s"') % name
        CremePropertyType.create('commercial-marketsegmenttestcase01', pname)

        response = self.assertPOST200(self.ADD_SEGMENT_URL, data={'name': name})
        self.assertFormError(response, 'form', 'name',
                             _(u'A property with the name «%(name)s» already exists') % {
                                    'name': pname,
                                 }
                            )

    def test_listview(self):
        response = self.assertGET200('/commercial/market_segments')
        self.assertTemplateUsed(response, 'commercial/list_segments.html')

    def test_edit01(self):
        name = 'industry'
        segment = self._create_segment(name)
        ptype_count = CremePropertyType.objects.count()
        url = segment.get_edit_absolute_url()
        self.assertGET200(url)

        name = name.title()
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        segment = self.refresh(segment)
        self.assertEqual(name, segment.name)
        self.assertEqual(ptype_count, CremePropertyType.objects.count())

        self.assertEqual(_(u'is in the segment "%s"') % name,
                         segment.property_type.text
                        )

    def test_edit02(self):
        "A segment with the same name already exists"
        name = 'Industry'
        self._create_segment(name)

        segment = self._create_segment('in-dus-try')
        response = self.assertPOST200(segment.get_edit_absolute_url(), data={'name': name})
        self.assertFormError(response, 'form', 'name',
                             _(u'A segment with this name already exists')
                            )

    def test_edit03(self):
        "A property with the same name already exists"
        segment = self._create_segment('in-dus-try')

        name = 'Industry'
        pname = _(u'is in the segment "%s"') % name
        CremePropertyType.create('commercial-marketsegmenttestcase01', pname)

        response = self.assertPOST200(segment.get_edit_absolute_url(), data={'name': name})
        self.assertFormError(response, 'form', 'name',
                             _(u'A property with the name «%(name)s» already exists') % {
                                 'name': pname,
                             }
                            )

    def test_edit04(self):
        "No name change => no collision"
        name = 'Industry'
        segment = self._create_segment(name)
        ptype_count = CremePropertyType.objects.count()

        self.assertNoFormError(self.client.post(segment.get_edit_absolute_url(),
                                                data={'name': name},
                                               )
                              )

        segment = self.refresh(segment)
        self.assertEqual(name, segment.name)
        self.assertEqual(ptype_count, CremePropertyType.objects.count())

        self.assertEqual(_(u'is in the segment "%s"') % name,
                         segment.property_type.text
                        )
