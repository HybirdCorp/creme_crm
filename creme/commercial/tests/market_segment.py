# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import CremePropertyType

    from ..models import MarketSegment
    from .base import CommercialBaseTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('MarketSegmentTestCase',)


class MarketSegmentTestCase(CommercialBaseTestCase):
    def test_create01(self):
        url = '/commercial/market_segment/add'
        self.assertGET200(url)

        name = 'Industry'
        response = self.client.post(url, data={'name': name})
        self.assertNoFormError(response)

        with self.assertNoException():
            segment = MarketSegment.objects.get(name=name)

        self.assertEqual(_(u'is in the segment "%s"') % name,
                         segment.property_type.text
                        )

    def test_create02(self):
        "A segment with same name already exists"
        name = 'Industry'
        url = '/commercial/market_segment/add'
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        response = self.assertPOST200(url, data={'name': name})
        self.assertFormError(response, 'form', 'name',
                             [_(u'A segment with this name already exists')]
                            )

    def test_create03(self):
        "A property with same name already exists"
        name = 'Industry'
        pname = _(u'is in the segment "%s"') % name
        CremePropertyType.create('commercial-marketsegmenttestcase01', pname)

        response = self.assertPOST200('/commercial/market_segment/add', data={'name': name})
        self.assertFormError(response, 'form', 'name',
                             [_(u'A property with the name <%s> already exists') % pname]
                            )

    def test_listview(self):
        self.assertGET200('/commercial/market_segments')

    #TODO: segment can be deleted ??
    #def test_segment_delete(self):
        #strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        #segment = MarketSegment.objects.create(name='Industry', strategy=strategy)
        #self.assertEqual(1, len(strategy.segments.all()))

        #response = self.client.post('/commercial/segment/delete', data={'id': segment.id}, follow=True)
        #self.assertEqual(response.status_code, 200)
        #self.assertEqual(0, len(strategy.segments.all()))
