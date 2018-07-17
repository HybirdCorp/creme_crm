# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from json import loads as json_load, dumps as json_dump

from django.apps import apps
from django.conf import settings
from django.db import migrations


EFC_FIELD = 5
RFT_FIELD = 1


def rename_linkedproject_fields(apps, schema_editor):
    if settings.PROJECTS_TASK_MODEL != 'projects.ProjectTask':
        return

    get_model = apps.get_model

    ct = get_model('contenttypes', 'ContentType').objects.filter(app_label='projects', model='projecttask').first()
    if ct is None:
        return

    ct_id = ct.id

    # HeaderFilter ------------
    for hfilter in get_model('creme_core', 'HeaderFilter').objects.filter(entity_type_id=ct_id)\
                                                                  .exclude(json_cells=None):
        cells_data = json_load(hfilter.json_cells)
        save = False

        for cell_data in cells_data:
            if cell_data.get('type') == 'regular_field' and cell_data.get('value', '').startswith('project'):
                cell_data['value'] = cell_data['value'].replace('project', 'linked_project')
                save = True

        if save:
            hfilter.json_cells = json_dump(cells_data)
            hfilter.save()

    # CustomBlockConfigItem ----------------
    for cbci in get_model('creme_core', 'CustomBlockConfigItem').objects.filter(content_type_id=ct_id) \
                                                                        .exclude(json_cells=None):
        cells_data = json_load(cbci.json_cells)
        save = False

        for cell_data in cells_data:
            if cell_data.get('type') == 'regular_field' and cell_data.get('value', '').startswith('project'):
                cell_data['value'] = cell_data['value'].replace('project', 'linked_project')
                save = True

        if save:
            cbci.json_cells = json_dump(cells_data)
            cbci.save()

    # RelationBlockItem -------------
    for rbci in get_model('creme_core', 'RelationBlockItem').objects.all():
        cells_map_data = json_load(rbci.json_cells_map)
        save = False

        for cells_ctid, cells_data in cells_map_data.items():
            if int(cells_ctid) == ct_id:
                for cell_data in cells_data:
                    if cell_data.get('type') == 'regular_field' and cell_data.get('value', '').startswith('project'):
                        cell_data['value'] = cell_data['value'].replace('project', 'linked_project')
                        save = True

                if save:
                    rbci.json_cells_map = json_dump(cells_map_data)
                    rbci.save()
                    break

    # EntityFilter -------------------
    old_prefix = 'project__'
    new_prefix = 'linked_project__'

    for cond in get_model('creme_core', 'EntityFilterCondition').objects.filter(filter__entity_type_id=ct_id,
                                                                                type=EFC_FIELD,
                                                                                name__startswith='project',
                                                                               ):
        if cond.name == 'project':
            cond.name = 'linked_project'
            cond.save()
        elif cond.name.startswith(old_prefix):
            cond.name = new_prefix + cond.name[len(old_prefix):]
            cond.save()


def rename_report_fields(apps, schema_editor):
    get_model = apps.get_model
    app_label, model_name = settings.PROJECTS_TASK_MODEL.split('.', 1)
    ct = get_model('contenttypes', 'ContentType').objects.filter(app_label=app_label, model=model_name.lower()).first()

    if ct is None:
        return

    for rfield in get_model('reports', 'Field').objects.filter(report__ct_id=ct.id,
                                                               type=RFT_FIELD,
                                                               name__startswith='project',
                                                              ):
        # TODO: doable with F() ?
        rfield.name = rfield.name.replace('project', 'linked_project')
        rfield.save()


def rename_rgraph_abcissa(apps, schema_editor):
    if settings.REPORTS_REPORT_MODEL != 'reports.Report':
        return

    if settings.REPORTS_GRAPH_MODEL != 'reports.ReportGraph':
        return

    get_model = apps.get_model
    app_label, model_name = settings.PROJECTS_TASK_MODEL.split('.', 1)
    ct = get_model('contenttypes', 'ContentType').objects.filter(app_label=app_label, model=model_name.lower()).first()

    if ct is None:
        return

    get_model('reports', 'ReportGraph').objects.filter(linked_report__ct_id=ct.id,
                                                       abscissa='project',
                                                      )\
                                               .update(abscissa='linked_project')


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0014_v1_8__linked_project_field_1'),
    ]

    operations = [
        migrations.RunPython(rename_linkedproject_fields),
    ]

    if apps.is_installed('creme.reports'):
        dependencies.append(
            ('reports', '0004_v1_8__linked_report_field')
        )
        operations += [
            migrations.RunPython(rename_report_fields),
            migrations.RunPython(rename_rgraph_abcissa),
        ]
