from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0052_v2_1__home_bricks_per_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='setcredentials',
            name='forbidden',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='setcredentials',
            name='role',
            field=models.ForeignKey(editable=False, on_delete=CASCADE, related_name='credentials', to='creme_core.UserRole'),
        ),
    ]
