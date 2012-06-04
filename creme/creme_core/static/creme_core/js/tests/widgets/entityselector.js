MockEntitySelector = function(backend) {
    return $.extend({}, creme.widget.EntitySelector, {
        options: $.extend({}, creme.widget.EntitySelector.options, {backend:backend})
    });
};

function mock_entityselector_create(options, noauto) {
    var options = $.extend({label: "select a mock", labelURL: "mock/label/${id}"}, options);

    var select = creme.widget.buildTag($('<span/>'), 'ui-creme-entityselector', options, !noauto)
                     .append($('<button type="button"/>'))
                     .append($('<input type="hidden" class="ui-creme-entityselector ui-creme-input"/>'));

    return select;
}

var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';

module("creme.widgets.entityselector.js", {
  setup: function() {
      this.backend = new MockAjaxBackend({sync:true});
      $.extend(this.backend.GET, {'mock/label/1': this.backend.response(200, [['John Doe']]),
                                  'mock/label/2': this.backend.response(200, [['Bean Bandit']]),
                                  'mock/popup': this.backend.response(200, MOCK_FRAME_CONTENT),
                                  'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                  'mock/error': this.backend.response(500, 'HTTP - Error 500')});

      creme.widget.unregister('ui-creme-entityselector');
      creme.widget.declare('ui-creme-entityselector', new MockEntitySelector(this.backend));
  },
  teardown: function() {
  },
});

test('creme.widget.EntitySelector.create (empty, auto)', function() {
    var element = mock_entityselector_create();

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

test('creme.widget.EntitySelector.create (not empty, auto)', function() {
    var element = mock_entityselector_create();
    creme.widget.input(element).val('1');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("John Doe", $('button', element).text());
    equal("1", element.creme().widget().val());
    equal("", element.creme().widget().options().popupURL);
    equal("mock/label/${id}", element.creme().widget().options().labelURL);
    equal("select a mock", element.creme().widget().options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, element.creme().widget().options().popupSelection);
    equal("", element.creme().widget().options().qfilter);
});

test('creme.widget.EntitySelector.create (empty, popup url, auto)', function() {
    var element = mock_entityselector_create({popupURL:'mock/label'});

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

test('creme.widget.EntitySelector.create (empty, invalid label url, auto)', function() {
    var element = mock_entityselector_create({labelURL:'mock/label/unknown'});

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

test('creme.widget.EntitySelector.create (not empty, invalid label url, auto)', function() {
    var element = mock_entityselector_create({labelURL:'mock/label/unknown'});
    creme.widget.input(element).val('1');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal("select a mock", $('button', element).text());
    equal("1", element.creme().widget().val());
    equal("", element.creme().widget().options().popupURL);
    equal("mock/label/unknown", element.creme().widget().options().labelURL);
    equal("select a mock", element.creme().widget().options().label);
    equal(creme.widget.EntitySelectorMode.SINGLE, element.creme().widget().options().popupSelection);
    equal("", element.creme().widget().options().qfilter);
});

test('creme.widget.EntitySelector.val', function() {
    var element = mock_entityselector_create();

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
    equal("select a mock", $('button', element).text());
    equal("unknown", element.creme().widget().val());
});

test('creme.widget.EntitySelector.multiple', function() {
    var element = mock_entityselector_create();
    creme.widget.create(element);

    equal(creme.widget.EntitySelectorMode.SINGLE, element.creme().widget().delegate._popupURL.parameters.selection);
    equal(element.creme().widget().isMultiple(), false);

    element.creme().widget().multiple(true);

    equal(creme.widget.EntitySelectorMode.MULTIPLE, element.creme().widget().delegate._popupURL.parameters.selection);
    equal(element.creme().widget().isMultiple(), true);

    var element = mock_entityselector_create({popupSelection: creme.widget.EntitySelectorMode.MULTIPLE});
    creme.widget.create(element);

    equal(creme.widget.EntitySelectorMode.MULTIPLE, element.creme().widget().options().popupSelection);
    equal(creme.widget.EntitySelectorMode.MULTIPLE, element.creme().widget().delegate._popupURL.parameters.selection);
    equal(element.creme().widget().isMultiple(), true);
});

test('creme.widget.EntitySelector.reload (url)', function() {
    var element = mock_entityselector_create();
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

test('creme.widget.EntitySelector.reload (template url, multiple)', function() {
    var element = mock_entityselector_create({popupURL:'mock/popup/${selection}'});

    creme.widget.create(element);
    deepEqual(['selection'], element.creme().widget().dependencies());

    equal("mock/popup/1", element.creme().widget().popupURL());

    element.creme().widget().multiple(true);
    equal("mock/popup/0", element.creme().widget().popupURL());

    element.creme().widget().reload({selection:2});
    equal("mock/popup/2", element.creme().widget().popupURL());
});

test('creme.widget.EntitySelector.reload (template url, multiple, qfilter)', function() {
    var element = mock_entityselector_create({popupURL:'mock/popup/${selection}?q_filter=${qfilter}'});

    creme.widget.create(element);
    deepEqual(['selection', 'qfilter'], element.creme().widget().dependencies());

    equal("mock/popup/1?q_filter=", element.creme().widget().popupURL());

    element.creme().widget().reload({selection:0});
    equal("mock/popup/0?q_filter=", element.creme().widget().popupURL());

    element.creme().widget().reload({qfilter:$.toJSON({"~pk__in":[1, 2]})});
    equal("mock/popup/0?q_filter=" + $.toJSON({"~pk__in":[1, 2]}), element.creme().widget().popupURL());

    element.creme().widget().reload('mock/popup/${ctype}/${selection}?q_filter=${qfilter}');
    deepEqual(['ctype', 'selection', 'qfilter'], element.creme().widget().dependencies());
    equal("mock/popup/${ctype}/0?q_filter=" + $.toJSON({"~pk__in":[1, 2]}), element.creme().widget().popupURL());
});
