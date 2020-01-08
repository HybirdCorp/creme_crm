from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrashCleaningCommand',
            fields=[
                ('user', models.OneToOneField(editable=False, on_delete=CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('job', models.ForeignKey(editable=False, on_delete=CASCADE, to='creme_core.Job')),
                ('deleted_count', models.PositiveIntegerField(default=0, editable=False)),
            ],
        ),
    ]
