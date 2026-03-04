from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0179_v2_8__user_roles02'),
    ]

    operations = [
        migrations.AddField(
            model_name='userrole',
            name='raw_special_perms',
            field=models.TextField(default=''),
        ),
    ]
