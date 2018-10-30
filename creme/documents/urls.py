# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme import documents
# from .views import portal, ajax
from .views import folder, document, quick_forms


urlpatterns = [
    # url(r'^$', portal.portal, name='documents__portal'),

    # url(r'^getChildFolders[/]?$',   ajax.get_child_folders,   name='documents__child_folders'),
    # url(r'^getChildDocuments[/]?$', ajax.get_child_documents, name='documents__child_documents'),
]

# if not documents.folder_model_is_custom():
#     urlpatterns += [
#         url(r'^folders[/]?$',                             folder.listview,   name='documents__list_folders'),
#         url(r'^folder/add[/]?$',                          folder.add,        name='documents__create_folder'),
#         url(r'^folder/(?P<folder_id>\d+)/add/child[/]?$', folder.add_child,  name='documents__create_child_folder'),
#         url(r'^folder/edit/(?P<folder_id>\d+)[/]?$',      folder.edit,       name='documents__edit_folder'),
#         url(r'^folder/(?P<folder_id>\d+)[/]?$',           folder.detailview, name='documents__view_folder'),
#     ]
urlpatterns += swap_manager.add_group(
    documents.folder_model_is_custom,
    Swappable(url(r'^folders[/]?$',                             folder.listview,                      name='documents__list_folders')),
    Swappable(url(r'^folder/add[/]?$',                          folder.FolderCreation.as_view(),      name='documents__create_folder')),
    Swappable(url(r'^folder/(?P<folder_id>\d+)/add/child[/]?$', folder.ChildFolderCreation.as_view(), name='documents__create_child_folder'), check_args=Swappable.INT_ID),
    Swappable(url(r'^folder/edit/(?P<folder_id>\d+)[/]?$',      folder.FolderEdition.as_view(),       name='documents__edit_folder'),         check_args=Swappable.INT_ID),
    Swappable(url(r'^folder/(?P<folder_id>\d+)[/]?$',           folder.FolderDetail.as_view(),        name='documents__view_folder'),         check_args=Swappable.INT_ID),
    app_name='documents',
).kept_patterns()

# if not documents.document_model_is_custom():
#     urlpatterns += [
#         url(r'^documents[/]?$',                              document.listview,    name='documents__list_documents'),
#         url(r'^document/add[/]?$',                           document.add,         name='documents__create_document'),
#         url(r'^document/add_related/(?P<entity_id>\d+)[/]?', document.add_related, name='documents__create_related_document'),
#         url(r'^document/edit/(?P<document_id>\d+)[/]?$',     document.edit,        name='documents__edit_document'),
#         url(r'^document/(?P<object_id>\d+)[/]?$',            document.detailview,  name='documents__view_document'),
#
#         url(r'^quickforms/from_widget/document/csv/add/(?P<count>\d)*[/]?$', quick_forms.add_csv_from_widget, name='documents__create_document_from_widget'),
#         url(r'^quickforms/image[/]?$',                                       quick_forms.add_image,           name='documents__create_image_popup'),
#     ]
urlpatterns += swap_manager.add_group(
    documents.document_model_is_custom,
    Swappable(url(r'^documents[/]?$',                              document.listview,                          name='documents__list_documents')),
    Swappable(url(r'^document/add[/]?$',                           document.DocumentCreation.as_view(),        name='documents__create_document')),
    Swappable(url(r'^document/add_related/(?P<entity_id>\d+)[/]?', document.RelatedDocumentCreation.as_view(), name='documents__create_related_document'), check_args=Swappable.INT_ID),
    Swappable(url(r'^document/edit/(?P<document_id>\d+)[/]?$',     document.DocumentEdition.as_view(),         name='documents__edit_document'),           check_args=Swappable.INT_ID),
    Swappable(url(r'^document/(?P<document_id>\d+)[/]?$',          document.DocumentDetail.as_view(),          name='documents__view_document'),           check_args=Swappable.INT_ID),

    Swappable(url(r'^quickforms/from_widget/document/csv/add[/]?$', quick_forms.QuickDocumentCreation.as_view(), name='documents__create_document_from_widget')),
    Swappable(url(r'^quickforms/image[/]?$',                        quick_forms.QuickImageCreation.as_view(),    name='documents__create_image_popup')),
    app_name='documents',
).kept_patterns()
