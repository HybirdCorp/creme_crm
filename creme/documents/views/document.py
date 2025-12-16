################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2026  Hybird
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
from os import path
from zipfile import ZipFile

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.transaction import atomic
from django.http import HttpResponseRedirect
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import documents
from creme.creme_core import auth
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms.validators import validate_linkable_model
from creme.creme_core.models import FileRef, Relation
from creme.creme_core.utils import ellipsis
from creme.creme_core.utils.file_handling import FileCreator
from creme.creme_core.utils.secure_filename import secure_filename
from creme.creme_core.utils.translation import smart_model_verbose_name
from creme.creme_core.views import generic

from .. import constants, custom_forms
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
    default_headerfilter_id = constants.DEFAULT_HFILTER_DOCUMENT


class BulkDownload(generic.base.CheckedView):
    permissions = 'documents'

    def get_ids(self, request):
        raw_ids = request.GET.getlist('id')

        if not raw_ids:
            raise ConflictError('The list of IDs is empty')

        try:
            cleaned_ids = {int(i) for i in raw_ids}
        except ValueError as e:
            raise ConflictError('Some IDs are invalid: {e}') from e

        return cleaned_ids

    def get(self, request, *args, **kwargs):
        ids = self.get_ids(request)
        user = request.user

        documents = EntityCredentials.filter(
            user=user, queryset=Document.objects.filter(id__in=ids),
        )

        if len(documents) != len(ids):
            raise PermissionDenied(gettext('Some documents are invalid or not viewable'))

        limit = settings.DOCUMENTS_BULK_DOWNLOAD_MAX_SIZE
        sizes_sum = sum(doc.file_size for doc in documents)
        if sizes_sum > limit:
            raise ConflictError(
                gettext(
                    'The total size of these files is {size} which is greater than '
                    'the allowed limit ({limit}).'
                ).format(
                    size=filesizeformat(sizes_sum),
                    limit=filesizeformat(limit),
                )
            )

        count = len(documents)
        # TODO: add date in the file name?
        basename = secure_filename(f'{Document._meta.verbose_name_plural}_X{count}.zip')
        final_path = FileCreator(
            dir_path=path.join(settings.MEDIA_ROOT, 'documents'),
            name=basename,
        ).create()

        # NB: we create the FileRef instance as soon as possible to get the
        #     smallest duration when a crash causes a file which have to be
        #     removed by hand (not cleaned by the Cleaner job).
        file_ref = FileRef.objects.create(
            user=user,
            filedata=f'documents/{path.basename(final_path)}',
            basename=basename,
            description=gettext('Bulk download of {count} {model}').format(
                count=count,
                model=smart_model_verbose_name(model=Document, count=count),
            ),
        )

        with ZipFile(final_path, 'w') as archive:
            for doc in documents:
                doc_path = doc.filedata.path
                archive.write(filename=doc_path, arcname=path.basename(doc_path))

        return HttpResponseRedirect(file_ref.get_download_absolute_url())
