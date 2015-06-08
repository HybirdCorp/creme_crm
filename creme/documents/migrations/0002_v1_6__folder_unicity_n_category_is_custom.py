# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from itertools import count

from django.conf import settings
from django.db import models, migrations
from django.utils import translation

from ..constants import (DOCUMENTS_FROM_ENTITIES, DOCUMENTS_FROM_ENTITIES_NAME,
        DOCUMENTS_FROM_EMAILS, DOCUMENTS_FROM_EMAILS_NAME)


def consolidate_categories(apps, schema_editor):
    FolderCategory = apps.get_model('documents', 'FolderCategory')

    def fix_category(pk, name):
        try:
            cat = FolderCategory.objects.get(pk=pk, name=name)
        except FolderCategory.DoesNotExist:
            name_stealer = FolderCategory.objects.filter(name=name).first() # name is unique, so there cannot be more than 1

            if name_stealer:
                for i in count(start=1):
                    new_name = name + ' #%s' % i

                    if not FolderCategory.objects.filter(name=new_name).exists():
                        name_stealer.name = new_name
                        name_stealer.save()
                        break

#            FolderCategory.objects.update_or_create(pk=pk,
#                                                    defaults={'name':      name,
#                                                              'is_custom': False,
#                                                             }
#                                                   )
#
#            from django.db import connection
#            from django.core.management.color import no_style
#            cursor = connection.cursor()
#            for line in connection.ops.sequence_reset_sql(no_style(), [FolderCategory]):
#                cursor.execute(line)
            try:
                cat = FolderCategory.objects.get(pk=pk)
            except FolderCategory.DoesNotExist:
                pass # OK the creation will be done by populate.py
            else:
                cat.name = name
                cat.is_custom = False
                cat.save()
        else:
            cat.is_custom = False
            cat.save()

    translation.activate(settings.LANGUAGE_CODE)
    fix_category(DOCUMENTS_FROM_ENTITIES, unicode(DOCUMENTS_FROM_ENTITIES_NAME))
    fix_category(DOCUMENTS_FROM_EMAILS,   unicode(DOCUMENTS_FROM_EMAILS_NAME))


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='folder',
            name='title',
            field=models.CharField(max_length=100, verbose_name='Title'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='folder',
            unique_together=set([('title', 'parent_folder', 'category')]),
        ),
        migrations.AddField(
            model_name='foldercategory',
            name='is_custom',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),

        migrations.RunPython(consolidate_categories),
    ]
