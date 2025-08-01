################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from functools import partial

from django.core.exceptions import ValidationError
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from creme import documents
from creme.creme_core import auth
from creme.creme_core.forms.validators import validate_linkable_model
from creme.creme_core.models import Relation
from creme.creme_core.utils import ellipsis
from creme.creme_core.views import generic

from .. import constants, custom_forms
from ..constants import DEFAULT_HFILTER_DOCUMENT
from ..models import FolderCategory

Folder = documents.get_folder_model()
Document = documents.get_document_model()


class DocumentCreation(generic.EntityCreation):
    model = Document
    form_class = custom_forms.DOCUMENT_CREATION_CFORM

    def get_initial(self):
        initial = super().get_initial()
        initial['linked_folder'] = Folder.objects.first()

        return initial


class RelatedDocumentCreation(generic.AddingInstanceToEntityPopup):
    model = Document
    form_class = custom_forms.DOCUMENT_CREATION_CFORM
    permissions = [
        'documents',
        auth.build_creation_perm(Document),
        auth.build_link_perm(Document),
    ]
    title = _('New document for «{entity}»')

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)
        user.has_perm_to_link_or_die(entity)

    def get_form_class(self):
        form_cls = super().get_form_class()

        class RelatedDocumentCreationForm(form_cls):
            def __init__(this, entity, *args, **kwargs):
                super().__init__(*args, **kwargs)
                this.related_entity = entity
                this.folder_category = None
                this.root_folder = None

                del this.fields['linked_folder']

            def clean_user(this):
                return validate_linkable_model(
                    Document, this.user, owner=this.cleaned_data['user'],
                )

            def clean(this):
                cleaned_data = super().clean()

                if not this._errors:
                    this.folder_category = cat = FolderCategory.objects.filter(
                        uuid=constants.UUID_FOLDER_CAT_ENTITIES,
                    ).first()
                    if cat is None:
                        raise ValidationError(
                            f'Populate script has not been run (unknown folder category '
                            f'uuid={constants.UUID_FOLDER_CAT_ENTITIES}) ; '
                            f'please contact your administrator.'
                        )

                    this.root_folder = folder = Folder.objects.filter(
                        uuid=constants.UUID_FOLDER_RELATED2ENTITIES,
                    ).first()
                    if folder is None:
                        raise ValidationError(
                            f'Populate script has not been run '
                            f'(unknown folder uuid={constants.UUID_FOLDER_RELATED2ENTITIES}) ; '
                            f'please contact your administrator'
                        )

                return cleaned_data

            def _get_relations_to_create(this):
                instance = this.instance

                return super()._get_relations_to_create().append(
                    Relation(
                        subject_entity=this.related_entity.get_real_entity(),
                        type_id=constants.REL_SUB_RELATED_2_DOC,
                        object_entity=instance,
                        user=instance.user,
                    ),
                )

            def _get_folder(this):
                entity = this.related_entity.get_real_entity()
                get_or_create_folder = partial(
                    Folder.objects.get_or_create,
                    category=this.folder_category,
                    defaults={'user': this.cleaned_data['user']},
                )
                model_folder = get_or_create_folder(
                    title=str(entity.entity_type),
                    parent_folder=this.root_folder,
                )[0]

                return get_or_create_folder(
                    title=ellipsis(
                        f'{entity.id}_{entity}',
                        length=Folder._meta.get_field('title').max_length,
                    ),  # Meh
                    parent_folder=model_folder,
                )[0]

            @atomic
            def save(this, *args, **kwargs):
                this.instance.linked_folder = this._get_folder()

                return super().save(*args, **kwargs)

        return RelatedDocumentCreationForm


class DocumentDetail(generic.EntityDetail):
    model = Document
    template_name = 'documents/view_document.html'
    pk_url_kwarg = 'document_id'


class DocumentEdition(generic.EntityEdition):
    model = Document
    form_class = custom_forms.DOCUMENT_EDITION_CFORM
    pk_url_kwarg = 'document_id'


class DocumentsList(generic.EntitiesList):
    model = Document
    default_headerfilter_id = DEFAULT_HFILTER_DOCUMENT
