/* globals QUnitWidgetMixin */
(function($) {

QUnit.module("creme.widget.entityselector.js", new QUnitMixin(QUnitAjaxMixin,
                                                              QUnitEventMixin,
                                                              QUnitDialogMixin,
                                                              QUnitWidgetMixin,
                                                              QUnitListViewMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.widget.entityselector.js'});
    },

    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        var singleListViewHtml = this.createListViewHtml(this.defaultListViewHtmlOptions({
            multiple: false,
            reloadUrl: 'mock/listview/single'
        }));

        var multiListViewHtml = this.createListViewHtml(this.defaultListViewHtmlOptions({
            multiple: true,
            reloadUrl: 'mock/listview/multiple'
        }));

        this.setMockBackendGET({
            'mock/listview/single': backend.response(200, singleListViewHtml),
            'mock/listview/multiple': backend.response(200, multiListViewHtml),
            'mock/label/1': backend.responseJSON(200, [['John Doe']]),
            'mock/label/2': backend.responseJSON(200, [['Bean Bandit']]),
            'mock/label/3': backend.responseJSON(200, [['Jean Bon']]),
            'mock/label/missing': backend.responseJSON(200, []),
            'mock/label/empty': backend.responseJSON(200, [['']]),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/error': backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));
    }
}));

QUnit.test('creme.widget.EntitySelector.create (empty, auto)', function(assert) {
    var element = this.createEntitySelectorTag();

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("select a mock", $('button', element).text());
    equal("", widget.val());
    equal("", widget.options().popupURL);
    equal("mock/label/${id}", widget.options().labelURL);
    equal("select a mock", widget.options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (not empty, auto)', function(assert) {
    var element = this.createEntitySelectorTag();
    creme.widget.input(element).val('1');

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("John Doe", $('button', element).text());
    equal($('button', element).is('[disabled]'), false);
    equal(widget.delegate._enabled, true);

    equal("1", widget.val());
    equal("", widget.options().popupURL);
    equal("mock/label/${id}", widget.options().labelURL);
    equal("select a mock", widget.options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (auto, [disabled] attribute)', function(assert) {
    var element = this.createEntitySelectorTag({disabled: ''});
    creme.widget.input(element).val('1');

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-ready'), true);

    equal($('button', element).is('[disabled]'), true);
    equal("1", widget.val());
    equal(widget.delegate._enabled, false);
});

QUnit.test('creme.widget.EntitySelector.create (auto, {disabled: true} option)', function(assert) {
    var element = this.createEntitySelectorTag();
    creme.widget.input(element).val('2');

    equal(element.is('[disabled]'), false);

    var widget = creme.widget.create(element, {disabled: true});

    equal(element.hasClass('widget-ready'), true);
    equal(element.is('[disabled]'), true);
    equal(widget.delegate._enabled, false);

    equal($('button', element).is('[disabled]'), true);
    equal("2", widget.val());
});

QUnit.test('creme.widget.EntitySelector.create (empty, popup url, auto)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/label'});

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("select a mock", $('button', element).text());
    equal("", widget.val());
    equal("mock/label", widget.options().popupURL);
    equal("mock/label/${id}", widget.options().labelURL);
    equal("select a mock", widget.options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (empty, invalid label url, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/unknown'});

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("select a mock", $('button', element).text());
    equal("", widget.val());
    equal("", widget.options().popupURL);
    equal("mock/label/unknown", widget.options().labelURL);
    equal("select a mock", widget.options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (not empty, invalid label url, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/unknown'});
    creme.widget.input(element).val('1');

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('1'));
    equal("1", widget.val());
    equal("", widget.options().popupURL);
    equal("mock/label/unknown", widget.options().labelURL);
    equal("select a mock", widget.options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (not empty, empty label data, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/empty'});
    creme.widget.input(element).val('1');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('1'));
});

QUnit.test('creme.widget.EntitySelector.create (not empty, missing label data, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/missing'});
    creme.widget.input(element).val('1');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('1'));
});

