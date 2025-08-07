from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        # ('creme_core', '0160_v2_7__customentitytype'),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomEntity1',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity10',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity11',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity12',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity13',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity14',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity15',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity16',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity17',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity18',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity19',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity2',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity20',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity3',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity4',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity5',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity6',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity7',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity8',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='CustomEntity9',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to='creme_core.cremeentity')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
