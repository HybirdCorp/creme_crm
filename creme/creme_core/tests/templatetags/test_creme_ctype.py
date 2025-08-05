from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language

# from creme.creme_core.models import FakePosition
from creme.creme_core.models import (
    Currency,
    CustomEntityType,
    FakeContact,
    FakeSector,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.utils.translation import smart_model_verbose_name

from ..base import CremeTestCase


class CremeCTypeTagsTestCase(CremeTestCase):
    # def test_ctype_for_model(self):  # DEPRECATED
    #     with self.assertNoException():
    #         template = Template(
    #             r"{% load creme_ctype %}"
    #             r"{% ctype_for_model currency_model as currency_ctype %}"
    #             r"<h1>{{currency_ctype}} ({{currency_ctype.id}})</h1>"
    #         )
    #         render = template.render(Context({
    #             'currency_model': Currency,
    #         }))
    #
    #     self.assertEqual(
    #         '<h1>{vname} ({id})</h1>'.format(
    #             vname=_('Currency'),
    #             id=ContentType.objects.get_for_model(Currency).id,
    #         ),
    #         render.strip()
    #     )

    def test_ctype_for_instance(self):
        with self.assertNoException():
            template = Template(
                r"{% load creme_ctype %}"
                r"{% with currency_ctype=currency|ctype_for_instance %}"
                r"<h1>{{currency_ctype}} ({{currency_ctype.id}})</h1>"
                r"{% endwith %}"
                r"<span>{{currency_model|ctype_for_instance}}</span>"
            )
            render = template.render(Context({
                'currency': Currency.objects.first(),
                'currency_model': Currency,  # Works with model too
            }))

        self.assertEqual(
            '<h1>{vname} ({id})</h1><span>{vname}</span>'.format(
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

    # @skipIfNotInstalled('creme.documents')
    # def test_ctype_for_swappable__simpletag(self):  # DEPRECATED
    #     from creme import documents
    #
    #     Document = documents.get_document_model()
    #
    #     with self.assertNoException():
    #         template = Template(
    #             r"{% load creme_ctype %}"
    #             r"{% ctype_for_swappable 'DOCUMENTS_DOCUMENT_MODEL' as doc_ctype %}"
    #             r"<h1>{{doc_ctype}} ({{doc_ctype.id}})</h1>"
    #         )
    #         render = template.render(Context())
    #
    #     self.assertEqual(
    #         '<h1>{vname} ({id})</h1>'.format(
    #             vname=Document._meta.verbose_name,
    #             id=ContentType.objects.get_for_model(Document).id,
    #         ),
    #         render.strip()
    #     )

    @skipIfNotInstalled('creme.documents')
    def test_ctype_for_swappable(self):
        from creme import documents

        Document = documents.get_document_model()

        with self.assertNoException():
            template = Template(
                r"{% load creme_ctype %}"
                r"{% with doc_ctype='DOCUMENTS_DOCUMENT_MODEL'|ctype_for_swappable %}"
                r"<h1>{{doc_ctype}} ({{doc_ctype.id}})</h1>"
                r"{% endwith %}"
            )
            render = template.render(Context())

        self.assertEqual(
            '<h1>{vname} ({id})</h1>'.format(
                vname=Document._meta.verbose_name,
                id=ContentType.objects.get_for_model(Document).id,
            ),
            render.strip()
        )

    def test_ctype_verbose_name(self):
        with self.assertNoException():
            template = Template(
                r'{% load creme_ctype %}'
                r'{{sector_ctype|ctype_verbose_name:1}}#'
                r'{{sector_ctype|ctype_verbose_name:10}}#'
                # r'{{sector_ctype|ctype_verbose_name}}'  # DEPRECATED
            )
            render = template.render(Context({
                'sector_ctype': ContentType.objects.get_for_model(FakeSector),
            }))

        self.assertEqual(
            f'{smart_model_verbose_name(model=FakeSector, count=1)}#'
            f'{smart_model_verbose_name(model=FakeSector, count=10)}#',
            # f'{FakeSector._meta.verbose_name}',
            render.strip(),
        )

    @override_language('en')
    def test_ctype_verbose_name__custom_type(self):
        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Warehouse'
        ce_type.plural_name = 'Warehouses'
        ce_type.save()

        with self.assertNoException():
            template = Template(
                r'{% load creme_ctype %}'
                r'{{custom_ctype|ctype_verbose_name:1}}#'
                r'{{custom_ctype|ctype_verbose_name:10}}#'
                # r'{{custom_ctype|ctype_verbose_name}}'  # DEPRECATED
            )
            render = template.render(Context({
                'custom_ctype': ContentType.objects.get_for_model(ce_type.entity_model),
            }))

        self.assertEqual(
            # f'{ce_type.name}#{ce_type.plural_name}#{ce_type.name}',
            f'{ce_type.name}#{ce_type.plural_name}#',
            render.strip(),
        )

    def test_ctype_verbose_name_plural(self):
        with self.assertNoException():
            template = Template(
                r'{% load creme_ctype %}'
                r'{{sector_ctype|ctype_verbose_name_plural}}#'
                r'{{contact_ctype|ctype_verbose_name_plural}}'
            )
            render = template.render(Context({
                'sector_ctype': ContentType.objects.get_for_model(FakeSector),
                'contact_ctype': ContentType.objects.get_for_model(FakeContact),
            }))

        self.assertEqual(
            f'{FakeSector._meta.verbose_name_plural}#'
            f'{FakeContact._meta.verbose_name_plural}',
            render.strip(),
        )

    def test_ctype_verbose_name_plural__custom_type(self):
        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Warehouse'
        ce_type.plural_name = 'Warehouses'
        ce_type.save()

        with self.assertNoException():
            template = Template(
                r'{% load creme_ctype %}'
                r'{{custom_ctype|ctype_verbose_name_plural}}'
            )
            render = template.render(Context({
                'custom_ctype': ContentType.objects.get_for_model(ce_type.entity_model),
            }))

        self.assertEqual(ce_type.plural_name, render.strip())

    # def test_ctype_counted_instances_label__simpletag01(self):  # DEPRECATED
    #     "Count == 1."
    #     with self.assertNoException():
    #         template = Template(
    #             r'{% load creme_ctype %}'
    #             r'{% ctype_counted_instances_label ctype=sector_ctype count=1 %}'
    #         )
    #         render = template.render(Context({
    #             'sector_ctype': ContentType.objects.get_for_model(FakeSector),
    #         }))
    #
    #     self.assertEqual(
    #         _('{count} {model}').format(
    #             count=1,
    #             model=smart_model_verbose_name(model=FakeSector, count=1),
    #         ),
    #         render.strip(),
    #     )

    # def test_ctype_counted_instances_label__simpletag02(self):  # DEPRECATED
    #     "Count == 10, assignment."
    #     with self.assertNoException():
    #         template = Template(
    #             r'{% load creme_ctype %}'
    #             r'{% ctype_counted_instances_label ctype=pos_ctype count=10 as label %}'
    #             r'<h1>{{label}}</h1>'
    #         )
    #         render = template.render(Context({
    #             'pos_ctype': ContentType.objects.get_for_model(FakePosition),
    #         }))
    #
    #     self.assertEqual(
    #         '<h1>{}</h1>'.format(_('{count} {model}').format(
    #             count=10,
    #             model=smart_model_verbose_name(model=FakePosition, count=10),
    #         )),
    #         render.strip()
    #     )

    def test_ctype_counted_instances_label(self):
        with self.assertNoException():
            template = Template(
                r'{% load creme_ctype %}'
                r'{{ sector_ctype|ctype_counted_label:1 }}#'
                r'{{ sector_ctype|ctype_counted_label:10 }}'
            )
            render = template.render(Context({
                'sector_ctype': ContentType.objects.get_for_model(FakeSector),
            }))

        fmt = _('{count} {model}').format
        self.assertEqual(
            f'{fmt(count=1, model=smart_model_verbose_name(model=FakeSector, count=1))}#'
            f'{fmt(count=10, model=smart_model_verbose_name(model=FakeSector, count=10))}',
            render.strip(),
        )

    # TODO: ctype_can_be_merged
    # TODO: ctype_can_be_mass_imported
    # TODO: ctype_has_quickform
