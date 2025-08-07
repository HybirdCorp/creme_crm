from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0158_v2_7__portable_ctype'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='buttonmenuitem',
            options={
                'ordering': ('order',),
                'verbose_name': 'Button to display',
                'verbose_name_plural': 'Buttons to display',
            },
        ),
        migrations.AddField(
            model_name='buttonmenuitem',
            name='role',
            field=models.ForeignKey(
                to='creme_core.userrole', verbose_name='Related role',
                default=None, null=True, on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name='buttonmenuitem',
            name='superuser',
            field=models.BooleanField(
                default=False, editable=False, verbose_name='related to superusers',
            ),
        ),
    ]
