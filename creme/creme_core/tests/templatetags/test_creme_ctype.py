# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.utils.translation import gettext as _

from creme.creme_core.models import Currency, FakePosition, FakeSector
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.utils.translation import get_model_verbose_name

from ..base import CremeTestCase


class CremeCTypeTagsTestCase(CremeTestCase):
    def test_ctype_for_model(self):
        with self.assertNoException():
            template = Template(
                r"{% load creme_ctype %}"
                r"{% ctype_for_model currency_model as currency_ctype %}"
                r"<h1>{{currency_ctype}} ({{currency_ctype.id}})</h1>"
            )
            render = template.render(Context({
                'currency_model': Currency,
            }))

        self.assertEqual(
            '<h1>{vname} ({id})</h1>'.format(
                vname=_('Currency'),
                id=ContentType.objects.get_for_model(Currency).id,
            ),
            render.strip()
        )

    def test_ctype_for_naturalkey(self):
        with self.assertNoException():
            template = Template(
                r"{% load creme_ctype %}"
                r"{% ctype_for_naturalkey app_label='creme_core' model='currency' as cur_ctype %}"
                r"<h1>{{cur_ctype}} ({{cur_ctype.id}})</h1>"
            )
            render = template.render(Context())

        self.assertEqual(
            '<h1>{vname} ({id})</h1>'.format(
                vname=_('Currency'),
                id=ContentType.objects.get_for_model(Currency).id,
            ),
            render.strip()
        )

    @skipIfNotInstalled('creme.documents')
    def test_ctype_for_swappable(self):
        from creme import documents

        Document = documents.get_document_model()

        with self.assertNoException():
            template = Template(
                r"{% load creme_ctype %}"
                r"{% ctype_for_swappable 'DOCUMENTS_DOCUMENT_MODEL' as doc_ctype %}"
                r"<h1>{{doc_ctype}} ({{doc_ctype.id}})</h1>"
            )
            render = template.render(Context())

        self.assertEqual(
            '<h1>{vname} ({id})</h1>'.format(
                vname=Document._meta.verbose_name,
                id=ContentType.objects.get_for_model(Document).id,
            ),
            render.strip()
        )

    def test_ctype_counted_instances_label01(self):
        "Count == 1"
        with self.assertNoException():
            template = Template(
                r'{% load creme_ctype %}'
                r'{% ctype_counted_instances_label ctype=sector_ctype count=1 %}'
            )
            render = template.render(Context({
                'sector_ctype': ContentType.objects.get_for_model(FakeSector),
            }))

        self.assertEqual(
            _('{count} {model}').format(
                count=1,
                model=get_model_verbose_name(model=FakeSector, count=1),
            ),
            render.strip()
        )

    def test_ctype_counted_instances_label02(self):
        "Count == 10, assignment"
        with self.assertNoException():
            template = Template(
                r'{% load creme_ctype %}'
                r'{% ctype_counted_instances_label ctype=pos_ctype count=10 as label %}'
                r'<h1>{{label}}</h1>'
            )
            render = template.render(Context({
                'pos_ctype': ContentType.objects.get_for_model(FakePosition),
            }))

        self.assertEqual(
            '<h1>{}</h1>'.format(_('{count} {model}').format(
                count=10,
                model=get_model_verbose_name(model=FakePosition, count=10),
            )),
            render.strip()
        )

    # TODO: ctype_can_be_merged
    # TODO: ctype_can_be_mass_imported
    # TODO: ctype_has_quickform
