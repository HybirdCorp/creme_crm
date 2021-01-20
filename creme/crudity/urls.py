# -*- coding: utf-8 -*-

from django.urls import re_path

from .views import actions, email, filesystem, history, infopath

urlpatterns = [
    re_path(
        r'^waiting_actions[/]?$',
        actions.Portal.as_view(),
        name='crudity__actions',
    ),
    re_path(
        r'^waiting_actions/refresh[/]?$',
        actions.ActionsRefreshing.as_view(),
        name='crudity__refresh_actions',
    ),
    re_path(
        r'^waiting_actions/delete[/]?$',
        actions.ActionsDeletion.as_view(),
        name='crudity__delete_actions',
    ),
    re_path(
        r'^waiting_actions/validate[/]?$',
        actions.ActionsValidation.as_view(),
        name='crudity__validate_actions',
    ),
    re_path(
        r'^waiting_actions/reload[/]?$',
        actions.ActionsBricksReloading.as_view(),
        name='crudity__reload_actions_bricks',
    ),

    re_path(
        r'^history[/]?$',
        history.History.as_view(),
        name='crudity__history',
    ),
    re_path(
        r'^history/reload[/]?$',
        history.HistoryBricksReloading.as_view(),
        name='crudity__reload_history_bricks',
    ),

    # TODO: only one URL which handles all templates ? (+ Class based)
    re_path(
        r'^infopath/create_form/(?P<subject>\w+)[/]?$',
        infopath.create_form,
        name='crudity__dl_infopath_form',
    ),
    re_path(
        r'^download_email_template/(?P<subject>\w+)[/]?$',
        email.download_email_template,
        name='crudity__dl_email_template',
    ),
    re_path(
        r'^download_ini_template/(?P<subject>\w+)[/]?$',
        filesystem.download_ini_template,
        name='crudity__dl_fs_ini_template',
    ),
]
