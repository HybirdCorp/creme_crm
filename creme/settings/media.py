# Django mediagenerator settings for creme project.

# TODO: create a static/css/creme-minimal.css for login/logout ??
CREME_CORE_CSS = [
    # Name
    'main.css',

    # Content
    'creme_core/css/jquery-css/creme-theme/jquery-ui-1.11.4.custom.css',
    'creme_core/css/jqplot-1.0.8/jquery.jqplot.css',
    'creme_core/css/jquery.gccolor.1.0.3/gccolor.css',
    'creme_core/css/chosen/chosen-0.9.15-unchosen.css',

    'creme_core/css/creme.css',
    'creme_core/css/creme-ui.css',

    'creme_core/css/header_menu.css',
    'creme_core/css/forms.css',
    'creme_core/css/blocks.css',
    'creme_core/css/bricks.css',
    'creme_core/css/home.css',
    'creme_core/css/my_page.css',
    'creme_core/css/list_view.css',
    'creme_core/css/detail_view.css',
    'creme_core/css/search_results.css',
    'creme_core/css/popover.css',

    'creme_config/css/creme_config.css',
]

CREME_OPT_CSS = [  # APPS
    ('creme.persons',          'persons/css/persons.css'),

    ('creme.activities',       'activities/css/activities.css'),
    ('creme.activities',       'activities/css/fullcalendar-3.10.0.css'),

    ('creme.billing',          'billing/css/billing.css'),
    ('creme.opportunities',    'opportunities/css/opportunities.css'),
    ('creme.commercial',       'commercial/css/commercial.css'),
    ('creme.crudity',          'crudity/css/crudity.css'),
    ('creme.emails',           'emails/css/emails.css'),
    ('creme.geolocation',      'geolocation/css/geolocation.css'),
    ('creme.polls',            'polls/css/polls.css'),
    ('creme.products',         'products/css/products.css'),
    ('creme.projects',         'projects/css/projects.css'),
    ('creme.reports',          'reports/css/reports.css'),
    ('creme.tickets',          'tickets/css/tickets.css'),
    ('creme.mobile',           'mobile/css/mobile.css'),
    ('creme.cti',              'cti/css/cti.css'),
]

CREME_I18N_JS = [
    'l10n.js',

    {'filter': 'mediagenerator.filters.i18n.I18N'},  # To build the i18n catalog statically.
    # 'creme_core/js/datejs/date-en-US.js', # TODO improve
    # 'creme_core/js/datejs/date-fr-FR.js',
]

CREME_LIB_JS = [
    'lib.js',

    # To get the media_url() function in JS.
    {'filter': 'mediagenerator.filters.media_url.MediaURL'},

    'creme_core/js/media.js',
    'creme_core/js/jquery/jquery-1.11.2.js',
    'creme_core/js/jquery/jquery-migrate-1.2.1.js',
    'creme_core/js/jquery/ui/jquery-ui-1.11.4.custom.js',
    'creme_core/js/jquery/ui/jquery-ui-locale.js',
    'creme_core/js/jquery/extensions/jquery.browser.js',
    'creme_core/js/jquery/extensions/jquery.uuid-2.0.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/excanvas.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/jquery.jqplot.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.enhancedLegendRenderer.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.canvasTextRenderer.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.categoryAxisRenderer.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.canvasTextRenderer.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.canvasAxisLabelRenderer.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.canvasAxisTickRenderer.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.pieRenderer.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.donutRenderer.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.barRenderer.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.pointLabels.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.highlighter.js',
    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.cursor.js',
    'creme_core/js/jquery/extensions/cookie.js',
    'creme_core/js/jquery/extensions/gccolor-1.0.3.js',
    'creme_core/js/jquery/extensions/json-2.2.js',
    'creme_core/js/jquery/extensions/highlight.js',
    'creme_core/js/jquery/extensions/utils.js',
    'creme_core/js/jquery/extensions/wait.js',
    'creme_core/js/jquery/extensions/jquery.dragtable.js',
    'creme_core/js/jquery/extensions/jquery.form-3.51.js',
    'creme_core/js/jquery/extensions/jquery.tinymce.js',
    'creme_core/js/jquery/extensions/jquery.debounce.js',
    'creme_core/js/jquery/extensions/chosen.jquery-0.9.15-unchosen.js',
    'creme_core/js/jquery/extensions/jquery.bind-first.js',
    'creme_core/js/jquery/extensions/jquery.floatthead-1.3.1._.js',
    'creme_core/js/jquery/extensions/jquery.floatthead-1.3.1.js',
    'creme_core/js/lib/momentjs/moment-2.24.0.js',
    'creme_core/js/lib/momentjs/locale/en-us.js',
    'creme_core/js/lib/momentjs/locale/fr-fr.js',
]

