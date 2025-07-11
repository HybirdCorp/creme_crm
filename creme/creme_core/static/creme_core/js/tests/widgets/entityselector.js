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
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal("select a mock", $('button', element).text());
    assert.equal("", widget.val());
    assert.equal("", widget.options().popupURL);
    assert.equal("mock/label/${id}", widget.options().labelURL);
    assert.equal("select a mock", widget.options().label);
    assert.equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    assert.equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (not empty, auto)', function(assert) {
    var element = this.createEntitySelectorTag();
    creme.widget.input(element).val('1');

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal("John Doe", $('button', element).text());
    assert.equal($('button', element).is('[disabled]'), false);
    assert.equal(widget.delegate._enabled, true);

    assert.equal("1", widget.val());
    assert.equal("", widget.options().popupURL);
    assert.equal("mock/label/${id}", widget.options().labelURL);
    assert.equal("select a mock", widget.options().label);
    assert.equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    assert.equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (auto, [disabled] attribute)', function(assert) {
    var element = this.createEntitySelectorTag({disabled: ''});
    creme.widget.input(element).val('1');

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal($('button', element).is('[disabled]'), true);
    assert.equal("1", widget.val());
    assert.equal(widget.delegate._enabled, false);
});

QUnit.test('creme.widget.EntitySelector.create (auto, {disabled: true} option)', function(assert) {
    var element = this.createEntitySelectorTag();
    creme.widget.input(element).val('2');

    assert.equal(element.is('[disabled]'), false);

    var widget = creme.widget.create(element, {disabled: true});

    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.is('[disabled]'), true);
    assert.equal(widget.delegate._enabled, false);

    assert.equal($('button', element).is('[disabled]'), true);
    assert.equal("2", widget.val());
});

QUnit.test('creme.widget.EntitySelector.create (empty, popup url, auto)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/label'});

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal("select a mock", $('button', element).text());
    assert.equal("", widget.val());
    assert.equal("mock/label", widget.options().popupURL);
    assert.equal("mock/label/${id}", widget.options().labelURL);
    assert.equal("select a mock", widget.options().label);
    assert.equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    assert.equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (empty, invalid label url, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/unknown'});

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal("select a mock", $('button', element).text());
    assert.equal("", widget.val());
    assert.equal("", widget.options().popupURL);
    assert.equal("mock/label/unknown", widget.options().labelURL);
    assert.equal("select a mock", widget.options().label);
    assert.equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    assert.equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (not empty, invalid label url, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/unknown'});
    creme.widget.input(element).val('1');

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('1'));
    assert.equal("1", widget.val());
    assert.equal("", widget.options().popupURL);
    assert.equal("mock/label/unknown", widget.options().labelURL);
    assert.equal("select a mock", widget.options().label);
    assert.equal(creme.widget.EntitySelectorMode.SINGLE, widget.options().popupSelection);
    assert.equal("", widget.options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (not empty, empty label data, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/empty'});
    creme.widget.input(element).val('1');

    creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('1'));
});

QUnit.test('creme.widget.EntitySelector.create (not empty, missing label data, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/missing'});
    creme.widget.input(element).val('1');

    creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('1'));
});

QUnit.test('creme.widget.EntitySelector.val (required)', function(assert) {
    var element = this.createEntitySelectorTag();

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    var input = element.find('input');
    var button = element.find('button');

    assert.equal("select a mock", button.text());
    assert.equal("", widget.val());
    assert.equal("", input.val());
    assert.equal(false, input.is(':invalid'));
    assert.equal(false, button.is('.is-field-invalid'));

    // not required
    creme.forms.validateHtml5Field(input);
    assert.equal(false, input.is(':required'));
    assert.equal(false, input.is(':invalid'));
    assert.equal(false, button.is('.is-field-invalid'));

    // required
    input.attr('required', '');
    creme.forms.validateHtml5Field(input);
    assert.equal(true, input.is(':required'));
    assert.equal(true, input.is(':invalid'));
    assert.equal(true, button.is('.is-field-invalid'));

    widget.val('2');

    creme.forms.validateHtml5Field(input);
    assert.equal("Bean Bandit", button.text());
    assert.equal("2", widget.val());
    assert.equal("2", input.val());
    assert.equal(false, input.is(':invalid'));
    assert.equal(false, button.is('.is-field-invalid'));
});

