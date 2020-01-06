# -*- coding: utf-8 -*-

from collections import defaultdict

from django.db import migrations


def remove_duplicated_favorite_entities(apps, schema_editor):
    mngr = apps.get_model('mobile', 'MobileFavorite').objects
    grouped_fav = defaultdict(list)

    for user_id, entity_id, fav_id in mngr.values_list('user', 'entity', 'id'):
        grouped_fav[(user_id, entity_id)].append(fav_id)

    for fav_ids in grouped_fav.values():
        if len(fav_ids) >= 2:
            mngr.filter(id__in=fav_ids[1:]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('mobile', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_duplicated_favorite_entities),
    ]
