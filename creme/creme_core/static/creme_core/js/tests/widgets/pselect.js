(function($) {

QUnit.module("creme.widget.pselect.js", new QUnitMixin({
    beforeEach: function() {},
    afterEach: function() {},

    createPSelectHtml: function(options) {
        options = options || {};

        function renderSelector(entry) {
            return (
                '<script type="text/template" selector-key="${key}">${html}</script>'
            ).template({
                key: entry[0],
                html: entry[1]
            });
        }

        var html = (
            '<span widget="ui-creme-polymorphicselect" class="ui-creme-polymorphicselect ui-creme-widget ${auto}" key="${key}">' +
                '<input type="hidden" class="ui-creme-input ui-creme-polymorphicselect"/>' +
                '${selectors}' +
            '</span>'
        ).template({
            auto: options.auto ? 'widget-auto' : '',
            key: options.key || '',
            selectors: Object.entries(options.selectors || {}).map(renderSelector).join('')
        });

        return html;
    },

    createPSelect: function(options) {
        return creme.widget.create($(this.createPSelectHtml(options)));
    },

    assertSelector: function(widget, type, value, query) {
        var assert = this.assert;

        assert.equal(widget.selectorKey(), type, 'selector type');
        assert.equal(widget.val(), value, 'value');

        if (query !== undefined) {
            assert.ok(widget.selector() !== undefined, 'selector exists');
            assert.ok(widget.selector().element.is(query), 'selector match ' + query);
            assert.equal(widget.selector().val(), value, 'selector value');
        } else {
            assert.equal(widget.selector(), undefined, 'empty selector');
        }
    }
}));

QUnit.test('creme.widgets.pselect.create (empty, no selector)', function(assert) {
    var element = $(this.createPSelectHtml());
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), null);

    assert.equal(widget.selectorModels().length, 0);
    assert.equal(widget.selectorModel('*'), undefined);

    assert.equal(widget.selectorKey(), '');
    assert.equal(widget.selector(), undefined);
});

QUnit.test('creme.widgets.pselect.create (empty, single selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        selectors: {
            'text': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput"/>'
        }
    }));

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), null, 'value');

    assert.equal(widget.selectorModels().length, 1, 'model count');
    assert.equal(widget.selectorModel('*'), undefined, '* model');
    assert.notEqual(widget.selectorModel('text'), undefined, 'text model');

    assert.equal(widget.selectorKey(), '', 'key');
    assert.equal(widget.selector(), undefined, 'selector');
});

QUnit.test('creme.widgets.pselect.create (empty, default single selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        selectors: {
            '*': '<input type="text" class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput"/>'
        }
    }));

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), '', 'value');

    assert.equal(widget.selectorModels().length, 1);
    assert.notEqual(widget.selectorModel('*'), undefined);
    assert.notEqual(widget.selectorModel('text'), undefined);

    assert.equal(widget.selectorKey(), '');
    assert.equal(widget.selector().val(), '');
    assert.ok(widget.selector().element.is('input[type="text"].ui-creme-dinput'));
});

QUnit.test('creme.widgets.pselect.create (empty, multiple selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        selectors: {
            '*': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>',
            'password': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="password"/>',
            'boolean': (
                '<select class="ui-creme-widget ui-creme-dselect" widget="ui-creme-dselect">' +
                    '<option value="true">True</option>' +
                    '<option value="false">False</option>' +
                '</select>'
            )
        }
    }));

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), '');

    assert.equal(widget.selectorModels().length, 3);
    assert.notEqual(widget.selectorModel('text'), undefined);
    assert.notEqual(widget.selectorModel('password'), undefined);
    assert.notEqual(widget.selectorModel('boolean'), undefined);

    // if unknown use default
    assert.notEqual(widget.selectorModel('double'), undefined);
    assert.notEqual(widget.selectorModel('int'), undefined);
    assert.notEqual(widget.selectorModel('float'), undefined);

    assert.equal(widget.selectorKey(), '');
    assert.equal(widget.selector().val(), '');
    assert.ok(widget.selector().element.is('input[type="text"].ui-creme-dinput'));
});

