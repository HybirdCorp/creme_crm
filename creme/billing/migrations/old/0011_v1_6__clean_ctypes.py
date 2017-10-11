# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.db import migrations


reports_installed = apps.is_installed('creme.reports')

CFIELD_INT         = 1
CFIELD_FLOAT       = 2
CFIELD_BOOL        = 3
CFIELD_STR         = 10
CFIELD_DATETIME    = 20
CFIELD_ENUM        = 100
CFIELD_MULTI_ENUM  = 101
CFIELD_TABLES = {
    CFIELD_INT:        'CustomFieldInteger',
    CFIELD_FLOAT:      'CustomFieldFloat',
    CFIELD_BOOL:       'CustomFieldBoolean',
    CFIELD_STR:        'CustomFieldString',
    CFIELD_DATETIME:   'CustomFieldDateTime',
    CFIELD_ENUM:       'CustomFieldEnum',
    CFIELD_MULTI_ENUM: 'CustomFieldMultiEnum',
}


def remove_old_ctypes(apps, schema_editor):
    get_model = apps.get_model
    ContentType = get_model('contenttypes', 'ContentType')

    ContentType.objects.filter(app_label='billing', model='base').delete()

    ct_line = ContentType.objects.filter(app_label='billing', model='line').first()

    if ct_line is not None:
        # Models which can be safely deleted
        get_model('creme_core', 'HeaderFilter').objects.filter(entity_type=ct_line.id).delete()
        get_model('creme_core', 'SearchConfigItem').objects.filter(content_type=ct_line.id).delete()
        get_model('creme_core', 'BlockDetailviewLocation').objects.filter(content_type=ct_line.id).delete()
        get_model('creme_core', 'CustomBlockConfigItem').objects.filter(content_type=ct_line.id).delete()
        get_model('creme_core', 'ButtonMenuItem').objects.filter(content_type=ct_line.id).delete()

        ct_pline = ContentType.objects.get(app_label='billing', model='productline')

        # Custom Fields --------------------------------------------------------
        CustomField = get_model('creme_core', 'CustomField')
        CustomFieldEnumValue = get_model('creme_core', 'CustomFieldEnumValue')

        cfields = CustomField.objects.filter(content_type=ct_line.id)
        if cfields:
            ct_sline = ContentType.objects.get(app_label='billing', model='serviceline')

            for cfield in cfields:
                print('BEWARE! The CustomField "%s" is duplicated from billing.Line '
                      'to billing.ProductLine & billing.ServiceLine.' % cfield.name
                     )

                # The original CustomField is linked to ProductLine & we copy it for ServiceLine
                cfield_sline = CustomField.objects.create(name=cfield.name,
                                                          content_type=ct_sline,
                                                          field_type=cfield.field_type,
                                                         )
                cfield_values_sline = get_model('creme_core', CFIELD_TABLES[cfield.field_type])\
                                               .objects.filter(custom_field=cfield,
                                                               entity__entity_type=ct_sline.id,
                                                              )

                cfield_values_sline.update(custom_field=cfield_sline)

                if cfield.field_type in (CFIELD_ENUM, CFIELD_MULTI_ENUM):
                    enum_maps = {enum_value.id: CustomFieldEnumValue.objects.create(custom_field=cfield_sline,
                                                                                    value=enum_value.value,
                                                                                    )
                                 for enum_value in CustomFieldEnumValue.objects.filter(custom_field=cfield)
                                }

                    if cfield.field_type == CFIELD_ENUM:
                        for cfvalue in cfield_values_sline:
                            cfvalue.value = enum_maps[cfvalue.value_id]
                            cfvalue.save()
                    else:  # CFIELD_MULTI_ENUM
                        for cfvalue in cfield_values_sline:
                            cfvalue.value = [enum_maps[enum.id] for enum in cfvalue.value]

                cfield.content_type = ct_pline
                cfield.save()

        # EntityFilters --------------------------------------------------------
        for efilter in get_model('creme_core', 'EntityFilter').objects.filter(entity_type=ct_line.id):
            print('BEWARE! The filter "%s" is converted from billing.Line to billing.ProductLine.' % efilter.name)
            efilter.entity_type = ct_pline
            efilter.save()

        # Reports --------------------------------------------------------------
        if reports_installed:
            for report in get_model('reports', 'Report').objects.filter(ct=ct_line.id):
                print('BEWARE! The report "%s" (id=%s) is converted from billing.Line to billing.ProductLine.' % (
                                report.name, report.id
                            )
                     )
                report.ct = ct_pline
                report.save()

        ct_line.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0011_v1_6__blockconfig_per_role'),
        ('billing',    '0010_v1_6__custom_blocks'),
    ]

    if reports_installed:
        dependencies.append(('reports', '0001_initial'))

    operations = [
        migrations.RunPython(remove_old_ctypes),
    ]