QUnit.test('creme.widget.EntitySelector.val', function(assert) {
    var element = this.createEntitySelectorTag();

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal("select a mock", $('button', element).text());
    assert.equal("", widget.val());

    widget.val('2');
    assert.equal("Bean Bandit", $('button', element).text());
    assert.equal("2", widget.val());

    widget.val('1');
    assert.equal("John Doe", $('button', element).text());
    assert.equal("1", widget.val());

    widget.val('unknown');
    assert.equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('unknown'));
    assert.equal("unknown", widget.val());
});

QUnit.test('creme.widget.EntitySelector.update', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);

    assert.equal("select a mock", $('button', element).text());
    assert.equal("", widget.val());

    widget.update({value: '2'});

    assert.equal("Bean Bandit", $('button', element).text());
    assert.equal("2", widget.val());
});

QUnit.test('creme.widget.EntitySelector.multiple (setter)', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);

    assert.equal(creme.widget.EntitySelectorMode.SINGLE, widget.delegate._popupURL.parameters().selection);
    assert.equal(widget.isMultiple(), false);

    widget.isMultiple(true);

    assert.equal(creme.widget.EntitySelectorMode.MULTIPLE, widget.delegate._popupURL.parameters().selection);
    assert.equal(widget.isMultiple(), true);
});

QUnit.test('creme.widget.EntitySelector.multiple (constructor)', function(assert) {
    var element = this.createEntitySelectorTag({popupSelection: creme.widget.EntitySelectorMode.MULTIPLE});
    var widget = creme.widget.create(element);

    assert.equal(creme.widget.EntitySelectorMode.MULTIPLE, widget.options().popupSelection);
    assert.equal(creme.widget.EntitySelectorMode.MULTIPLE, widget.delegate._popupURL.parameters().selection);
    assert.equal(widget.isMultiple(), true);
});

QUnit.test('creme.widget.EntitySelector.qfilter (setter)', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);

    assert.equal("", widget.delegate._popupURL.parameters().qfilter);

    widget.qfilter('{"id": 12}');

    assert.equal('{"id": 12}', widget.delegate._popupURL.parameters().qfilter);
});

QUnit.test('creme.widget.EntitySelector.reload (url)', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);
    assert.deepEqual([], widget.dependencies());


    widget.val('2');
    assert.equal("Bean Bandit", $('button', element).text());
    assert.equal("2", widget.val());
    assert.equal("", widget.popupURL());

    widget.reload('mock/listview');
    assert.equal("select a mock", $('button', element).text());
    assert.equal("", widget.val());
    assert.equal("mock/listview", widget.popupURL());
});

QUnit.test('creme.widget.EntitySelector.reload (template url, multiple)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});

    var widget = creme.widget.create(element);
    assert.deepEqual(['selection'], widget.dependencies());

    assert.equal("mock/listview/single", widget.popupURL());

    widget.isMultiple(true);
    assert.equal("mock/listview/multiple", widget.popupURL());

    widget.reload({selection: 2});
    assert.equal("mock/listview/2", widget.popupURL());
});

QUnit.test('creme.widget.EntitySelector.reload (template url, multiple, qfilter)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}?q_filter=${qfilter}'});

    var widget = creme.widget.create(element);
    assert.deepEqual(['selection', 'qfilter'], widget.dependencies());

    assert.equal("mock/listview/single?q_filter=", widget.popupURL());

    widget.reload({selection: creme.widget.EntitySelectorMode.MULTIPLE});
    assert.equal("mock/listview/multiple?q_filter=", widget.popupURL());

    widget.reload({qfilter: JSON.stringify({"~pk__in": [1, 2]})});
    assert.equal("mock/listview/multiple?q_filter=" + JSON.stringify({"~pk__in": [1, 2]}), widget.popupURL());

    widget.reload('mock/listview/${ctype}/${selection}?q_filter=${qfilter}');
    assert.deepEqual(['ctype', 'selection', 'qfilter'], widget.dependencies());
    assert.equal("mock/listview/${ctype}/multiple?q_filter=" + JSON.stringify({"~pk__in": [1, 2]}), widget.popupURL());
});