QUnit.test('creme.widgets.pselect.create (empty, multiple selector, no default)', function(assert) {
    var element = $(this.createPSelectHtml({
        selectors: {
            'text': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>',
            'password': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="password"/>',
            'boolean': (
                '<select class="ui-creme-widget ui-creme-dselect" widget="ui-creme-dselect">' +
                    '<option value="true">True</option>' +
                    '<option value="false">False</option>' +
                '</select>'
            )
        }
    }));

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), null);

    assert.equal(widget.selectorModels().length, 3);
    assert.notEqual(widget.selectorModel('text'), undefined);
    assert.notEqual(widget.selectorModel('password'), undefined);
    assert.notEqual(widget.selectorModel('boolean'), undefined);

    assert.equal(widget.selectorModel('double'), undefined);
    assert.equal(widget.selectorModel('int'), undefined);
    assert.equal(widget.selectorModel('float'), undefined);

    assert.equal(widget.selectorKey(), '');
    assert.equal(widget.selector(), undefined);
});

QUnit.test('creme.widgets.pselect.val (unknown key, default selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: 'unknown',
        selectors: {
            '*': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>'
        }
    }));

    var widget = creme.widget.create(element);

    this.assertSelector(widget, 'unknown', '', '.ui-creme-dinput[type="text"]');

    widget.val(12.5);
    this.assertSelector(widget, 'unknown', 12.5, '.ui-creme-dinput[type="text"]');
});

QUnit.test('creme.widgets.pselect.val (key, no selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: 'text'
    }));

    var widget = creme.widget.create(element);

    this.assertSelector(widget, 'text', null);

    widget.val(12.5);
    this.assertSelector(widget, 'text', null);
});

QUnit.test('creme.widgets.pselect.val (selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: 'text',
        selectors: {
            'text': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>'
        }
    }));

    var widget = creme.widget.create(element);
    this.assertSelector(widget, 'text', '', '.ui-creme-dinput[type="text"]');

    widget.val(12.5);
    this.assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');
});

QUnit.test('creme.widgets.pselect.val (multiple selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: 'password',
        selectors: {
            'text': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>',
            'password': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="password"/>',
            'boolean': (
                '<select class="ui-creme-widget ui-creme-dselect" widget="ui-creme-dselect">' +
                    '<option value="true">True</option>' +
                    '<option value="false">False</option>' +
                '</select>'
            )
        }
    }));

    var widget = creme.widget.create(element);
    widget.val('toor');
    this.assertSelector(widget, 'password', 'toor', '.ui-creme-dinput[type="password"]');
});

QUnit.test('creme.widgets.pselect.reload (unknown type, default selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: '${operator}',
        selectors: {
            '*': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>'
        }
    }));

    var widget = creme.widget.create(element);

    assert.deepEqual(['operator'], widget.dependencies());
    this.assertSelector(widget, '', '', '.ui-creme-dinput[type="text"]');

    widget.reload({operator: 'text'});
    widget.val(12.5);
    this.assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');

    widget.reload({operator: 'boolean'});
    this.assertSelector(widget, 'boolean', 12.5, '.ui-creme-dinput[type="text"]');
});

QUnit.test('creme.widgets.pselect.reload (any type, default selector, template)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: '${operator}',
        selectors: {
            '*': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="${operator}"/>'
        }
    }));

    var widget = creme.widget.create(element);
    assert.deepEqual(['operator'], widget.dependencies());
    this.assertSelector(widget, '', '', '.ui-creme-dinput[type]');

    widget.reload({operator: 'text'});
    widget.val(12.5);
    this.assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');

    widget.reload({operator: 'boolean'});
    this.assertSelector(widget, 'boolean', '', '.ui-creme-dinput[type="boolean"]');
});

/*
 * Issue https://github.com/HybirdCorp/creme_crm/issues/61
 * The widget was removed from the DOM on a selector change
 */