CREME_CORE_JS = [
    # Name
    'main.js',

    # Content
    'creme_core/js/lib/fallbacks/object-0.1.js',
    'creme_core/js/lib/fallbacks/array-0.9.js',
    'creme_core/js/lib/fallbacks/string-0.1.js',
    'creme_core/js/lib/fallbacks/console.js',
    'creme_core/js/lib/fallbacks/event-0.1.js',
    'creme_core/js/lib/fallbacks/htmldocument-0.1.js',
    'creme_core/js/lib/generators-0.1.js',
    'creme_core/js/lib/color.js',
    'creme_core/js/lib/assert.js',
    'creme_core/js/lib/faker.js',
    'creme_core/js/lib/browser.js',

    'creme_core/js/creme.js',
    'creme_core/js/color.js',
    'creme_core/js/utils.js',
    'creme_core/js/forms.js',
    'creme_core/js/ajax.js',

    'creme_core/js/widgets/base.js',

    'creme_core/js/widgets/component/component.js',
    'creme_core/js/widgets/component/factory.js',
    'creme_core/js/widgets/component/events.js',
    'creme_core/js/widgets/component/action.js',
    'creme_core/js/widgets/component/action-registry.js',
    'creme_core/js/widgets/component/action-link.js',
    'creme_core/js/widgets/component/chosen.js',

    'creme_core/js/widgets/utils/template.js',
    'creme_core/js/widgets/utils/lambda.js',
    'creme_core/js/widgets/utils/converter.js',
    'creme_core/js/widgets/utils/json.js',
    'creme_core/js/widgets/utils/compare.js',
    'creme_core/js/widgets/utils/history.js',
    'creme_core/js/widgets/utils/plugin.js',

    'creme_core/js/widgets/ajax/url.js',
    'creme_core/js/widgets/ajax/backend.js',
    'creme_core/js/widgets/ajax/mockbackend.js',
    'creme_core/js/widgets/ajax/cachebackend.js',
    'creme_core/js/widgets/ajax/query.js',

    'creme_core/js/widgets/layout/layout.js',
    'creme_core/js/widgets/layout/sortlayout.js',
    'creme_core/js/widgets/layout/columnlayout.js',
    'creme_core/js/widgets/layout/autosize.js',

    'creme_core/js/widgets/model/collection.js',
    'creme_core/js/widgets/model/array.js',
    'creme_core/js/widgets/model/renderer.js',
    'creme_core/js/widgets/model/query.js',
    'creme_core/js/widgets/model/controller.js',
    'creme_core/js/widgets/model/choice.js',

    'creme_core/js/widgets/dialog/dialog.js',
    'creme_core/js/widgets/dialog/overlay.js',
    'creme_core/js/widgets/dialog/frame.js',
    'creme_core/js/widgets/dialog/confirm.js',
    'creme_core/js/widgets/dialog/form.js',
    'creme_core/js/widgets/dialog/select.js',
    'creme_core/js/widgets/dialog/glasspane.js',
    'creme_core/js/widgets/dialog/popover.js',

    'creme_core/js/widgets/list/pager.js',

    'creme_core/js/widgets/frame.js',
    'creme_core/js/widgets/toggle.js',
    'creme_core/js/widgets/pluginlauncher.js',
    'creme_core/js/widgets/dinput.js',
    'creme_core/js/widgets/dselect.js',
    'creme_core/js/widgets/checklistselect.js',
    'creme_core/js/widgets/datetime.js',
    'creme_core/js/widgets/daterange.js',
    'creme_core/js/widgets/daterangeselector.js',
    'creme_core/js/widgets/chainedselect.js',
    'creme_core/js/widgets/selectorlist.js',
    'creme_core/js/widgets/entityselector.js',
    'creme_core/js/widgets/pselect.js',
    'creme_core/js/widgets/actionlist.js',
    'creme_core/js/widgets/plotdata.js',
    'creme_core/js/widgets/plot.js',
    'creme_core/js/widgets/plotselector.js',
    'creme_core/js/widgets/scrollactivator.js',
    'creme_core/js/widgets/container.js',

    'creme_core/js/menu.js',
    'creme_core/js/search.js',
    'creme_core/js/bricks.js',
    'creme_core/js/bricks-action.js',

    'creme_core/js/list_view.core.js',
    'creme_core/js/lv_widget.js',
    'creme_core/js/detailview.js',

    'creme_core/js/entity_cell.js',
    'creme_core/js/export.js',
    'creme_core/js/merge.js',
    'creme_core/js/relations.js',
    'creme_core/js/jobs.js',
]

