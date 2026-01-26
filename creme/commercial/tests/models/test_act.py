from datetime import date
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.activities.constants import (
    REL_SUB_ACTIVITY_SUBJECT,
    UUID_SUBTYPE_MEETING_OTHER,
)
from creme.activities.models import ActivitySubType
from creme.activities.tests.base import skipIfCustomActivity
from creme.commercial.constants import REL_SUB_COMPLETE_GOAL
from creme.commercial.models import ActObjective
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models import EntityFilter, Relation, RelationType
from creme.opportunities.models import SalesPhase
from creme.opportunities.tests.base import skipIfCustomOpportunity
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..base import (
    Activity,
    CommercialBaseTestCase,
    Contact,
    Opportunity,
    Organisation,
    skipIfCustomAct,
)


@skipIfCustomAct
class ActTestCase(CommercialBaseTestCase):
    def assertObjectivesEqual(self, obj_a, obj_b):
        self.assertEqual(obj_a.name,         obj_b.name)
        self.assertEqual(obj_a.counter,      obj_b.counter)
        self.assertEqual(obj_a.counter_goal, obj_b.counter_goal)
        self.assertEqual(obj_a.ctype,        obj_b.ctype)

    def test_clone(self):
        user = self.login_as_root_and_get()
        act = self._create_act(user=user)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Acme', Organisation, is_custom=True,
        )

        create_obj = partial(ActObjective.objects.create, act=act)
        obj1 = create_obj(name='Hello counter')
        obj2 = create_obj(
            name='Organisation counter', counter_goal=2, filter=efilter, ctype=Organisation,
        )

        cloned = self.clone(act)

        self.assertEqual(act.name,     cloned.name)
        self.assertEqual(act.due_date, cloned.due_date)
        self.assertEqual(act.segment,  cloned.segment)

        cloned_objs = ActObjective.objects.filter(act=cloned).order_by('name')
        self.assertEqual(2, len(cloned_objs))

        self.assertObjectivesEqual(obj1, cloned_objs[0])
        self.assertObjectivesEqual(obj2, cloned_objs[1])

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #     act = self.create_act(user=user)
    #
    #     efilter = EntityFilter.objects.smart_update_or_create(
    #         'test-filter01', 'Acme', Organisation, is_custom=True,
    #     )
    #
    #     create_obj = partial(ActObjective.objects.create, act=act)
    #     obj1 = create_obj(name='Hello counter')
    #     obj2 = create_obj(
    #         name='Organisation counter', counter_goal=2, filter=efilter, ctype=Organisation,
    #     )
    #
    #     cloned = act.clone()
    #     self.assertEqual(act.name,     cloned.name)
    #     self.assertEqual(act.due_date, cloned.due_date)
    #     self.assertEqual(act.segment,  cloned.segment)
    #
    #     cloned_objs = ActObjective.objects.filter(act=cloned).order_by('name')
    #     self.assertEqual(2, len(cloned_objs))
    #
    #     self.assertObjectivesEqual(obj1, cloned_objs[0])
    #     self.assertObjectivesEqual(obj2, cloned_objs[1])

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_count_relations(self):
        user = self.login_as_root_and_get()
        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_COMPLETE_GOAL)

        act = self._create_act(user=user)
        objective = ActObjective.objects.create(
            act=act, name='Orga counter', counter_goal=2, ctype=Organisation,
        )
        self.assertEqual(0, objective.get_count())
        self.assertFalse(objective.reached)

        completes_goal = partial(
            Relation.objects.create, type=rtype, object_entity=act, user=user,
        )
        create_orga = partial(Organisation.objects.create, user=user)

        completes_goal(subject_entity=create_orga(name='Ferraille corp'))
        objective = self.refresh(objective)  # Refresh cache
        self.assertEqual(1, objective.get_count())
        self.assertFalse(objective.reached)

        orga02 = create_orga(name='World company')
        completes_goal(subject_entity=orga02)
        objective = self.refresh(objective)  # Refresh cache
        self.assertEqual(2, objective.get_count())
        self.assertTrue(objective.reached)

        contact = Contact.objects.create(user=user, first_name='Monsieur', last_name='Ferraille')
        completes_goal(subject_entity=contact)
        objective = self.refresh(objective)  # Refresh cache
        self.assertEqual(2, objective.get_count())
        self.assertTrue(objective.reached)

        orga02.trash()
        self.assertEqual(1, self.refresh(objective).get_count())

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_count_relations__filter(self):
        "With filter."
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Acme', Organisation, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Organisation,
                    operator=operators.ICONTAINS,
                    field_name='name', values=['Ferraille'],
                ),
            ],
        )

        act = self._create_act(user=user)
        objective = ActObjective.objects.create(
            act=act, name='Orga counter', counter_goal=2,
            ctype=Organisation, filter=efilter,
        )
        self.assertEqual(0, objective.get_count())

        create_orga  = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='Ferraille corp')
        orga02 = create_orga(name='World company')
        orga03 = create_orga(name='Ferraille inc')

        all_orgas = {*efilter.filter(Organisation.objects.all())}
        self.assertIn(orga01, all_orgas)
        self.assertNotIn(orga02, all_orgas)

        completes_goal = partial(
            Relation.objects.create,
            type_id=REL_SUB_COMPLETE_GOAL, object_entity=act, user=user,
        )
        completes_goal(subject_entity=orga01)
        self.assertEqual(1, self.refresh(objective).get_count())

        completes_goal(subject_entity=orga02)
        self.assertEqual(1, self.refresh(objective).get_count())

        completes_goal(subject_entity=orga03)
        self.assertEqual(2, self.refresh(objective).get_count())

        contact = Contact.objects.create(user=user, first_name='Monsieur', last_name='Ferraille')
        completes_goal(subject_entity=contact)
        self.assertEqual(2, self.refresh(objective).get_count())

    def test_delete_type(self):
        user = self.login_as_root_and_get()
        act = self._create_act(user=user)
        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('commercial', 'act_type', act.act_type_id),
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_commercial__act_act_type',
            errors=_('Deletion is not possible.'),
        )

    def test_delete_objective(self):
        user = self.login_as_root_and_get()

        act = self._create_act(user=user)
        objective = ActObjective.objects.create(act=act, name='OBJ#1')
        ct = ContentType.objects.get_for_model(ActObjective)

        response = self.client.post(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': objective.id}
        )
        self.assertRedirects(response, act.get_absolute_url())
        self.assertDoesNotExist(objective)

    @skipIfCustomOrganisation
    @skipIfCustomActivity
    @skipIfCustomOpportunity
    def test_link_to_activity(self):
        user = self.login_as_root_and_get()
        act1 = self._create_act(user=user, name='Act#1')
        act2 = self._create_act(user=user, name='Act#2')

        create_orga = partial(Organisation.objects.create, user=user)
        opp = Opportunity.objects.create(
            user=user, name='Opp01',
            sales_phase=SalesPhase.objects.create(name='Foresale'),
            closing_date=date.today(),
            emitter=create_orga(name='Ferraille corp'),
            target=create_orga(name='World company'),
        )

        create_rel = partial(Relation.objects.create, subject_entity=opp, user=user)
        create_rel(type_id=REL_SUB_COMPLETE_GOAL, object_entity=act1)
        create_rel(type_id=REL_SUB_COMPLETE_GOAL, object_entity=act2)

        create_dt = self.create_datetime
        sub_type = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_MEETING_OTHER)
        meeting = Activity.objects.create(
            user=user, title='Meeting #01',
            type_id=sub_type.type_id,
            sub_type=sub_type,
            start=create_dt(year=2011, month=5, day=20, hour=14, minute=0),
            end=create_dt(year=2011,   month=6, day=1,  hour=15, minute=0),
        )

        create_rel(type_id=REL_SUB_ACTIVITY_SUBJECT, object_entity=meeting)
        self.assertHaveRelation(subject=meeting, type=REL_SUB_COMPLETE_GOAL, object=act1)
        self.assertHaveRelation(subject=meeting, type=REL_SUB_COMPLETE_GOAL, object=act2)
