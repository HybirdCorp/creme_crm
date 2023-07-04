from django.db import migrations


def generate_line_ordering(apps, schema_editor):
    from creme.creme_core.core.paginator import FlowPaginator

    from ..constants import REL_OBJ_HAS_LINE

    doc_models = [
        apps.get_model('billing', name)
        for name in ('Invoice', 'Quote', 'CreditNote', 'SalesOrder')
    ]

    line_models = [
        apps.get_model('billing', name)
        for name in ('ProductLine', 'ServiceLine')
    ]

    for doc_model in doc_models:
        paginator = FlowPaginator(
            queryset=doc_model.objects.values_list('pk'),
            key='id',
            per_page=1024,
        )

        for doc_page in paginator.pages():
            for doc_id in doc_page.object_list:
                for line_model in line_models:
                    for order, line in enumerate(line_model.objects.filter(
                        relations__type=REL_OBJ_HAS_LINE,
                        relations__object_entity=doc_id,
                    ), 1):
                        line.order = order
                        line.save()


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0030_v2_5__lines_order'),
    ]

    operations = [
        migrations.RunPython(generate_line_ordering),
    ]
