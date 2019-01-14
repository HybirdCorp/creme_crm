# -*- coding: utf-8 -*-

from collections import defaultdict

from django.db import migrations
from django.db.models import Count


def remove_duplicated_relations(apps, schema_editor):
    Relation = apps.get_model('creme_core', 'Relation')

    # NB:
    # - we exclude the relation types corresponding to less than 2 Relation instances,
    #   because they can obviously have duplicates
    # - we exclude type with ID 'my_app-object-...', because they will be removed as symmetric.
    for rtype_id in apps.get_model('creme_core', 'RelationType') \
                        .objects \
                        .filter(id__contains='-subject_') \
                        .annotate(rcount=Count('relation')) \
                        .filter(rcount__gte=2) \
                        .values_list('id', flat=True):
        grouped_rel_ids = defaultdict(list)

        # NB: we order by ID to remove the latest instances (ie: keep the first ones).
        for rel_id, s_id, o_id in Relation.objects \
                                          .filter(type=rtype_id) \
                                          .values_list('id', 'subject_entity', 'object_entity') \
                                          .order_by('id'):
            grouped_rel_ids[(s_id, o_id)].append(rel_id)

        for rel_sig, rel_ids in grouped_rel_ids.items():
            if len(rel_ids) >= 2:
                print('\n    {count} duplicated relation(s) removed: '
                      'subject={subject} type={type} object={object}'.format(
                    count=len(rel_ids)-1,
                    subject=rel_sig[0],
                    object=rel_sig[1],
                    type=rtype_id,
                ))
                Relation.objects.filter(id__in=rel_ids[1:]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0048_v2_0__relation_type_not_null'),
    ]

    operations = [
        migrations.RunPython(remove_duplicated_relations),
    ]
