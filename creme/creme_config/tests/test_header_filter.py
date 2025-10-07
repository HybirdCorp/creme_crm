from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.bricks import HeaderFiltersBrick
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import FakeContact, HeaderFilter
from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class HeaderFilterConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    @staticmethod
    def _build_add_url(ct):
        return reverse('creme_config__create_hfilter', args=(ct.id,))

    @staticmethod
    def _build_edit_url(hfilter):
        return reverse('creme_config__edit_hfilter', args=(hfilter.id,))

    def _ctype_labels_from_brick(self, response):
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            HeaderFiltersBrick.id,
        )

        return [
            ct_group[0].tail.strip()
            for ct_group in brick_node.findall(
                './/div[@class="headerfilter-config-group-title"]'
            )
        ]

    def test_portal01(self):
        "Super-user."
        self.login_as_root()

        response = self.assertGET200(reverse('creme_config__hfilters'))
        self.assertTemplateUsed(response, 'creme_config/portals/header-filter.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        ct_labels = self._ctype_labels_from_brick(response)
        if len(ct_labels) < HeaderFiltersBrick.page_size:
            self.assertIn(FakeContact._meta.verbose_name, ct_labels)

    @skipIfNotInstalled('creme.documents')
    def test_portal02(self):
        "Not super-user."
        from creme import documents

        self.login_as_standard(allowed_apps=('documents',))

        response = self.assertGET200(reverse('creme_config__hfilters'))
        self.assertCountEqual(
            self._ctype_labels_from_brick(response),
            [
                model._meta.verbose_name
                for model in (documents.get_document_model(), documents.get_folder_model())
            ],
        )

    @override_settings(FILTERS_INITIAL_PRIVATE=False)
    def test_create01(self):
        "Check app credentials."
        user = self.login_as_standard(allowed_apps=('documents',))

        ct = ContentType.objects.get_for_model(FakeContact)

        url = self._build_add_url(ct)
        self.assertGET403(url)

        # ---
        role = user.role
        role.allowed_apps = ['documents', 'creme_core']
        role.save()
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Create a view for «{model}»').format(model='Test Contact'),
            context1.get('title'),
        )

        with self.assertNoException():
            form = context1['form']

        self.assertIs(form.initial.get('is_private'), False)

        name = 'My simple view'
        response2 = self.client.post(
            url,
            data={
                'name':  name,
                'cells': 'regular_field-last_name',
            },
        )
        self.assertNoFormError(response2)

        hfilter = self.get_object_or_fail(HeaderFilter, name=name)
        self.assertEqual(ct, hfilter.entity_type)
        self.assertIsNone(hfilter.user)
        self.assertTrue(hfilter.is_custom)
        self.assertFalse(hfilter.is_private)

        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, 'last_name')],
            hfilter.cells,
        )

    @override_settings(FILTERS_INITIAL_PRIVATE=True)
    def test_create02(self):
        self.login_as_standard()

        response = self.assertGET200(
            self._build_add_url(ContentType.objects.get_for_model(FakeContact))
        )
        form = self.get_form_or_fail(response)
        self.assertIs(form.initial.get('is_private'), True)

    def test_edit01(self):
        self.login_as_root()

        name = 'Contact view'
        field1 = 'first_name'
        hfilter = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name=name,
            model=FakeContact, is_custom=True,
            cells=[(EntityCellRegularField, field1)],
        ).get_or_create()[0]

        url = self._build_edit_url(hfilter)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit «{object}»').format(object=hfilter.name),
            context1.get('title'),
        )

        with self.assertNoException():
            submit_label = context1['submit_label']

        self.assertEqual(_('Save the view'), submit_label)

        name += ' v2'
        field2 = 'last_name'
        response2 = self.client.post(
            url,
            data={
                'name':  name,
                'cells': f'regular_field-{field1},regular_field-{field2}',
            },
        )
        self.assertNoFormError(response2)

        hfilter = self.refresh(hfilter)
        self.assertEqual(name, hfilter.name)
        self.assertTrue(hfilter.is_custom)
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, field1),
                EntityCellRegularField.build(FakeContact, field2),
            ],
            hfilter.cells,
        )

    def test_edit02(self):
        "Can not edit a HeaderFilter which belongs to another user."
        self.login_as_standard()

        hfilter = HeaderFilter.objects.proxy(
            id='tests-hf_contact', name='Contact view',
            model=FakeContact, is_custom=True,
            user=self.create_user(1), cells=[],
        ).get_or_create()[0]
        self.assertGET403(self._build_edit_url(hfilter))
