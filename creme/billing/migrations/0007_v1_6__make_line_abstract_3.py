# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0006_v1_6__make_line_abstract_2'),
    ]

    operations = [
        # Step 3: remove links to Base & the Base table too.
        migrations.RemoveField(
            model_name='productline',
            name='line_ptr',
        ),
        migrations.RemoveField(
            model_name='serviceline',
            name='line_ptr',
        ),
        #TODO: useful ??
        #migrations.RemoveField(
            #model_name='line',
            #name='cremeentity_ptr',
        #),
        #migrations.RemoveField(
            #model_name='line',
            #name='vat_value',
        #),
        migrations.DeleteModel(
            name='Line',
        ),

        # Step 4: alter options
        migrations.AlterModelOptions(
            name='productline',
            options={'ordering': ('created',), 'verbose_name': 'Product line', 'verbose_name_plural': 'Product lines'},
        ),
        migrations.AlterModelOptions(
            name='serviceline',
            options={'ordering': ('created',), 'verbose_name': 'Service line', 'verbose_name_plural': 'Service lines'},
        ),

        # Step 5: FK to CremeEntity are finalized (not nullable, primary key)
        migrations.AlterField(
            model_name='productline',
            name='cremeentity_ptr',
            field=models.OneToOneField(#parent_link=False, #parent_link=True (+ 'bases' in 0001_initial.py) in Creme1.7
                                       parent_link=True,
                                       auto_created=True,
                                       primary_key=True,
                                       serialize=False,
                                       #null=False,
                                       to='creme_core.CremeEntity',
                                      ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='serviceline',
            name='cremeentity_ptr',
            field=models.OneToOneField(#parent_link=False, #parent_link=True (+ 'bases' in 0001_initial.py) in Creme1.7
                                       parent_link=True,
                                       auto_created=True,
                                       primary_key=True,
                                       serialize=False,
                                       #null=False,
                                       to='creme_core.CremeEntity',
                                      ),
            preserve_default=True,
        ),
    ]

