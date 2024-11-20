from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userrole',
            name='listable_ctypes',
            field=models.ManyToManyField(
                to='contenttypes.contenttype',
                verbose_name='Listable resources',
                related_name='roles_allowing_list',
            ),
        ),
    ]