QUnit.test('creme.widget.EntitySelector.val (required)', function(assert) {
    var element = this.createEntitySelectorTag();

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    var input = element.find('input');
    var button = element.find('button');

    equal("select a mock", button.text());
    equal("", widget.val());
    equal("", input.val());
    equal(false, input.is(':invalid'));
    equal(false, button.is('.is-field-invalid'));

    // not required
    creme.forms.validateHtml5Field(input);
    equal(false, input.is(':required'));
    equal(false, input.is(':invalid'));
    equal(false, button.is('.is-field-invalid'));

    // required
    input.attr('required', '');
    creme.forms.validateHtml5Field(input);
    equal(true, input.is(':required'));
    equal(true, input.is(':invalid'));
    equal(true, button.is('.is-field-invalid'));

    widget.val('2');

    creme.forms.validateHtml5Field(input);
    equal("Bean Bandit", button.text());
    equal("2", widget.val());
    equal("2", input.val());
    equal(false, input.is(':invalid'));
    equal(false, button.is('.is-field-invalid'));
});

QUnit.test('creme.widget.EntitySelector.val', function(assert) {
    var element = this.createEntitySelectorTag();

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("select a mock", $('button', element).text());
    equal("", widget.val());

    widget.val('2');
    equal("Bean Bandit", $('button', element).text());
    equal("2", widget.val());

    widget.val('1');
    equal("John Doe", $('button', element).text());
    equal("1", widget.val());

    widget.val('unknown');
    equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('unknown'));
    equal("unknown", widget.val());
});

QUnit.test('creme.widget.EntitySelector.update', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);

    equal("select a mock", $('button', element).text());
    equal("", widget.val());

    widget.update({value: '2'});

    equal("Bean Bandit", $('button', element).text());
    equal("2", widget.val());
});

QUnit.test('creme.widget.EntitySelector.multiple (setter)', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);

    equal(creme.widget.EntitySelectorMode.SINGLE, widget.delegate._popupURL.parameters().selection);
    equal(widget.isMultiple(), false);

    widget.isMultiple(true);

    equal(creme.widget.EntitySelectorMode.MULTIPLE, widget.delegate._popupURL.parameters().selection);
    equal(widget.isMultiple(), true);
});

QUnit.test('creme.widget.EntitySelector.multiple (constructor)', function(assert) {
    var element = this.createEntitySelectorTag({popupSelection: creme.widget.EntitySelectorMode.MULTIPLE});
    var widget = creme.widget.create(element);

    equal(creme.widget.EntitySelectorMode.MULTIPLE, widget.options().popupSelection);
    equal(creme.widget.EntitySelectorMode.MULTIPLE, widget.delegate._popupURL.parameters().selection);
    equal(widget.isMultiple(), true);
});

QUnit.test('creme.widget.EntitySelector.qfilter (setter)', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);

    equal("", widget.delegate._popupURL.parameters().qfilter);

    widget.qfilter('{"id": 12}');

    equal('{"id": 12}', widget.delegate._popupURL.parameters().qfilter);
});

QUnit.test('creme.widget.EntitySelector.reload (url)', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);
    deepEqual([], widget.dependencies());


    widget.val('2');
    equal("Bean Bandit", $('button', element).text());
    equal("2", widget.val());
    equal("", widget.popupURL());

    widget.reload('mock/listview');
    equal("select a mock", $('button', element).text());
    equal("", widget.val());
    equal("mock/listview", widget.popupURL());
});

QUnit.test('creme.widget.EntitySelector.reload (template url, multiple)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});

    var widget = creme.widget.create(element);
    deepEqual(['selection'], widget.dependencies());

    equal("mock/listview/single", widget.popupURL());

    widget.isMultiple(true);
    equal("mock/listview/multiple", widget.popupURL());

    widget.reload({selection: 2});
    equal("mock/listview/2", widget.popupURL());
});