CREME_OPTLIB_JS = [
    ('creme.activities', 'activities/js/jquery/extensions/fullcalendar-3.10.0.js'),
]

CREME_OPT_JS = [  # OPTIONAL APPS
    ('creme.persons',       'persons/js/persons.js'),

    ('creme.activities',    'activities/js/activities.js'),
    ('creme.activities',    'activities/js/activities-calendar.js'),

    ('creme.billing',       'billing/js/billing.js'),
    ('creme.billing',       'billing/js/billing-actions.js'),

    ('creme.opportunities', 'opportunities/js/opportunities.js'),

    ('creme.commercial',    'commercial/js/commercial.js'),

    ('creme.projects',      'projects/js/projects.js'),

    ('creme.reports',       'reports/js/reports.js'),
    ('creme.reports',       'reports/js/reports-actions.js'),

    ('creme.crudity',       'crudity/js/crudity.js'),

    ('creme.emails',        'emails/js/emails.js'),

    ('creme.cti',           'cti/js/cti.js'),

    ('creme.events',        'events/js/events.js'),

    ('creme.geolocation',   'geolocation/js/geolocation.js'),
    ('creme.geolocation',   'geolocation/js/geolocation-google.js'),
    ('creme.geolocation',   'geolocation/js/brick.js'),
]

TEST_CREME_LIB_JS = [
    # Name
    'testlib.js',

    # Content
    'creme_core/js/tests/qunit/qunit-1.18.0.js',
    'creme_core/js/tests/qunit/qunit-mixin.js',
    'creme_core/js/tests/component/qunit-event-mixin.js',
    'creme_core/js/tests/ajax/qunit-ajax-mixin.js',
    'creme_core/js/tests/dialog/qunit-dialog-mixin.js',
    'creme_core/js/tests/widgets/qunit-widget-mixin.js',
    'creme_core/js/tests/widgets/qunit-plot-mixin.js',
    'creme_core/js/tests/list/qunit-listview-mixin.js',
    'creme_core/js/tests/brick/qunit-brick-mixin.js',
    'creme_core/js/tests/views/qunit-detailview-mixin.js',
]

