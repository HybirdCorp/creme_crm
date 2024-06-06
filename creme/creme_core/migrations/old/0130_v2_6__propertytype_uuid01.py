from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0129_v2_6__filtercondition_jsonfield02'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremepropertytype',
            name='subject_ctypes_bk',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='relationtype',
            name='subject_properties_bk',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='relationtype',
            name='subject_forbidden_properties_bk',
            field=models.TextField(default=''),
        ),
    ]