QUnit.test('creme.widget.EntitySelector.reload (template url, multiple, qfilter)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}?q_filter=${qfilter}'});

    var widget = creme.widget.create(element);
    deepEqual(['selection', 'qfilter'], widget.dependencies());

    equal("mock/listview/single?q_filter=", widget.popupURL());

    widget.reload({selection: creme.widget.EntitySelectorMode.MULTIPLE});
    equal("mock/listview/multiple?q_filter=", widget.popupURL());

    widget.reload({qfilter: JSON.stringify({"~pk__in": [1, 2]})});
    equal("mock/listview/multiple?q_filter=" + JSON.stringify({"~pk__in": [1, 2]}), widget.popupURL());

    widget.reload('mock/listview/${ctype}/${selection}?q_filter=${qfilter}');
    deepEqual(['ctype', 'selection', 'qfilter'], widget.dependencies());
    equal("mock/listview/${ctype}/multiple?q_filter=" + JSON.stringify({"~pk__in": [1, 2]}), widget.popupURL());
});

QUnit.test('creme.widget.EntitySelector.reset', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);
    deepEqual([], widget.dependencies());

    widget.val('2');
    equal("Bean Bandit", $('button', element).text());
    equal("2", widget.val());
    equal("", widget.popupURL());

    widget.reset();

    equal("select a mock", $('button', element).text());
    equal("", widget.val());
    equal("", widget.popupURL());
});

QUnit.test('creme.widget.EntitySelector.select (single)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});

    var widget = creme.widget.create(element);

    deepEqual(['selection'], widget.dependencies());
    equal("mock/listview/single", widget.popupURL());

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    this.assertClosedDialog();
    deepEqual([], this.mockBackendUrlCalls('mock/listview/single'));
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    $('button', element).trigger('click');

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/single'));
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1']);
    this.validateListViewSelectionDialog(dialog);

    equal("John Doe", $('button', element).text());
    equal('1', widget.val());
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([['change']], this.mockListenerJQueryCalls('change'));
});

QUnit.test('creme.widget.EntitySelector.select (single, filtered)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});

    var widget = creme.widget.create(element);

    deepEqual(['selection'], widget.dependencies());
    equal("mock/listview/single", widget.popupURL());

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    this.assertClosedDialog();
    deepEqual([], this.mockBackendUrlCalls('mock/listview/single'));
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    $('button', element).trigger('click');

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/single'));
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1']);
    this.validateListViewSelectionDialog(dialog);

    equal("John Doe", $('button', element).text());
    equal('1', widget.val());
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([['change']], this.mockListenerJQueryCalls('change'));
});

QUnit.test('creme.widget.EntitySelector.select (multiple)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});
    var widget = creme.widget.create(element);
    widget.isMultiple(true);

    equal("mock/listview/multiple", widget.popupURL());
    this.assertClosedDialog();

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    deepEqual([], this.mockBackendUrlCalls('mock/listview/multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    $('button', element).trigger('click');

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    deepEqual([
        ['GET', {selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1', '3']);
    this.validateListViewSelectionDialog(dialog);

    equal("John Doe", $('button', element).text());
    equal('1', widget.val());

    deepEqual([['change-multiple', [['1', '3']]]], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([['change']], this.mockListenerJQueryCalls('change'));
});

QUnit.test('creme.widget.EntitySelector.select (cancel)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});
    var widget = creme.widget.create(element);

    deepEqual(['selection'], widget.dependencies());
    equal("mock/listview/single", widget.popupURL());

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    this.assertClosedDialog();
    deepEqual([], this.mockBackendUrlCalls('mock/listview/single'));
    deepEqual([], this.mockListenerCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    $('button', element).trigger('click');

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/single'));
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1']);
    this.closeDialog();

    this.assertClosedDialog();

    equal("select a mock", $('button', element).text());
    equal('', widget.val());

    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));
});

QUnit.test('creme.widget.EntitySelector.select (action)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});
    var widget = creme.widget.create(element);

    deepEqual(['selection'], widget.dependencies());
    equal("mock/listview/single", widget.popupURL());

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    this.assertClosedDialog();
    deepEqual([], this.mockBackendUrlCalls('mock/listview/single'));
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    element.trigger('action', ['select']);

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/single'));
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1']);
    this.validateListViewSelectionDialog(dialog);

    equal("John Doe", $('button', element).text());
    equal('1', widget.val());
    deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    deepEqual([['change']], this.mockListenerJQueryCalls('change'));
});

}(jQuery));
