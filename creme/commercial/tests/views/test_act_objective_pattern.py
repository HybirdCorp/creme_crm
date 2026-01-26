from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.commercial.bricks import PatternComponentsBrick
from creme.commercial.models import ActObjectivePatternComponent
from creme.creme_core.models import EntityFilter, FakeContact
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..base import (
    ActObjectivePattern,
    CommercialBaseTestCase,
    skipIfCustomPattern,
)


@skipIfCustomPattern
class ActObjectivePatternViewsTestCase(BrickTestCaseMixin, CommercialBaseTestCase):
    @staticmethod
    def _build_add_component_url(pattern):
        return reverse('commercial__create_component', args=(pattern.id,))

    @staticmethod
    def _build_parent_url(component):
        return reverse('commercial__create_parent_component', args=(component.id,))

    def test_creation(self):
        user = self.login_as_root_and_get()
        url = reverse('commercial__create_pattern')
        self.assertGET200(url)

        segment = self._create_segment()
        name = 'ObjPattern#1'
        average_sales = 5000
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':          user.pk,
                'name':          name,
                'average_sales': average_sales,
                'segment':       segment.id,
            },
        )
        self.assertNoFormError(response)

        pattern = self.get_alone_element(ActObjectivePattern.objects.all())
        self.assertEqual(name,          pattern.name)
        self.assertEqual(average_sales, pattern.average_sales)
        self.assertEqual(segment,       pattern.segment)

        self.assertRedirects(response, pattern.get_absolute_url())

    def test_edition(self):
        user = self.login_as_root_and_get()
        name = 'ObjPattern'
        average_sales = 1000
        pattern = self._create_pattern(user=user, name=name, average_sales=average_sales)

        url = pattern.get_edit_absolute_url()
        self.assertGET200(url)

        # ---
        name += '_edited'
        average_sales *= 2
        segment = self._create_segment('Segment#2')
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':          user.pk,
                'name':          name,
                'average_sales': average_sales,
                'segment':       segment.id,
            },
        ))

        pattern = self.refresh(pattern)
        self.assertEqual(name,          pattern.name)
        self.assertEqual(average_sales, pattern.average_sales)
        self.assertEqual(segment,       pattern.segment)

    def test_list_view(self):
        user = self.login_as_root_and_get()
        create_patterns = partial(ActObjectivePattern.objects.create, user=user)
        patterns = [
            create_patterns(
                name=f'ObjPattern#{i}',
                average_sales=1000 * i,
                segment=self._create_segment(f'Segment #{i}'),
            ) for i in range(1, 4)
        ]

        response = self.assertGET200(ActObjectivePattern.get_lv_absolute_url())

        with self.assertNoException():
            patterns_page = response.context['page_obj']

        self.assertEqual(1, patterns_page.number)
        self.assertEqual(3, patterns_page.paginator.count)
        self.assertCountEqual(patterns, patterns_page.object_list)

    def test_add_root_pattern_component(self):
        "No parent component, no counted relation."
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)

        url = self._build_add_component_url(pattern)
        get_ctxt = self.assertGET200(url).context.get
        self.assertEqual(
            _('New objective for «{entity}»').format(entity=pattern),
            get_ctxt('title'),
        )
        self.assertEqual(_('Save the objective'), get_ctxt('submit_label'))

        # ---
        name = 'Signed opportunities'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name':            name,
                'success_rate':    10,
                'entity_counting': self.formfield_value_filtered_entity_type(),
            },
        ))

        component = self.get_alone_element(pattern.components.all())
        self.assertEqual(name, component.name)
        self.assertIsNone(component.parent)
        self.assertIsNone(component.ctype)

        # ---
        detail_response = self.assertGET200(pattern.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(detail_response.content),
            brick=PatternComponentsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node, count=1, title='{count} Objective', plural_title='{count} Objectives',
        )

    def test_add_root_pattern_component__counted_relation(self):
        "Counted relation (no parent component)."
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)
        name = 'Called contacts'
        ct = ContentType.objects.get_for_model(FakeContact)
        response = self.client.post(
            self._build_add_component_url(pattern),
            data={
                'name':            name,
                'entity_counting': self.formfield_value_filtered_entity_type(ct),
                'success_rate':    15,
            },
        )
        self.assertNoFormError(response)

        component = self.get_alone_element(pattern.components.all())
        self.assertEqual(name, component.name)
        self.assertEqual(ct,   component.ctype)
        self.assertIsNone(component.filter)

    def test_add_root_pattern_component__counted_relation__filter(self):
        "Counted relation with filter (no parent component)."
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)
        name = 'Called contacts'
        ct = ContentType.objects.get_for_model(FakeContact)
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ninja', FakeContact, is_custom=True,
        )
        response = self.client.post(
            self._build_add_component_url(pattern),
            data={
                'name':            name,
                'entity_counting': self.formfield_value_filtered_entity_type(ct, efilter),
                'success_rate':    15,
            },
        )
        self.assertNoFormError(response)

        with self.assertNoException():
            component = pattern.components.get(name=name)

        self.assertEqual(ct,      component.ctype)
        self.assertEqual(efilter, component.filter)

    def test_add_child_pattern_component(self):
        "Parent component."
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)
        comp01 = ActObjectivePatternComponent.objects.create(
            name='Signed opportunities',
            pattern=pattern,
            success_rate=50,
        )

        url = reverse('commercial__create_child_component', args=(comp01.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('New child objective for «{component}»').format(component=comp01),
            context.get('title')
        )
        self.assertEqual(_('Save the objective'), context.get('submit_label'))

        # ---
        name = 'Spread Vcards'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name':            name,
                'success_rate':    20,
                'entity_counting': self.formfield_value_filtered_entity_type(),
            },
        ))

        comp02 = self.get_alone_element(comp01.children.all())
        self.assertEqual(name,   comp02.name)
        self.assertEqual(comp01, comp02.parent)
        self.assertIsNone(comp02.ctype)

        name = 'Called contacts'
        ct = ContentType.objects.get_for_model(FakeContact)
        response = self.client.post(
            url,
            data={
                'name':            name,
                'entity_counting': self.formfield_value_filtered_entity_type(ct),
                'success_rate':    60,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, comp01.children.count())

        with self.assertNoException():
            comp03 = comp01.children.get(name=name)

        self.assertEqual(ct, comp03.ctype)

        # ---
        detail_response = self.assertGET200(pattern.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(detail_response.content), brick=PatternComponentsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node, count=3, title='{count} Objective', plural_title='{count} Objectives',
        )

    def test_add_parent_pattern_component(self):
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)
        comp01 = ActObjectivePatternComponent.objects.create(
            name='Sent mails', pattern=pattern, success_rate=5,
        )

        url = self._build_parent_url(comp01)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        get_ctxt = response.context.get
        self.assertEqual(
            _('New parent objective for «{component}»').format(component=comp01),
            get_ctxt('title'),
        )
        self.assertEqual(_('Save the objective'), get_ctxt('submit_label'))

        # ---
        name = 'Signed opportunities'
        success_rate = 50
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name':            name,
                'success_rate':    success_rate,
                'entity_counting': self.formfield_value_filtered_entity_type(),
            },
        ))

        pattern = self.refresh(pattern)
        components = pattern.components.order_by('id')
        self.assertEqual(2, len(components))

        child = components[0]
        self.assertEqual(comp01, child)

        parent = components[1]
        self.assertEqual(name,         parent.name)
        self.assertEqual(success_rate, parent.success_rate)
        self.assertIsNone(parent.parent)
        self.assertEqual(child.parent, parent)

    def test_add_parent_pattern_component__already_parented(self):
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)

        create_comp = partial(ActObjectivePatternComponent.objects.create, pattern=pattern)
        comp01 = create_comp(name='Signed opportunities', success_rate=50)
        comp02 = create_comp(name='Spread Vcards',        success_rate=1, parent=comp01)

        name = 'Called contacts'
        ct = ContentType.objects.get_for_model(FakeContact)
        response = self.client.post(
            self._build_parent_url(comp02),
            data={
                'name':            name,
                'entity_counting': self.formfield_value_filtered_entity_type(ct),
                'success_rate':    20,
            },
        )
        self.assertNoFormError(response)

        pattern = self.get_object_or_fail(ActObjectivePattern, pk=pattern.id)
        components = pattern.components.order_by('id')
        self.assertEqual(3, len(components))

        grandpa = components[0]
        self.assertEqual(comp01, grandpa)

        child = components[1]
        self.assertEqual(comp02, child)

        parent = components[2]
        self.assertEqual(name, parent.name)
        self.assertEqual(ct,   parent.ctype)

        self.assertEqual(child.parent,  parent)
        self.assertEqual(parent.parent, grandpa)

    def test_add_pattern_component_errors(self):
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)
        url = self._build_add_component_url(pattern)

        response1 = self.client.post(
            url,
            data={
                'name':         'Signed opportunities',
                'success_rate': 0,  # Minimum is 1
            },
        )
        self.assertFormError(
            response1.context['form'],
            field='success_rate',
            errors=_(
                'Ensure this value is greater than or equal to %(limit_value)s.'
            ) % {'limit_value': 1},
        )

        # ---
        response2 = self.client.post(
            url,
            data={
                'name':         'Signed opportunities',
                'success_rate': 101,  # Maximum is 100
            },
        )
        self.assertFormError(
            response2.context['form'],
            field='success_rate',
            errors=_(
                'Ensure this value is less than or equal to %(limit_value)s.'
            ) % {'limit_value': 100},
        )

    # TODO?
    # def test_inneredit(self):
    #     pattern = self._create_pattern()
    #     comp01 = ActObjectivePatternComponent.objects.create(
    #         name='signed opportunities', pattern=pattern, success_rate=50,
    #     )
    #
    #     build_uri = self.build_inneredit_uri
    #     field_name = 'name'
    #     uri = build_uri(comp01, field_name)
    #     self.assertGET200(uri)
    #
    #     name = comp01.name.title()
    #     response = self.client.post(
    #         uri,
    #         data={
    #             # 'entities_lbl': [str(comp01)],
    #             # 'field_value':  name,
    #             field_name: name,
    #         },
    #     )
    #     self.assertNoFormError(response)
    #     self.assertEqual(name, self.refresh(comp01).name)
    #
    #     self.assertGET404(build_uri(comp01, 'success_rate'))
