# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from datetime import datetime

from django.utils.translation import ugettext as _
from django.forms import BooleanField

from activities.forms.activity import ActivityCreateForm, ActivityEditForm

from commercial.models import CommercialApproach


def add_commapp_field(form):
    form.fields['is_comapp'] = BooleanField(required=False, label=_(u"Is a commercial approach ?"),
                                            help_text=_(u"All participants (except users), subjects and linked entities will be linked to a commercial approach."),
                                           initial=True)

def save_commapp_field(form):
    cleaned_data = form.cleaned_data

    if not cleaned_data.get('is_comapp', False):
        return

    comapp_subjects = list(cleaned_data['other_participants'])
    comapp_subjects += cleaned_data['subjects']
    comapp_subjects += cleaned_data['linked_entities']

    if not comapp_subjects:
        return

    now = datetime.now()
    instance = form.instance
    create_comapp = CommercialApproach.objects.create

    for entity in comapp_subjects:
        create_comapp(title=instance.title,
                      description=instance.description,
                      creation_date=now,
                      creme_entity=entity,
                      related_activity_id=instance.id,
                     )

def update_commapp(form):
    instance = form.instance
    CommercialApproach.objects.filter(related_activity=instance).update(title=instance.title)

ActivityCreateForm.add_post_init_callback(add_commapp_field)
ActivityCreateForm.add_post_save_callback(save_commapp_field)

ActivityEditForm.add_post_save_callback(update_commapp)