QUnit.test('creme.widgets.pselect.reload (#61)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: '${operator}',
        selectors: {
            '*': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="${operator}"/>'
        }
    })).appendTo(this.qunitFixture());

    assert.equal(0, this.qunitFixture().find('.delegate .ui-creme-dinput[type]').length);

    var widget = creme.widget.create(element);
    assert.deepEqual(['operator'], widget.dependencies());
    this.assertSelector(widget, '', '', '.ui-creme-dinput[type]');

    assert.equal(1, this.qunitFixture().find('.delegate .ui-creme-dinput[type]').length);

    widget.reload({operator: 'text'});
    widget.val(12.5);
    this.assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');

    assert.equal(1, this.qunitFixture().find('.delegate .ui-creme-dinput[type="text"]').length);

    widget.reload({operator: 'boolean'});
    this.assertSelector(widget, 'boolean', '', '.ui-creme-dinput[type="boolean"]');

    assert.equal(1, this.qunitFixture().find('.delegate .ui-creme-dinput[type="boolean"]').length);
});

QUnit.test('creme.widgets.pselect.reload (unknown type, single selector, no default)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: '${operator}',
        selectors: {
            'text': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>'
        }
    }));

    var widget = creme.widget.create(element);
    assert.deepEqual(['operator'], widget.dependencies());
    this.assertSelector(widget, '', null);

    widget.reload({operator: 'text'});
    widget.val(12.5);
    this.assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');

    widget.reload({operator: 'boolean'});
    this.assertSelector(widget, 'boolean', null);
});

QUnit.test('creme.widgets.pselect.reload (type, value, multiple selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: '${operator}',
        selectors: {
            'text': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>',
            'password': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="password"/>',
            'boolean': (
                '<select class="ui-creme-widget ui-creme-dselect" widget="ui-creme-dselect">' +
                    '<option value="true" selected>True</option>' +
                    '<option value="false">False</option>' +
                '</select>'
            )
        }
    }));

    var widget = creme.widget.create(element);
    this.assertSelector(widget, '', null);

    widget.reload({operator: 'password'});
    widget.val('toor');

    this.assertSelector(widget, 'password', 'toor', '.ui-creme-dinput[type="password"]');

    widget.reload({operator: 'boolean'});
    this.assertSelector(widget, 'boolean', 'true', '.ui-creme-dselect');
});

QUnit.test('creme.widgets.pselect.reload (type, value, multiple selector, template)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: '${operator}.${type}',
        selectors: {
            'text.*': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>',
            'input.*': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="${type}"/>',
            'boolean.*': (
                '<select class="ui-creme-widget ui-creme-dselect" widget="ui-creme-dselect">' +
                    '<option value="true" selected>True</option>' +
                    '<option value="false">False</option>' +
                '</select>'
            )
        }
    }));

    var widget = creme.widget.create(element);
    this.assertSelector(widget, '', null);

    widget.reload({operator: 'input', type: 'password'});
    widget.val('toor');

    this.assertSelector(widget, 'input.password', 'toor', '.ui-creme-dinput[type="password"]');

    widget.reload({operator: 'input', type: 'boolean'});
    this.assertSelector(widget, 'input.boolean', '', '.ui-creme-dinput[type="boolean"]');

    widget.reload({operator: 'text', type: 'boolean'});
    this.assertSelector(widget, 'text.boolean', '', '.ui-creme-dinput[type="text"]');

    widget.reload({operator: 'boolean'});
    this.assertSelector(widget, 'boolean.boolean', 'true', '.ui-creme-dselect');
});

QUnit.test('creme.widgets.pselect.reset (type, value, multiple selector)', function(assert) {
    var element = $(this.createPSelectHtml({
        key: '${operator}',
        selectors: {
            'text': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="text"/>',
            'password': '<input class="ui-creme-widget ui-creme-dinput" widget="ui-creme-dinput" type="password"/>',
            'boolean': (
                '<select class="ui-creme-widget ui-creme-dselect" widget="ui-creme-dselect">' +
                    '<option value="true" selected>True</option>' +
                    '<option value="false">False</option>' +
                '</select>'
            )
        }
    }));

    var widget = creme.widget.create(element);

    widget.reload({operator: 'password'});
    widget.val('toor');
    this.assertSelector(widget, 'password', 'toor', '.ui-creme-dinput[type="password"]');

    widget.reset();
    this.assertSelector(widget, 'password', '', '.ui-creme-dinput[type="password"]');
});

}(jQuery));
