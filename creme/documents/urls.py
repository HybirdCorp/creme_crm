# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import document_model_is_custom, folder_model_is_custom
from .views import portal, ajax


urlpatterns = [
    url(r'^$', portal.portal),

    url(r'^getChildFolders/$',   ajax.get_child_folders),
    url(r'^getChildDocuments/$', ajax.get_child_documents),
]

if not folder_model_is_custom():
    from .views import folder

    urlpatterns += [
        url(r'^folders$',                             folder.listview,   name='documents__list_folders'),
        url(r'^folder/add$',                          folder.add,        name='documents__create_folder'),
        url(r'^folder/(?P<folder_id>\d+)/add/child$', folder.add_child,  name='documents__create_child_folder'),
        url(r'^folder/edit/(?P<folder_id>\d+)$',      folder.edit,       name='documents__edit_folder'),
        url(r'^folder/(?P<folder_id>\d+)$',           folder.detailview, name='documents__view_folder'),
    ]

if not document_model_is_custom():
    from .views import document, quick_forms

    urlpatterns += [
        url(r'^documents$',                              document.listview,    name='documents__list_documents'),
        url(r'^document/add$',                           document.add,         name='documents__create_document'),
        url(r'^document/add_related/(?P<entity_id>\d+)', document.add_related, name='documents__create_related_document'),
        url(r'^document/edit/(?P<document_id>\d+)$',     document.edit,        name='documents__edit_document'),
        url(r'^document/(?P<object_id>\d+)$',            document.detailview,  name='documents__view_document'),

        url(r'^quickforms/from_widget/document/csv/add/(?P<count>\d)$',
            quick_forms.add_csv_from_widget, name='documents__create_document_from_widget',
           ),
        url(r'^quickforms/image$',
            quick_forms.add_image, name='documents__create_image_popup',
           ),
    ]
