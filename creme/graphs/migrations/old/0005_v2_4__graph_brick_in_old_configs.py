from django.db import migrations


# We add the new brick on existing configurations
def fix_bricks_config(apps, schema_editor):
    get_model = apps.get_model
    graph_ct = get_model(
        'contenttypes', 'ContentType'
    ).objects.filter(app_label='graphs', model='graph').first()

    if graph_ct is None:
        return

    bdv_model = get_model('creme_core', 'BrickDetailviewLocation')

    creation_kwargs = {
        'content_type_id': graph_ct.id,
        'brick_id': 'block_graphs-relation_chart',
        'zone': 3,  # RIGHT
        'order': 1,
    }
    graph_bdv = bdv_model.objects.filter(content_type=graph_ct)

    if graph_bdv.exists():
        bdv_model.objects.create(**creation_kwargs)

    if graph_bdv.filter(superuser=True).exists():
        bdv_model.objects.create(**creation_kwargs, superuser=True)

    for role_id in graph_bdv.exclude(role=None).values_list('role', flat=True).distinct():
        bdv_model.objects.create(**creation_kwargs, role_id=role_id)


class Migration(migrations.Migration):
    dependencies = [
        ('graphs', '0004_v2_4__rootnode_entity_ctype03'),
    ]

    operations = [
        migrations.RunPython(fix_bricks_config),
    ]