QUnit.test('creme.widget.EntitySelector.reset', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);
    assert.deepEqual([], widget.dependencies());

    widget.val('2');
    assert.equal("Bean Bandit", $('button', element).text());
    assert.equal("2", widget.val());
    assert.equal("", widget.popupURL());

    widget.reset();

    assert.equal("select a mock", $('button', element).text());
    assert.equal("", widget.val());
    assert.equal("", widget.popupURL());
});

QUnit.test('creme.widget.EntitySelector.select (single)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});

    var widget = creme.widget.create(element);

    assert.deepEqual(['selection'], widget.dependencies());
    assert.equal("mock/listview/single", widget.popupURL());

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    this.assertClosedDialog();
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/single'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    $('button', element).trigger('click');

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    assert.deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/single'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1']);
    this.validateListViewSelectionDialog(dialog);

    assert.equal("John Doe", $('button', element).text());
    assert.equal('1', widget.val());
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([['change']], this.mockListenerJQueryCalls('change'));
});

QUnit.test('creme.widget.EntitySelector.select (single, filtered)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});

    var widget = creme.widget.create(element);

    assert.deepEqual(['selection'], widget.dependencies());
    assert.equal("mock/listview/single", widget.popupURL());

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    this.assertClosedDialog();
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/single'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    $('button', element).trigger('click');

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    assert.deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/single'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1']);
    this.validateListViewSelectionDialog(dialog);

    assert.equal("John Doe", $('button', element).text());
    assert.equal('1', widget.val());
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([['change']], this.mockListenerJQueryCalls('change'));
});

QUnit.test('creme.widget.EntitySelector.select (multiple)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});
    var widget = creme.widget.create(element);
    widget.isMultiple(true);

    assert.equal("mock/listview/multiple", widget.popupURL());
    this.assertClosedDialog();

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    $('button', element).trigger('click');

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    assert.deepEqual([
        ['GET', {selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1', '3']);
    this.validateListViewSelectionDialog(dialog);

    assert.equal("John Doe", $('button', element).text());
    assert.equal('1', widget.val());

    assert.deepEqual([['change-multiple', [['1', '3']]]], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([['change']], this.mockListenerJQueryCalls('change'));
});

QUnit.test('creme.widget.EntitySelector.select (cancel)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});
    var widget = creme.widget.create(element);

    assert.deepEqual(['selection'], widget.dependencies());
    assert.equal("mock/listview/single", widget.popupURL());

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    this.assertClosedDialog();
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/single'));
    assert.deepEqual([], this.mockListenerCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    $('button', element).trigger('click');

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    assert.deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/single'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1']);
    this.closeDialog();

    this.assertClosedDialog();

    assert.equal("select a mock", $('button', element).text());
    assert.equal('', widget.val());

    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));
});

QUnit.test('creme.widget.EntitySelector.select (action)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/listview/${selection}'});
    var widget = creme.widget.create(element);

    assert.deepEqual(['selection'], widget.dependencies());
    assert.equal("mock/listview/single", widget.popupURL());

    element.on('change-multiple', this.mockListener('change-multiple'));
    element.on('change', this.mockListener('change'));

    this.assertClosedDialog();
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/single'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    element.trigger('action', ['select']);

    var dialog = this.assertOpenedListViewDialog();
    var list = dialog.find('.ui-creme-listview').list_view('instance');

    assert.deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/single'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change'));

    this.setListviewSelection(list, ['1']);
    this.validateListViewSelectionDialog(dialog);

    assert.equal("John Doe", $('button', element).text());
    assert.equal('1', widget.val());
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));
    assert.deepEqual([['change']], this.mockListenerJQueryCalls('change'));
});

}(jQuery));
