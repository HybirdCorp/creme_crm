# -*- coding: utf-8 -*-

from django.conf.urls import patterns


urlpatterns = patterns('creme.documents.views',
    (r'^$', 'portal.portal'),

    (r'^folders$',                        'folder.listview'),
    (r'^folder/add$',                     'folder.add'),
    (r'^folder/edit/(?P<folder_id>\d+)$', 'folder.edit'),
    (r'^folder/(?P<folder_id>\d+)$',      'folder.detailview'),

    (r'^getChildFolders/$',   'ajax.get_child_folders'),
    (r'^getChildDocuments/$', 'ajax.get_child_documents'),

    (r'^documents$',                                'document.listview'),
    (r'^document/add$',                             'document.add'),
    (r'^document/add_related/(?P<entity_id>\d+)',   'document.add_related'),
    (r'^document/edit/(?P<document_id>\d+)$',       'document.edit'),
    (r'^document/(?P<object_id>\d+)$',              'document.detailview'),

    (r'^quickforms/from_widget/document/csv/add/(?P<count>\d)$', 'quick_forms.add_csv_from_widget'),
)