TEST_CREME_CORE_JS = [
    # Name
    'testcore.js',

    # Content
    'creme_core/js/tests/component/component.js',
    'creme_core/js/tests/component/events.js',
    'creme_core/js/tests/component/action.js',
    'creme_core/js/tests/component/actionregistry.js',
    'creme_core/js/tests/component/actionlink.js',
    'creme_core/js/tests/component/chosen.js',

    'creme_core/js/tests/utils/template.js',
    'creme_core/js/tests/utils/lambda.js',
    'creme_core/js/tests/utils/converter.js',
    'creme_core/js/tests/utils/utils.js',
    'creme_core/js/tests/utils/plugin.js',

    'creme_core/js/tests/ajax/mockajax.js',
    'creme_core/js/tests/ajax/cacheajax.js',
    'creme_core/js/tests/ajax/query.js',
    'creme_core/js/tests/ajax/localize.js',
    'creme_core/js/tests/ajax/utils.js',

    'creme_core/js/tests/model/collection.js',
    'creme_core/js/tests/model/renderer-list.js',
    'creme_core/js/tests/model/renderer-choice.js',
    'creme_core/js/tests/model/renderer-checklist.js',
    'creme_core/js/tests/model/query.js',
    'creme_core/js/tests/model/controller.js',

    'creme_core/js/tests/dialog/frame.js',
    'creme_core/js/tests/dialog/overlay.js',
    'creme_core/js/tests/dialog/dialog.js',
    'creme_core/js/tests/dialog/dialog-form.js',
    'creme_core/js/tests/dialog/popover.js',
    'creme_core/js/tests/dialog/glasspane.js',

    'creme_core/js/tests/fallbacks.js',
    'creme_core/js/tests/generators.js',
    'creme_core/js/tests/color.js',
    'creme_core/js/tests/assert.js',
    'creme_core/js/tests/faker.js',
    'creme_core/js/tests/browser.js',

    'creme_core/js/tests/widgets/base.js',
    'creme_core/js/tests/widgets/widget.js',
    'creme_core/js/tests/widgets/plot.js',
    'creme_core/js/tests/widgets/frame.js',
    'creme_core/js/tests/widgets/toggle.js',
    'creme_core/js/tests/widgets/dselect.js',
    'creme_core/js/tests/widgets/dinput.js',
    'creme_core/js/tests/widgets/pselect.js',
    'creme_core/js/tests/widgets/entityselector.js',
    'creme_core/js/tests/widgets/chainedselect.js',
    'creme_core/js/tests/widgets/checklistselect.js',
    'creme_core/js/tests/widgets/selectorlist.js',
    'creme_core/js/tests/widgets/actionlist.js',
    'creme_core/js/tests/widgets/plotselector.js',
    'creme_core/js/tests/widgets/entitycells.js',

    'creme_core/js/tests/form/forms.js',

    'creme_core/js/tests/list/list-pager.js',
    'creme_core/js/tests/list/listview-actions.js',
    'creme_core/js/tests/list/listview-header.js',
    'creme_core/js/tests/list/listview-core.js',
    'creme_core/js/tests/list/listview-dialog.js',

    'creme_core/js/tests/brick/brick.js',
    'creme_core/js/tests/brick/brick-actions.js',
    'creme_core/js/tests/brick/brick-menu.js',
    'creme_core/js/tests/brick/brick-table.js',
    'creme_core/js/tests/brick/dependencies.js',

    'creme_core/js/tests/views/detailview-actions.js',
    'creme_core/js/tests/views/hatmenubar.js',
    'creme_core/js/tests/views/menu.js',
    'creme_core/js/tests/views/search.js',
    'creme_core/js/tests/views/utils.js',
]

TEST_CREME_OPT_JS = [
    # ('creme.my_app',       'my_app/js/tests/my_app.js'),
    ('creme.activities',    'activities/js/tests/activities-listview.js'),
    ('creme.activities',    'activities/js/tests/activities-calendar.js'),
    ('creme.billing',       'billing/js/tests/billing.js'),
    ('creme.billing',       'billing/js/tests/billing-actions.js'),
    ('creme.billing',       'billing/js/tests/billing-listview.js'),
    ('creme.commercial',    'commercial/js/tests/commercial-score.js'),
    ('creme.crudity',       'crudity/js/tests/crudity-actions.js'),
    ('creme.cti',           'cti/js/tests/cti-actions.js'),
    ('creme.emails',        'emails/js/tests/emails-actions.js'),
    ('creme.emails',        'emails/js/tests/emails-listview.js'),
    ('creme.events',        'events/js/tests/events-listview.js'),
    ('creme.geolocation',   'geolocation/js/tests/qunit-geolocation-mixin.js'),
    ('creme.geolocation',   'geolocation/js/tests/geolocation.js'),
    ('creme.geolocation',   'geolocation/js/tests/geolocation-google.js'),
    ('creme.geolocation',   'geolocation/js/tests/persons-brick.js'),
    ('creme.geolocation',   'geolocation/js/tests/addresses-brick.js'),
    ('creme.geolocation',   'geolocation/js/tests/persons-neighborhood-brick.js'),
    ('creme.opportunities', 'opportunities/js/tests/opportunities.js'),
    ('creme.persons',       'persons/js/tests/persons.js'),
    ('creme.persons',       'persons/js/tests/persons-actions.js'),
    ('creme.projects',      'projects/js/tests/projects.js'),
    ('creme.reports',       'reports/js/tests/reports-actions.js'),
    ('creme.reports',       'reports/js/tests/reports-listview.js'),
    ('creme.reports',       'reports/js/tests/reports-chart.js'),
    ('creme.reports',       'reports/js/tests/reports-filter.js'),
]

# Optional js/css bundles for extending projects.
# Beware to clashes with existing bundles ('main.js', 'l10n.js').
CREME_OPT_MEDIA_BUNDLES = []
