from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0188_v3_0__filter_cond_op_str_ids'),
    ]

    operations = [
        migrations.RenameField(
            model_name='entityfiltercondition',
            old_name='type',
            new_name='old_type',
        ),
        migrations.AddField(
            model_name='entityfiltercondition',
            name='type',
            field=models.CharField(default='', max_length=30),
            preserve_default=False,
        ),
    ]
