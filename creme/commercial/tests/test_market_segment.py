# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import RelationType, CremePropertyType, CremeProperty

    from creme.persons.tests.base import skipIfCustomOrganisation

    from ..models import MarketSegment
    from .base import CommercialBaseTestCase, Organisation, Strategy
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class MarketSegmentTestCase(CommercialBaseTestCase):
    def _build_delete_url(self, segment):
        return reverse('commercial__delete_segment', args=(segment.id,))

    def test_unique_segment_with_ptype(self):
        self.get_object_or_fail(MarketSegment, property_type=None)

        with self.assertRaises(ValueError):
            MarketSegment.objects.create(name='Foobar', property_type=None)

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
        response = self.assertGET200(reverse('commercial__list_segments'))
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

    def test_edit05(self):
        "Edit the segment with property_type=NULL"
        segment = self.get_object_or_fail(MarketSegment, property_type=None)
        ptype_count = CremePropertyType.objects.count()

        name = 'All the corporations'
        self.assertNoFormError(self.client.post(segment.get_edit_absolute_url(),
                                                data={'name': name},
                                               )
                              )

        segment = self.refresh(segment)
        self.assertEqual(name, segment.name)
        self.assertEqual(ptype_count, CremePropertyType.objects.count())

    @skipIfCustomOrganisation
    def test_segment_delete01(self):
        strategy = Strategy.objects.create(user=self.user, name='Producers')
        desc = self._create_segment_desc(strategy, 'Producer')
        segment1 = desc.segment
        old_ptype = segment1.property_type

        orga = Organisation.objects.create(user=self.user, name='NHK')
        prop = CremeProperty.objects.create(creme_entity=orga, type=old_ptype)

        rtype = RelationType.create(('commercial-subject_test_segment_delete', 'has produced',         [Organisation], [old_ptype]),
                                    ('commercial-object_test_segment_delete',  'has been produced by', [Organisation]),
                                   )[0]

        segment2 = self._create_segment('Industry')

        url = self._build_delete_url(segment1)
        self.assertGET200(url)

        self.assertPOST200(url, data={'to_segment': segment2.id})
        self.assertDoesNotExist(segment1)
        self.assertDoesNotExist(old_ptype)

        desc = self.assertStillExists(desc)
        self.assertEqual(segment2, desc.segment)

        prop = self.assertStillExists(prop)
        self.assertEqual(prop.type, segment2.property_type)

        ptypes = rtype.subject_properties.all()
        self.assertIn(prop.type,    ptypes)
        self.assertNotIn(old_ptype, ptypes)

    def test_segment_delete02(self):
        "Cannot delete if there is only one segment"
        segment = self.get_object_or_fail(MarketSegment, property_type=None)

        self.assertGET409(self._build_delete_url(segment))

    def test_segment_delete03(self):
        "Cannot replace a segment by itself"
        segment = self._create_segment('Noobs')
        self._create_segment('Nerds')

        response = self.assertPOST200(self._build_delete_url(segment),
                                      data={'to_segment': segment.id},
                                     )
        self.assertFormError(response, 'form', 'to_segment',
                             _('Select a valid choice. That choice is not one of the available choices.')
                            )

    @skipIfCustomOrganisation
    def test_segment_delete05(self):
        "Avoid CremeProperty duplicates"
        Strategy.objects.create(user=self.user, name='Producers')

        segment1 = self._create_segment('Robots')
        segment2 = self._create_segment('Mechas')
        ptype1 = segment1.property_type
        ptype2 = segment2.property_type

        create_orga = partial(Organisation.objects.create, user=self.user)
        orga1 = create_orga(name='Kunato Industries R&D#1')
        orga2 = create_orga(name='Kunato Industries R&D#2')
        orga3 = create_orga(name='Kunato Industries R&D#3')

        create_prop = CremeProperty.objects.create
        create_prop(type=ptype1, creme_entity=orga1)
        create_prop(type=ptype1, creme_entity=orga2)
        create_prop(type=ptype2, creme_entity=orga1)
        create_prop(type=ptype2, creme_entity=orga3)

        self.assertPOST200(self._build_delete_url(segment1), data={'to_segment': segment2.id})
        self.assertDoesNotExist(segment1)
        self.assertDoesNotExist(ptype1)

        expected = [ptype2]

        ptypes = lambda orga: [p.type for p in orga.properties.all()]

        self.assertEqual(expected, ptypes(orga1))  # Only one property, not 2 (with the same type)
        self.assertEqual(expected, ptypes(orga2))
        self.assertEqual(expected, ptypes(orga3))

    def test_segment_delete06(self):
        "Cannot delete the segment with property_type=NULL"
        segment = self.get_object_or_fail(MarketSegment, property_type=None)
        self._create_segment('Industry')  # We add this segment to not try to delete the last one.

        self.assertGET409(self._build_delete_url(segment))

    @skipIfCustomOrganisation
    def test_segment_delete07(self):
        "We replace with the segment with property_type=NULL"
        strategy = Strategy.objects.create(user=self.user, name='Producers')
        desc = self._create_segment_desc(strategy, 'Producer')
        segment1 = desc.segment
        old_ptype = segment1.property_type

        orga = Organisation.objects.create(user=self.user, name='NHK')
        prop = CremeProperty.objects.create(creme_entity=orga, type=old_ptype)

        rtype = RelationType.create(
                    ('commercial-subject_test_segment_delete7', 'has produced',         [Organisation], [old_ptype]),
                    ('commercial-object_test_segment_delete7',  'has been produced by', [Organisation]),
                   )[0]

        segment2 = self.get_object_or_fail(MarketSegment, property_type=None)
        self.assertPOST200(self._build_delete_url(segment1), data={'to_segment': segment2.id})
        self.assertDoesNotExist(segment1)
        self.assertDoesNotExist(old_ptype)

        desc = self.assertStillExists(desc)
        self.assertEqual(segment2, desc.segment)

        self.assertDoesNotExist(prop)
        self.assertFalse(rtype.subject_properties.all())
