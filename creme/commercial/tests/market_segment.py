# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme_core.models import CremePropertyType

    from commercial.models import MarketSegment
    from commercial.tests.base import CommercialBaseTestCase
except Exception as e:
    print 'Error:', e


__all__ = ('MarketSegmentTestCase',)


class MarketSegmentTestCase(CommercialBaseTestCase):
    def test_create01(self):
        url = '/commercial/market_segment/add'
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Industry'
        response = self.client.post(url, data={'name': name})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        #try:
        with self.assertNoException():
            segment = MarketSegment.objects.get(name=name)
        #except Exception as e:
            #self.fail(str(e))

        self.assertEqual(_(u'is in the segment "%s"') % name,
                         segment.property_type.text
                        )

    def test_create02(self): #segment with same name already exists
        name = 'Industry'
        url = '/commercial/market_segment/add'
        response = self.client.post(url, data={'name': name})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url, data={'name': name})
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'name', [_(u'A segment with this name already exists')])

    def test_create03(self): #property with same name already exists
        name = 'Industry'
        pname = _(u'is in the segment "%s"') % name
        CremePropertyType.create('commercial-marketsegmenttestcase01', pname)

        response = self.client.post('/commercial/market_segment/add', data={'name': name})
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'name', [_(u'A property with the name <%s> already exists') % pname])

    def test_listview(self):
        response = self.client.get('/commercial/market_segments')
        self.assertEqual(200, response.status_code)

    #TODO: segment can be deleted ??
    #def test_segment_delete(self):
        #strategy = Strategy.objects.create(user=self.user, name='Strat#1')
        #segment = MarketSegment.objects.create(name='Industry', strategy=strategy)
        #self.assertEqual(1, len(strategy.segments.all()))

        #response = self.client.post('/commercial/segment/delete', data={'id': segment.id}, follow=True)
        #self.assertEqual(response.status_code, 200)
        #self.assertEqual(0, len(strategy.segments.all()))
