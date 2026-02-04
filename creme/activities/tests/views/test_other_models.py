from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.activities.constants import UUID_TYPE_MEETING, UUID_TYPE_PHONECALL
from creme.activities.models import ActivitySubType, ActivityType
from creme.activities.views.other_models import NarrowedSubTypesBrick
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class ActivitySubTypeConfigViewsTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_portal(self):
        self.login_as_standard(admin_4_apps=('activities',))

        atype = self.get_object_or_fail(ActivityType, uuid=UUID_TYPE_PHONECALL)
        response = self.assertGET200(
            reverse('activities__type_portal', args=(atype.id,)),
        )
        self.assertTemplateUsed(response, 'activities/config/activity-type-portal.html')

        get_context = response.context.get
        self.assertEqual(atype, get_context('activity_type'))
        self.assertEqual(_('Activities'), get_context('app_verbose_name'))
        self.assertEqual(
            reverse('activities__reload_type_brick', args=(atype.id,)),
            get_context('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=NarrowedSubTypesBrick,
        )

        texts = {
            text
            for row in self.get_brick_table_rows(brick_node)
            for cell in row.findall('.//td') if (text := cell.text.strip())
        }
        self.assertIn(
            ActivitySubType.objects.filter(type=atype).first().name,
            texts,
        )
        self.assertNotIn(
            ActivitySubType.objects.filter(type__uuid=UUID_TYPE_MEETING).first().name,
            texts,
        )

    def test_creation(self):
        self.login_as_standard(admin_4_apps=('activities',))

        atype = self.get_object_or_fail(ActivityType, uuid=UUID_TYPE_PHONECALL)
        url = reverse('activities__create_subtype', args=(atype.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        context = response1.context
        self.assertEqual(
            pgettext('activities-type', 'New sub-type for «{type}»').format(type=atype),
            context.get('title'),
        )
        self.assertEqual(
            pgettext('activities-type', 'Save the sub-type'),
            context.get('submit_label'),
        )

        with self.assertNoException():
            fields = context['form'].fields
        self.assertIn('name', fields)
        self.assertEqual(1, len(fields))

        # POST ---
        name = 'New subtype'
        self.assertNoFormError(self.client.post(url, data={'name': name}))
        self.get_object_or_fail(ActivitySubType, name=name, type=atype)

    def test_reload_brick(self):
        self.login_as_standard(admin_4_apps=('activities',))

        atype = self.get_object_or_fail(ActivityType, uuid=UUID_TYPE_PHONECALL)
        url = reverse('activities__reload_type_brick', args=(atype.id,))
        self.assertGET404(url)  # No brick ID
        self.assertGET404(url, data={'brick_id': 'invalid'})

        response = self.assertGET200(url, data={'brick_id': NarrowedSubTypesBrick.id})
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertIsList(content, length=1)

        brick_data = content[0]
        self.assertEqual(2, len(brick_data))
        self.assertEqual(NarrowedSubTypesBrick.id, brick_data[0])
        self.assertIn(f' id="brick-{NarrowedSubTypesBrick.id}"', brick_data[1])
        self.assertIn(f' data-brick-id="{NarrowedSubTypesBrick.id}"', brick_data[1])

    def test_reorder_sub_types(self):
        self.login_as_standard(admin_4_apps=('activities',))

        create_type = ActivityType.objects.create
        atype1 = create_type(name='Type #1', order=1000)
        atype2 = create_type(name='Type #2', order=1001)

        create_sub_type = ActivitySubType.objects.create
        subtype11 = create_sub_type(type=atype1, name='Sub-type #1', order=1)
        subtype12 = create_sub_type(type=atype1, name='Sub-type #2', order=2)
        subtype13 = create_sub_type(type=atype1, name='Sub-type #3', order=3)
        subtype21 = create_sub_type(type=atype2, name='Sub-type #4', order=1)
        subtype22 = create_sub_type(type=atype2, name='Sub-type #5', order=2)

        url = reverse('activities__reorder_sub_type', args=(subtype11.id,))
        data = {'target': 3}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertEqual(3, self.refresh(subtype11).order)
        self.assertEqual(1, self.refresh(subtype12).order)
        self.assertEqual(2, self.refresh(subtype13).order)
        self.assertEqual(1, self.refresh(subtype21).order)
        self.assertEqual(2, self.refresh(subtype22).order)

    def test_forbidden(self):
        self.login_as_standard(allowed_apps=('activities',))  # admin_4_apps=('activities',)

        atype_id = ActivityType.objects.first().id
        self.assertGET403(reverse('activities__type_portal', args=(atype_id,)))
        self.assertGET403(reverse('activities__create_subtype', args=(atype_id,)))
        self.assertGET403(reverse('activities__reload_type_brick', args=(atype_id,)))

        subtype_id = ActivitySubType.objects.first().id
        self.assertPOST403(
            reverse('activities__reorder_sub_type', args=(subtype_id,)),
            data={'target': 3},
        )
