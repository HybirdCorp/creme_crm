/* globals QUnitWidgetMixin */
(function($) {

var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';

QUnit.module("creme.widget.entityselector.js", new QUnitMixin(QUnitAjaxMixin, QUnitWidgetMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.widget.entityselector.js'});
    },

    beforeEach: function() {
        this.setMockBackendGET({
            'mock/label/1': this.backend.responseJSON(200, [['John Doe']]),
            'mock/label/2': this.backend.responseJSON(200, [['Bean Bandit']]),
            'mock/popup': this.backend.response(200, MOCK_FRAME_CONTENT),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));
    }
}));

QUnit.test('creme.widget.EntitySelector.create (empty, auto)', function(assert) {
    var element = this.createEntitySelectorTag();

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("select a mock", $('button', element).text());
    equal("", element.creme().widget().val());
    equal("", element.creme().widget().options().popupURL);
    equal("mock/label/${id}", element.creme().widget().options().labelURL);
    equal("select a mock", element.creme().widget().options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, element.creme().widget().options().popupSelection);
    equal("", element.creme().widget().options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (not empty, auto)', function(assert) {
    var element = this.createEntitySelectorTag();
    creme.widget.input(element).val('1');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("John Doe", $('button', element).text());
    equal($('button', element).is('[disabled]'), false);
    equal(element.creme().widget().delegate._enabled, true);

    equal("1", element.creme().widget().val());
    equal("", element.creme().widget().options().popupURL);
    equal("mock/label/${id}", element.creme().widget().options().labelURL);
    equal("select a mock", element.creme().widget().options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, element.creme().widget().options().popupSelection);
    equal("", element.creme().widget().options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (auto, [disabled] attribute)', function(assert) {
    var element = this.createEntitySelectorTag({disabled: ''});
    creme.widget.input(element).val('1');

    creme.widget.create(element);
    equal(element.hasClass('widget-ready'), true);

    equal($('button', element).is('[disabled]'), true);
    equal("1", element.creme().widget().val());
    equal(element.creme().widget().delegate._enabled, false);
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
    equal("2", element.creme().widget().val());
});

QUnit.test('creme.widget.EntitySelector.create (empty, popup url, auto)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/label'});

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("select a mock", $('button', element).text());
    equal("", element.creme().widget().val());
    equal("mock/label", element.creme().widget().options().popupURL);
    equal("mock/label/${id}", element.creme().widget().options().labelURL);
    equal("select a mock", element.creme().widget().options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, element.creme().widget().options().popupSelection);
    equal("", element.creme().widget().options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (empty, invalid label url, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/unknown'});

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("select a mock", $('button', element).text());
    equal("", element.creme().widget().val());
    equal("", element.creme().widget().options().popupURL);
    equal("mock/label/unknown", element.creme().widget().options().labelURL);
    equal("select a mock", element.creme().widget().options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, element.creme().widget().options().popupSelection);
    equal("", element.creme().widget().options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.create (not empty, invalid label url, auto)', function(assert) {
    var element = this.createEntitySelectorTag({labelURL: 'mock/label/unknown'});
    creme.widget.input(element).val('1');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

//    equal("select a mock", $('button', element).text());
    equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('1'));
    equal("1", element.creme().widget().val());
    equal("", element.creme().widget().options().popupURL);
    equal("mock/label/unknown", element.creme().widget().options().labelURL);
    equal("select a mock", element.creme().widget().options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, element.creme().widget().options().popupSelection);
    equal("", element.creme().widget().options().qfilter);
});

QUnit.test('creme.widget.EntitySelector.val', function(assert) {
    var element = this.createEntitySelectorTag();

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("select a mock", $('button', element).text());
    equal("", element.creme().widget().val());

    element.creme().widget().val('2');
    equal("Bean Bandit", $('button', element).text());
    equal("2", element.creme().widget().val());

    element.creme().widget().val('1');
    equal("John Doe", $('button', element).text());
    equal("1", element.creme().widget().val());

    element.creme().widget().val('unknown');
//    equal("select a mock", $('button', element).text());
    equal($('button', element).text(), gettext('Entity #%s (not viewable)').format('unknown'));
    equal("unknown", element.creme().widget().val());
});

QUnit.test('creme.widget.EntitySelector.multiple', function(assert) {
    var element = this.createEntitySelectorTag();
    creme.widget.create(element);

    equal(creme.widget.EntitySelectorMode.SINGLE, element.creme().widget().delegate._popupURL.parameters().selection);
    equal(element.creme().widget().isMultiple(), false);

    element.creme().widget().isMultiple(true);

    equal(creme.widget.EntitySelectorMode.MULTIPLE, element.creme().widget().delegate._popupURL.parameters().selection);
    equal(element.creme().widget().isMultiple(), true);

    element = this.createEntitySelectorTag({popupSelection: creme.widget.EntitySelectorMode.MULTIPLE});
    creme.widget.create(element);

    equal(creme.widget.EntitySelectorMode.MULTIPLE, element.creme().widget().options().popupSelection);
    equal(creme.widget.EntitySelectorMode.MULTIPLE, element.creme().widget().delegate._popupURL.parameters().selection);
    equal(element.creme().widget().isMultiple(), true);
});

QUnit.test('creme.widget.EntitySelector.reload (url)', function(assert) {
    var element = this.createEntitySelectorTag();
    creme.widget.create(element);
    deepEqual([], element.creme().widget().dependencies());


    element.creme().widget().val('2');
    equal("Bean Bandit", $('button', element).text());
    equal("2", element.creme().widget().val());
    equal("", element.creme().widget().popupURL());

    element.creme().widget().reload('mock/popup');
    equal("select a mock", $('button', element).text());
    equal("", element.creme().widget().val());
    equal("mock/popup", element.creme().widget().popupURL());
});

QUnit.test('creme.widget.EntitySelector.reload (template url, multiple)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/popup/${selection}'});

    creme.widget.create(element);
    deepEqual(['selection'], element.creme().widget().dependencies());

    equal("mock/popup/single", element.creme().widget().popupURL());

    element.creme().widget().isMultiple(true);
    equal("mock/popup/multiple", element.creme().widget().popupURL());

    element.creme().widget().reload({selection: 2});
    equal("mock/popup/2", element.creme().widget().popupURL());
});

