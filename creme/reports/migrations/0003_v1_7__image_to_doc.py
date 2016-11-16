# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.conf import settings
from django.db import migrations

from ..constants import RFT_FIELD


def convert_img_reports(apps, schema_editor):
    if settings.REPORTS_REPORT_MODEL != 'reports.Report':
        return

    get_model = apps.get_model
    ContentType = get_model('contenttypes', 'ContentType')

    ct_app_label, ct_model = settings.DOCUMENTS_FOLDER_MODEL.split('.')
    ct_doc = ContentType.objects.filter(app_label=ct_app_label, model=ct_model.lower()).first()

    if ct_doc is None:
        return

    ct_img = ContentType.objects.get(app_label='media_managers', model='image')
    Field = get_model('reports', 'Field')

    Field.objects.filter(report__ct=ct_img.id, type=RFT_FIELD, name='name').update(name='title')
    Field.objects.filter(report__ct=ct_img.id, type=RFT_FIELD, name='image').update(name='filedata')

    for report in get_model('reports', 'Report').objects.filter(ct=ct_img.id):
        rfields = Field.objects.filter(report=report.id, type=RFT_FIELD, name__in=('height', 'width'))
        if rfields:
            print('The Report "%s" (id=%s) related to Image has column(s) on fields "height/width" which are deleted.' % (
                        report.name, report.id,
                    )
                 )
            rfields.delete()

        print('The Report "%s" (id=%s) related to Image is now related to Document, '
              'but you could have to fix the filtering manually.' % (
                    report.name, report.id
                )
             )

        report.ct = ct_doc
        report.save()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0007_v1_7__image_to_doc_2'),
        ('reports', '0002_v1_6__type_choices'),
    ]

    run_before = [
        ('documents', '0009_v1_7__image_to_doc_4'),
    ]

    operations = [
        migrations.RunPython(convert_img_reports),
    ]
