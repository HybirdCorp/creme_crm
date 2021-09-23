from django.urls import include, re_path

from .views import actions, config, history  # email filesystem

urlpatterns = [
    re_path(
        r'^waiting_actions[/]?$',
        actions.Portal.as_view(),
        name='crudity__actions',
    ),
    re_path(
        r'^waiting_actions/',
        include([
            # re_path(
            #     r'^refresh[/]?$',
            #     actions.ActionsRefreshing.as_view(),
            #     name='crudity__refresh_actions',
            # ),
            # re_path(
            #     r'^delete[/]?$',
            #     actions.ActionsDeletion.as_view(),
            #     name='crudity__delete_actions',
            # ),
            # re_path(
            #     r'^validate[/]?$',
            #     actions.ActionsValidation.as_view(),
            #     name='crudity__validate_actions',
            # ),
            # re_path(
            #     r'^reload[/]?$',
            #     actions.ActionsBricksReloading.as_view(),
            #     name='crudity__reload_actions_bricks',
            # ),
        ]),
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

    re_path(
        r'^fetchers/',
        include([
            re_path(
                r'^add[/]?$',
                config.FetcherConfigItemCreationWizard.as_view(),
                name='crudity__create_fetcher_item',
            ),
        ]),
    ),

    re_path(
        r'^machines/',
        include([
            re_path(
                r'^add[/]?$',
                config.MachineConfigItemCreationWizard.as_view(),
                name='crudity__create_machine_item',
            ),
        ]),
    ),

    # TODO: only one URL which handles all templates ? (+ Class based)
    # re_path(
    #     r'^download_email_template/(?P<subject>\w+)[/]?$',
    #     email.download_email_template,
    #     name='crudity__dl_email_template',
    # ),
    # re_path(
    #     r'^download_ini_template/(?P<subject>\w+)[/]?$',
    #     filesystem.download_ini_template,
    #     name='crudity__dl_fs_ini_template',
    # ),
]