QUnit.test('creme.widget.EntitySelector.reload (template url, multiple, qfilter)', function(assert) {
    var element = this.createEntitySelectorTag({popupURL: 'mock/popup/${selection}?q_filter=${qfilter}'});

    creme.widget.create(element);
    deepEqual(['selection', 'qfilter'], element.creme().widget().dependencies());

    equal("mock/popup/single?q_filter=", element.creme().widget().popupURL());

    element.creme().widget().reload({selection: creme.widget.EntitySelectorMode.MULTIPLE});
    equal("mock/popup/multiple?q_filter=", element.creme().widget().popupURL());

    element.creme().widget().reload({qfilter: $.toJSON({"~pk__in": [1, 2]})});
    equal("mock/popup/multiple?q_filter=" + $.toJSON({"~pk__in": [1, 2]}), element.creme().widget().popupURL());

    element.creme().widget().reload('mock/popup/${ctype}/${selection}?q_filter=${qfilter}');
    deepEqual(['ctype', 'selection', 'qfilter'], element.creme().widget().dependencies());
    equal("mock/popup/${ctype}/multiple?q_filter=" + $.toJSON({"~pk__in": [1, 2]}), element.creme().widget().popupURL());
});

QUnit.test('creme.widget.EntitySelector.reset', function(assert) {
    var element = this.createEntitySelectorTag();
    var widget = creme.widget.create(element);
    deepEqual([], element.creme().widget().dependencies());

    widget.val('2');
    equal("Bean Bandit", $('button', element).text());
    equal("2", widget.val());
    equal("", widget.popupURL());

    widget.reset();

    equal("select a mock", $('button', element).text());
    equal("", widget.val());
    equal("", widget.popupURL());
});
}(jQuery));
