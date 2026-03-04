from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0177_v2_8__misc_created_n_modified02'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeuser',
            name='roles',
            field=models.ManyToManyField(
                to='creme_core.userrole', verbose_name='Possible roles',
                blank=True, related_name='+',
                help_text=(
                    'A normal user must have at least one role.\n'
                    ' - A user with no role will be a SUPERUSER.\n'
                    ' - If you choose several roles, the user will be able to switch between them.'
                ),
            ),
        ),
        migrations.AlterField(
            model_name='cremeuser',
            name='is_superuser',
            field=models.BooleanField(default=False, editable=False, verbose_name='Is a superuser?'),
        ),
        migrations.AlterField(
            model_name='cremeuser',
            name='role',
            field=models.ForeignKey(
                to='creme_core.userrole', verbose_name='Role', null=True,
                editable=False, on_delete=models.PROTECT,
            ),
        ),
    ]
