# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


RFT_FIELD = 1


def rename_linkedfolder_fields(apps, schema_editor):
    get_model = apps.get_model
    app_label, model_name = settings.DOCUMENTS_DOCUMENT_MODEL.split('.', 1)
    ct = get_model('contenttypes', 'ContentType').objects.filter(app_label=app_label, model=model_name.lower()).first()

    if ct is None:
        return

    for rfield in get_model('reports', 'Field').objects.filter(report__ct_id=ct.id,
                                                               type=RFT_FIELD,
                                                               name__startswith='folder',
                                                              ):
        # TODO: doable with F() ?
        rfield.name = rfield.name.replace('folder', 'linked_folder')
        rfield.save()


def rename_linkedfolder_graphs(apps, schema_editor):
    if settings.REPORTS_REPORT_MODEL != 'reports.Report':
        return

    if settings.REPORTS_GRAPH_MODEL != 'reports.ReportGraph':
        return

    get_model = apps.get_model
    app_label, model_name = settings.DOCUMENTS_DOCUMENT_MODEL.split('.', 1)
    ct = get_model('contenttypes', 'ContentType').objects.filter(app_label=app_label, model=model_name.lower()).first()

    if ct is None:
        return

    get_model('reports', 'ReportGraph').objects.filter(linked_report__ct_id=ct.id,
                                                       abscissa='folder',
                                                      )\
                                               .update(abscissa='linked_folder')


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0004_v1_8__linked_report_field'),
        ('documents', '0014_v1_8__linked_folder_field_1'),
    ]

    operations = [
        migrations.RunPython(rename_linkedfolder_fields),
        migrations.RunPython(rename_linkedfolder_graphs),
    ]
