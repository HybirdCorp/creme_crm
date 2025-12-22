from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_filter import EF_CREDENTIALS
from creme.creme_core.models import (
    EntityFilter,
    FakeContact,
    FakeOrganisation,
    RelationType,
)
from creme.reports.constants import EF_REPORTS
from creme.reports.core.entity_filter import (
    ReportRelationSubFilterConditionHandler,
    ReportRelationSubfiltersConditionsField,
)
from creme.reports.tests.base import BaseReportsTestCase


class ReportRelationSubfiltersConditionsFieldTestCase(BaseReportsTestCase):
    def _create_rtype(self):
        return RelationType.objects.builder(
            id='test-subject_freelance', predicate='Is a freelance for',
            models=[FakeContact],
        ).symmetric(
            id='test-object_freelance', predicate='Works with the freelance',
        ).get_or_create()[0]

    def test_clean__empty__required(self):
        field = ReportRelationSubfiltersConditionsField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='[]')

    def test_clean__incomplete_data__required(self):
        rtype = self._create_rtype()
        field = ReportRelationSubfiltersConditionsField(model=FakeContact)
        msg = _('This field is required.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=json_dump([{'rtype': rtype.id}]),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=json_dump([{'has': True}]),
        )

    def test_unknown_filter(self):
        rtype = self._create_rtype()
        field = ReportRelationSubfiltersConditionsField(model=FakeContact)
        field.user = self.get_root_user()
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'rtype': rtype.id, 'has': False,
                'ctype': ContentType.objects.get_for_model(FakeContact).id,
                'filter': '3213213543',  # <==
            }]),
            messages=_('This filter is invalid.'),
            codes='invalidfilter',
        )

    def test_ok(self):
        user = self.get_root_user()
        team = self.create_team('My team', user)

        rtype1 = self._create_rtype()
        rtype2 = rtype1.symmetric_type

        efilter1 = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
        )
        efilter2 = EntityFilter.objects.create(
            id='reports-organisation_filter1',
            name='Organisation filter (only reports)',
            entity_type=FakeOrganisation,
            filter_type=EF_REPORTS,
            is_private=True,
            user=user,
        )
        efilter3 = EntityFilter.objects.create(
            id='reports-organisation_filter2',
            name='Team filter (only reports)',
            entity_type=FakeOrganisation,
            filter_type=EF_REPORTS,
            is_private=True,
            user=team,
        )

        with self.assertNumQueries(0):
            field = ReportRelationSubfiltersConditionsField(model=FakeContact)
            field.user = user

        field.efilter_type = EF_REPORTS

        conditions = field.clean(json_dump([
            {
                'rtype': rtype1.id,
                'has': True,
                'ctype': efilter1.entity_type_id,
                'filter': efilter1.id,
            }, {
                'rtype': rtype2.id,
                'has': False,
                'ctype': efilter2.entity_type_id,
                'filter': efilter2.id,
            }, {
                'rtype': rtype2.id,
                'has': False,
                'ctype': efilter3.entity_type_id,
                'filter': efilter3.id,
            },
        ]))
        self.assertEqual(3, len(conditions))

        type_id = ReportRelationSubFilterConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id,    condition1.type)
        self.assertEqual(rtype1.id,  condition1.name)
        self.assertEqual(EF_REPORTS, condition1.filter_type)
        self.assertDictEqual(
            {'has': True, 'filter_id': efilter1.id},
            condition1.value,
        )

        condition2 = conditions[1]
        self.assertEqual(type_id,   condition2.type)
        self.assertEqual(rtype2.id, condition2.name)
        self.assertDictEqual(
            {'has': False, 'filter_id': efilter2.id},
            condition2.value,
        )

        self.assertDictEqual(
            {'has': False, 'filter_id': efilter3.id},
            conditions[2].value,
        )

    def test_forbidden_filter__private(self):
        user = self.get_root_user()
        other = self.create_user()

        rtype = self._create_rtype()
        efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
            is_private=True,
            user=other,
        )

        field = ReportRelationSubfiltersConditionsField(model=FakeContact, user=user)
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'rtype': rtype.id, 'has': False,
                'ctype': efilter.entity_type_id,
                'filter': efilter.id,
            }]),
            messages=_('This filter is invalid.'),
            codes='invalidfilter',
        )

    def test_forbidden_filter__bad_type(self):
        user = self.get_root_user()

        rtype = self._create_rtype()
        efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )

        field = ReportRelationSubfiltersConditionsField(model=FakeContact, user=user)
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'rtype': rtype.id, 'has': False,
                'ctype': efilter.entity_type_id,
                'filter': efilter.id,
            }]),
            messages=_('This filter is invalid.'),
            codes='invalidfilter',
        )

    def test_staff(self):
        user = self.login_as_super(is_staff=True)
        other_user = self.create_user(index=1)
        rtype = self._create_rtype()
        efilter = EntityFilter.objects.create(
            id='reports-organisation_filter',
            name='Organisation filter (only reports)',
            entity_type=FakeOrganisation,
            filter_type=EF_REPORTS,
            is_private=True,
            user=other_user,
        )
        field = ReportRelationSubfiltersConditionsField(
            model=FakeContact, user=user, efilter_type=EF_REPORTS,
        )

        condition = self.get_alone_element(field.clean(json_dump([{
            'rtype': rtype.id,
            'has': True,
            'ctype': efilter.entity_type_id,
            'filter': efilter.id,
        }])))
        self.assertDictEqual(
            {'has': True, 'filter_id': efilter.id}, condition.value,
        )

    def test_disabled_rtype__not_used(self):
        efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )

        rtype = self._create_rtype()
        rtype.enabled = False
        rtype.save()

        self.assertFormfieldError(
            field=ReportRelationSubfiltersConditionsField(
                model=FakeContact, user=self.get_root_user(),
            ),
            value=json_dump([{
                'rtype': rtype.id, 'has': True,
                'ctype': efilter.entity_type_id,
                'filter': efilter.id,
            }]),
            messages=_('This type of relationship type is invalid with this model.'),
            codes='invalidrtype',
        )

    def test_disabled_rtype__used(self):
        "Disabled RelationType is already used => still proposed."
        efilter = EntityFilter.objects.create(
            id='creme_core-contacts_filter',
            name='Contact filter',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )

        rtype = self._create_rtype()
        rtype.enabled = False
        rtype.save()

        field = ReportRelationSubfiltersConditionsField(
            model=FakeContact, user=self.get_root_user(), efilter_type=EF_REPORTS,
        )

        ct = ContentType.objects.get_for_model(FakeContact)
        field.initialize(
            ctype=ct,
            conditions=[
                ReportRelationSubFilterConditionHandler.build_condition(
                    model=FakeContact, rtype=rtype, subfilter=efilter,
                ),
            ],
        )
        efilter_id = efilter.id
        condition = self.get_alone_element(field.clean(json_dump([{
            'rtype': rtype.id, 'has': True, 'ctype': ct.id, 'filter': efilter_id,
        }])))
        self.assertEqual(ReportRelationSubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(rtype.id, condition.name)
        self.assertDictEqual(
            {'has': True, 'filter_id': efilter_id}, condition.value,
        )
