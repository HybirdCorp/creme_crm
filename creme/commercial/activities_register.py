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

from activities.forms.activity import ActivityCreateForm

from commercial.models import CommercialApproach


def add_commapp_field(form):
    form.fields['is_comapp'] = BooleanField(required=False, label=_(u"Is a commercial approach ?"),
                                            help_text=_(u"Add participants to them be linked to a commercial approach."),
                                           )

def save_commapp_field(form):
    if not form.cleaned_data.get('is_comapp', False):
        return

    participants = [entity for rtype, entity in form.cleaned_data['participants']]

    extra_entity = getattr(form, '_entity_for_relation', None)
    if extra_entity:
        participants.append(extra_entity)

    if not participants:
        return

    now = datetime.now()
    instance = form.instance
    create_comapp = CommercialApproach.objects.create

    for participant in participants:
        create_comapp(title=instance.title,
                      description=instance.description,
                      creation_date=now,
                      creme_entity=participant,
                      related_activity_id=instance.id,
                     )

ActivityCreateForm.add_post_init_callback(add_commapp_field)
ActivityCreateForm.add_post_save_callback(save_commapp_field)
