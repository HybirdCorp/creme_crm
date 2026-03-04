from django.db import migrations


def delete_graphes(apps, schema_editor):
    # NB: if we do not delete them explicitly, the CremeEntity part is not
    #     removed when the table is deleted (0019_v2_8__reportchart04.py)
    apps.get_model('reports', 'ReportGraph').objects.all().delete()


# def delete_ctype(apps, schema_editor):
#     apps.get_model('contenttypes', 'ContentType').objects.filter(
#         app_label='reports', model='reportgraph',
#     ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0017_v2_8__reportchart02'),
    ]

    operations = [
        # We delete Graphes in a separated migration to allow third code to
        # perform after data migration & before cleaning
        migrations.RunPython(delete_graphes),
        # TODO: remove the ContentType for ReportGraph in the next major version
        # migrations.RunPython(delete_ctype),
    ]
