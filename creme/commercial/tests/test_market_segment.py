# -*- coding: utf-8 -*-

from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    RelationType,
)
from creme.persons.tests.base import skipIfCustomOrganisation

from ..models import MarketSegment
from .base import CommercialBaseTestCase, Organisation, Strategy


class MarketSegmentTestCase(CommercialBaseTestCase):
    @staticmethod
    def _build_delete_url(segment):
        return reverse('commercial__delete_segment', args=(segment.id,))

    def test_unique_segment_with_ptype(self):
        self.get_object_or_fail(MarketSegment, property_type=None)

        with self.assertRaises(ValueError):
            MarketSegment.objects.create(name='Foobar', property_type=None)

    def test_create01(self):
        self.login()
        url = self.ADD_SEGMENT_URL

        context = self.assertGET200(url).context
        self.assertEqual(_('Create a market segment'), context.get('title'))
        self.assertEqual(_('Save the market segment'), context.get('submit_label'))

        name = 'Industry'
        segment = self._create_segment(name)

        self.assertEqual(
            _('is in the segment «{}»').format(name),
            segment.property_type.text,
        )

    def test_create02(self):
        "A segment with the same name already exists."
        self.login(is_superuser=False, allowed_apps=['commercial'])

        name = 'Industry'
        url = self.ADD_SEGMENT_URL
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        response = self.assertPOST200(url, data={'name': name})
        self.assertFormError(
            response, 'form', 'name',
            _('A segment with this name already exists'),
        )

    def test_create03(self):
        "A property with the same name already exists."
        self.login()

        name = 'Industry'
        pname = _('is in the segment «{}»').format(name)
        CremePropertyType.objects.smart_update_or_create(
            str_pk='commercial-marketsegmenttestcase01', text=pname,
        )

        response = self.assertPOST200(self.ADD_SEGMENT_URL, data={'name': name})
        self.assertFormError(
            response, 'form', 'name',
            _('A property with the name «%(name)s» already exists') % {'name': pname},
        )

    def test_create04(self):
        "Not allowed"
        self.login(is_superuser=False)
        self.assertGET403(self.ADD_SEGMENT_URL)

    def test_listview01(self):
        self.login(is_superuser=False, allowed_apps=['commercial'])

        response = self.assertGET200(reverse('commercial__list_segments'))
        self.assertTemplateUsed(response, 'commercial/list_segments.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

    def test_listview02(self):
        "App permission needed."
        self.login(is_superuser=False, allowed_apps=['persons'])

        self.assertGET403(reverse('commercial__list_segments'))

    def test_edit01(self):
        self.login()

        name = 'industry'
        segment = self._create_segment(name)
        ptype_count = CremePropertyType.objects.count()
        url = segment.get_edit_absolute_url()

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        get_ctxt = response.context.get
        self.assertEqual(_('Edit «{object}»').format(object=segment), get_ctxt('title'))
        self.assertEqual(_('Save the modifications'),                 get_ctxt('submit_label'))

        # ---
        name = name.title()
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        segment = self.refresh(segment)
        self.assertEqual(name, segment.name)
        self.assertEqual(ptype_count, CremePropertyType.objects.count())

        self.assertEqual(
            _('is in the segment «{}»').format(name),
            segment.property_type.text,
        )

    def test_edit02(self):
        "A segment with the same name already exists."
        self.login()

        name = 'Industry'
        self._create_segment(name)

        segment = self._create_segment('in-dus-try')
        response = self.assertPOST200(
            segment.get_edit_absolute_url(), data={'name': name},
        )
        self.assertFormError(
            response, 'form', 'name',
            _('A segment with this name already exists'),
        )

    def test_edit03(self):
        "A property with the same name already exists."
        self.login()

        segment = self._create_segment('in-dus-try')

        name = 'Industry'
        pname = _('is in the segment «{}»').format(name)
        CremePropertyType.objects.smart_update_or_create(
            str_pk='commercial-marketsegmenttestcase01', text=pname,
        )

        response = self.assertPOST200(
            segment.get_edit_absolute_url(), data={'name': name},
        )
        self.assertFormError(
            response, 'form', 'name',
            _('A property with the name «%(name)s» already exists') % {'name': pname},
        )

    def test_edit04(self):
        "No name change => no collision"
        self.login()

        name = 'Industry'
        segment = self._create_segment(name)
        ptype_count = CremePropertyType.objects.count()

        self.assertNoFormError(self.client.post(
            segment.get_edit_absolute_url(), data={'name': name},
        ))

        segment = self.refresh(segment)
        self.assertEqual(name, segment.name)
        self.assertEqual(ptype_count, CremePropertyType.objects.count())

        self.assertEqual(
            _('is in the segment «{}»').format(name),
            segment.property_type.text,
        )

    def test_edit05(self):
        "Edit the segment with property_type=NULL."
        self.login()

        segment = self.get_object_or_fail(MarketSegment, property_type=None)
        ptype_count = CremePropertyType.objects.count()

        name = 'All the corporations'
        self.assertNoFormError(self.client.post(
            segment.get_edit_absolute_url(), data={'name': name},
        ))

        segment = self.refresh(segment)
        self.assertEqual(name, segment.name)
        self.assertEqual(ptype_count, CremePropertyType.objects.count())

    def test_edit06(self):
        "Not super-user."
        self.login(is_superuser=False, allowed_apps=['commercial'])

        segment = self._create_segment('Industry')
        self.assertGET200(segment.get_edit_absolute_url())

    def test_edit07(self):
        "No app permission."
        self.login(is_superuser=False)  # allowed_apps=['commercial']

        ptype = CremePropertyType.objects.create(
            pk='commercial-test_market_segment_test_edit_07',
            text='Is an otaku',
        )
        segment = MarketSegment.objects.create(name='Otakus', property_type=ptype)
        self.assertGET403(segment.get_edit_absolute_url())

    @skipIfCustomOrganisation
    def test_delete01(self):
        user = self.login()

        strategy = Strategy.objects.create(user=user, name='Producers')
        desc = self._create_segment_desc(strategy, 'Producer')
        segment1 = desc.segment
        old_ptype = segment1.property_type

        orga = Organisation.objects.create(user=user, name='NHK')
        prop = CremeProperty.objects.create(creme_entity=orga, type=old_ptype)

        rtype = RelationType.objects.smart_update_or_create(
            (
                'commercial-subject_test_segment_delete',
                'has produced',
                [Organisation],
                [old_ptype],
            ),
            (
                'commercial-object_test_segment_delete',
                'has been produced by',
                [Organisation],
            ),
        )[0]

        segment2 = self._create_segment('Industry')

        url = self._build_delete_url(segment1)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/delete-popup.html')

        get_ctxt = response.context.get
        self.assertEqual(
            _('Delete and replace «{object}»').format(object=segment1),
            get_ctxt('title'),
        )
        self.assertEqual(_('Replace'), get_ctxt('submit_label'))

        # ---
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

    def test_delete02(self):
        "Cannot delete if there is only one segment."
        self.login()

        segment = self.get_object_or_fail(MarketSegment, property_type=None)
        self.assertGET409(self._build_delete_url(segment))

    def test_delete03(self):
        "Cannot replace a segment by itself."
        self.login()

        segment = self._create_segment('Noobs')
        self._create_segment('Nerds')

        response = self.assertPOST200(
            self._build_delete_url(segment), data={'to_segment': segment.id},
        )
        self.assertFormError(
            response, 'form', 'to_segment',
            _('Select a valid choice. That choice is not one of the available choices.')
        )

    @skipIfCustomOrganisation
    def test_delete05(self):
        "Avoid CremeProperty duplicates."
        user = self.login()

        Strategy.objects.create(user=user, name='Producers')

        segment1 = self._create_segment('Robots')
        segment2 = self._create_segment('Mechas')
        ptype1 = segment1.property_type
        ptype2 = segment2.property_type

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Kunato Industries R&D#1')
        orga2 = create_orga(name='Kunato Industries R&D#2')
        orga3 = create_orga(name='Kunato Industries R&D#3')

        create_prop = CremeProperty.objects.create
        create_prop(type=ptype1, creme_entity=orga1)
        create_prop(type=ptype1, creme_entity=orga2)
        create_prop(type=ptype2, creme_entity=orga1)
        create_prop(type=ptype2, creme_entity=orga3)

        self.assertPOST200(
            self._build_delete_url(segment1), data={'to_segment': segment2.id},
        )
        self.assertDoesNotExist(segment1)
        self.assertDoesNotExist(ptype1)

        expected = [ptype2]

        def ptypes(orga):
            return [p.type for p in orga.properties.all()]

        # Only one property, not 2 (with the same type)
        self.assertListEqual(expected, ptypes(orga1))

        self.assertListEqual(expected, ptypes(orga2))
        self.assertListEqual(expected, ptypes(orga3))

    def test_delete06(self):
        "Cannot delete the segment with property_type=NULL."
        self.login()

        segment = self.get_object_or_fail(MarketSegment, property_type=None)
        # We add this segment to not try to delete the last one.
        self._create_segment('Industry')

        self.assertGET404(self._build_delete_url(segment))

    @skipIfCustomOrganisation
    def test_delete07(self):
        "We replace with the segment with property_type=NULL."
        user = self.login()

        strategy = Strategy.objects.create(user=user, name='Producers')
        desc = self._create_segment_desc(strategy, 'Producer')
        segment1 = desc.segment
        old_ptype = segment1.property_type

        orga = Organisation.objects.create(user=user, name='NHK')
        prop = CremeProperty.objects.create(creme_entity=orga, type=old_ptype)

        rtype = RelationType.objects.smart_update_or_create(
            (
                'commercial-subject_test_segment_delete7',
                'has produced',
                [Organisation],
                [old_ptype],
            ),
            (
                'commercial-object_test_segment_delete7',
                'has been produced by',
                [Organisation],
            ),
        )[0]

        segment2 = self.get_object_or_fail(MarketSegment, property_type=None)
        self.assertPOST200(
            self._build_delete_url(segment1), data={'to_segment': segment2.id},
        )
        self.assertDoesNotExist(segment1)
        self.assertDoesNotExist(old_ptype)

        desc = self.assertStillExists(desc)
        self.assertEqual(segment2, desc.segment)

        self.assertDoesNotExist(prop)
        self.assertFalse(rtype.subject_properties.all())
