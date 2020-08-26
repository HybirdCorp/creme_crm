# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme import documents
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.documents.forms.document import BaseDocumentCustomForm
from creme.documents.forms.folder import BaseFolderCustomForm

Folder = documents.get_folder_model()
Document = documents.get_document_model()


FOLDER_CREATION_CFORM = CustomFormDescriptor(
    id='documents-folder_creation',
    model=Folder,
    verbose_name=_('Creation form for folder'),
    base_form_class=BaseFolderCustomForm,  # NB: not necessary indeed
)
FOLDER_EDITION_CFORM = CustomFormDescriptor(
    id='documents-folder_edition',
    model=Folder,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for folder'),
    base_form_class=BaseFolderCustomForm,
)
DOCUMENT_CREATION_CFORM = CustomFormDescriptor(
    id='documents-document_creation',
    model=Document,
    verbose_name=_('Creation form for document'),
    base_form_class=BaseDocumentCustomForm,
)
DOCUMENT_EDITION_CFORM = CustomFormDescriptor(
    id='documents-document_edition',
    model=Document,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for document'),
    base_form_class=BaseDocumentCustomForm,  # NB: not necessary indeed
    excluded_fields=('filedata',),
)

del Folder
del Document
