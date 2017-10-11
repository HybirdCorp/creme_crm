# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0003_v1_6__make_base_abstract_2'),
    ]

    operations = [
        # Step 3: remove links to Base & the Base table too.
        migrations.RemoveField(
            model_name='creditnote',
            name='base_ptr',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='base_ptr',
        ),
        migrations.RemoveField(
            model_name='quote',
            name='base_ptr',
        ),
        migrations.RemoveField(
            model_name='salesorder',
            name='base_ptr',
        ),
        migrations.RemoveField(
            model_name='templatebase',
            name='base_ptr',
        ),
        migrations.DeleteModel('base'),

        # Step 4: alter options
        migrations.AlterModelOptions(
            name='creditnote',
            options={'ordering': ('name',), 'verbose_name': 'Credit note', 'verbose_name_plural': 'Credit notes'},
        ),
        migrations.AlterModelOptions(
            name='invoice',
            options={'ordering': ('name',), 'verbose_name': 'Invoice', 'verbose_name_plural': 'Invoices'},
        ),
        migrations.AlterModelOptions(
            name='quote',
            options={'ordering': ('name',), 'verbose_name': 'Quote', 'verbose_name_plural': 'Quotes'},
        ),
        migrations.AlterModelOptions(
            name='salesorder',
            options={'ordering': ('name',), 'verbose_name': 'Salesorder', 'verbose_name_plural': 'Salesorders'},
        ),
        migrations.AlterModelOptions(
            name='templatebase',
            options={'ordering': ('name',), 'verbose_name': 'Template', 'verbose_name_plural': 'Templates'},
        ),

        # Step 5: finalize fields

        # Step 5.1: FK to CremeEntity are not nullable, are primary keys
        migrations.AlterField(
            model_name='creditnote',
            name='cremeentity_ptr',
            field=models.OneToOneField(parent_link=True, # (+ 'bases' in 0001_initial.py) in Creme1.7
                                       #parent_link=False,
                                       auto_created=True,
                                       primary_key=True,
                                       serialize=False,
                                       #null=False,
                                       to='creme_core.CremeEntity',
                                      ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='cremeentity_ptr',
            field=models.OneToOneField(parent_link=True, # (+ 'bases' in 0001_initial.py) in Creme1.7
                                       #parent_link=False,
                                       auto_created=True,
                                       primary_key=True,
                                       serialize=False,
                                       #null=False,
                                       to='creme_core.CremeEntity',
                                      ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='quote',
            name='cremeentity_ptr',
            field=models.OneToOneField(parent_link=True, # (+ 'bases' in 0001_initial.py) in Creme1.7
                                       #parent_link=False,
                                       auto_created=True,
                                       primary_key=True,
                                       serialize=False,
                                       #null=False,
                                       to='creme_core.CremeEntity',
                                      ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='salesorder',
            name='cremeentity_ptr',
            field=models.OneToOneField(parent_link=True, # (+ 'bases' in 0001_initial.py) in Creme1.7
                                       #parent_link=False,
                                       auto_created=True,
                                       primary_key=True,
                                       serialize=False,
                                       #null=False,
                                       to='creme_core.CremeEntity',
                                      ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='templatebase',
            name='cremeentity_ptr',
            field=models.OneToOneField(parent_link=True, # (+ 'bases' in 0001_initial.py) in Creme1.7
                                       #parent_link=False,
                                       auto_created=True,
                                       primary_key=True,
                                       serialize=False,
                                       #null=False,
                                       to='creme_core.CremeEntity',
                                      ),
            preserve_default=True,
        ),

        # Step 5.2: names have no default value
        migrations.AlterField(
            model_name='creditnote',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='quote',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='salesorder',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='templatebase',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
    ]
