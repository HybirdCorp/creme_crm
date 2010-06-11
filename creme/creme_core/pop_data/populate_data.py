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

#TODO: remove this file --> credentials in each app

import logging

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.utils import create_or_update_models_instance as create

from creme_core.models import CremeRole
from creme_core.models import CremeAppDroit, CremeProfile, CremeDroitEntityType

from persons.models import Contact, Organisation

from activities.models import Activity

def set_up():
    print 'populate REMOVE ME SOON data begin'

    #populate_data_initial()

    get_ct = ContentType.objects.get_for_model

    admin = User.objects.get_or_create(pk=1)[0]

    #TODO: MOVE.....
    create(CremeAppDroit, 1, name_app= "persons",  type_droit_id=2)
    create(CremeAppDroit, 2, name_app= "activity", type_droit_id=2)
    create(CremeAppDroit, 3, name_app= "document", type_droit_id=2)

    Role_Admin         = create(CremeRole, 1, name='Admin',              user_id=admin.pk)
    Role_DR            = create(CremeRole, 2, name='Directeur Regional', superieur_id=Role_Admin.pk, user_id=admin.pk)
    Role_Administratif = create(CremeRole, 3, name='Administratif',      superieur_id=Role_Admin.pk, user_id=admin.pk)
    Role_Technicien    = create(CremeRole, 4, name='Technicien',         superieur_id=Role_Admin.pk, user_id=admin.pk)
    Role_Commercial    = create(CremeRole, 5, name='Commercial',         superieur_id=Role_Admin.pk, user_id=admin.pk)
    Role_Formateur     = create(CremeRole, 6, name='Formateur',          superieur_id=Role_Admin.pk, user_id=admin.pk)

    create(CremeProfile, 1, user_id=admin.pk, creme_role_id=Role_Admin.pk) #admin's profil

    #TODO: MOVE.....
    Acces_CRM        = create(CremeAppDroit, 1, name_app='persons',    type_droit_id=2)
    Acces_document   = create(CremeAppDroit, 2, name_app='documents',  type_droit_id=2) 
    Acces_activity   = create(CremeAppDroit, 3, name_app='activity',   type_droit_id=2)
    Acces_formations = create(CremeAppDroit, 4, name_app='formations', type_droit_id=2)

    #TODO: MOVE.....
    Droit_Lecture_contact      = create(CremeDroitEntityType, 1, content_type_id=get_ct(Contact).id,      type_droit_id =1, type_ensemble_fiche_id =1)
    Droit_Lecture_organisation = create(CremeDroitEntityType, 2, content_type_id=get_ct(Organisation).id, type_droit_id =1, type_ensemble_fiche_id =1)
    Droit_Lecture_activity     = create(CremeDroitEntityType, 3, content_type_id=get_ct(Activity).id, type_droit_id =1, type_ensemble_fiche_id =1)

    #TODO: MOVE.....
    Role_Commercial.droits_app.add(Acces_CRM)
    Role_Commercial.droits_app.add(Acces_document)
    Role_Commercial.droits_app.add(Acces_activity)
    Role_Commercial.droits_entity_type.add(Droit_Lecture_contact)
    Role_Commercial.droits_entity_type.add(Droit_Lecture_organisation)
    Role_Commercial.droits_entity_type.add(Droit_Lecture_activity)
    Role_Commercial.save()

    #TODO: MOVE.....
    Role_Formateur.droits_app.add(Acces_CRM)
    Role_Formateur.droits_app.add(Acces_document)
    Role_Formateur.droits_app.add(Acces_activity)
    Role_Formateur.droits_app.add(Acces_formations)
    Role_Formateur.droits_entity_type.add(Droit_Lecture_contact)
    Role_Formateur.droits_entity_type.add(Droit_Lecture_organisation)
    Role_Formateur.droits_entity_type.add(Droit_Lecture_activity)
    Role_Formateur.save()


    print 'populate REMOVE ME SOON data end'
