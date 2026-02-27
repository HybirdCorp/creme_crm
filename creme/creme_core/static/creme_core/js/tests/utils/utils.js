/* global QUnitConsoleMixin FunctionFaker */

(function($) {

QUnit.module("creme.widget.utils.js", new QUnitMixin(QUnitConsoleMixin, QUnitDialogMixin));

QUnit.test('creme.utils.comparator (simple)', function(assert) {
    var compare = creme.utils.comparator();

    assert.deepEqual(compare, creme.utils.compareTo);

    assert.equal(0, compare(12, 12));
    assert.equal(0, compare(4.57, 4.57));
    assert.equal(0, compare('test', 'test'));

    assert.equal(-1, compare(12, 13));
    assert.equal(-1, compare(4.57, 5.57));
    assert.equal(-1, compare('da test', 'test'));

    assert.equal(1, compare(13, 12));
    assert.equal(1, compare(5.57, 4.57));
    assert.equal(1, compare('test', 'da test'));
});

QUnit.test('creme.utils.comparator (key)', function(assert) {
    var compare = creme.utils.comparator('value');

    assert.equal(0, compare({value: 12}, {value: 12}));
    assert.equal(0, compare({value: 4.57}, {value: 4.57}));
    assert.equal(0, compare({value: 'test'}, {value: 'test'}));

    assert.equal(-1, compare({value: 12}, {value: 13}));
    assert.equal(-1, compare({value: 4.57}, {value: 5.57}));
    assert.equal(-1, compare({value: 'da test'}, {value: 'test'}));

    assert.equal(1, compare({value: 13}, {value: 12}));
    assert.equal(1, compare({value: 5.57}, {value: 4.57}));
    assert.equal(1, compare({value: 'test'}, {value: 'da test'}));
});

QUnit.test('creme.utils.comparator (multiple keys)', function(assert) {
    var compare = creme.utils.comparator('value', 'index');

    assert.equal(0, compare({value: 12, index: 0}, {value: 12, index: 0}));

    assert.equal(1, compare({value: 12, index: 1}, {value: 12, index: 0}));
    assert.equal(1, compare({value: 13, index: 0}, {value: 12, index: 1}));

    assert.equal(-1, compare({value: 12, index: 0}, {value: 12, index: 1}));
    assert.equal(-1, compare({value: 12, index: 1}, {value: 13, index: 0}));
});

QUnit.test('creme.utils.isHTMLDataType', function(assert) {
    assert.equal(creme.utils.isHTMLDataType('html'), true);
    assert.equal(creme.utils.isHTMLDataType('text/html'), true);
    assert.equal(creme.utils.isHTMLDataType('HTML'), true);
    assert.equal(creme.utils.isHTMLDataType('json'), false);

    assert.equal(creme.utils.isHTMLDataType(''), false);
    assert.equal(creme.utils.isHTMLDataType(), false);
    assert.equal(creme.utils.isHTMLDataType(null), false);
    assert.equal(creme.utils.isHTMLDataType(false), false);
    assert.equal(creme.utils.isHTMLDataType(12), false);
});

QUnit.parameterize('creme.utils.jQueryToMomentDateFormat', [
    ['', ''],
    ['d/m/y', 'D/M/YY'],
    ['d/m/yy', 'D/M/YYYY'],
    ['dd/mm/yy', 'DD/MM/YYYY']
], function(source, expected, assert) {
    assert.equal(creme.utils.jQueryToMomentDateFormat(source), expected);
});

QUnit.parametrize('creme.utils.ajaxQuery (error message)', [
    // xhr, textStatus, errorThrown
    [[{}, undefined, undefined], {
        header: gettext('Error'),
        message: 'HTTP 0 - ' + gettext('Error')
    }],
    [[{status: 0, statusText: 'error statusText'}, 'error', undefined], {
        header: gettext('Connection Refused'),
        message: 'HTTP 0 - error statusText'
    }],
    [[{status: 400, statusText: 'error statusText'}, 'error', ''], {
        header: gettext('Bad Request'),
        message: 'HTTP 400 - error statusText'
    }],
    [[{status: 501, statusText: 'error statusText'}, 'error', ''], {
        header: gettext('Error') + ' (501)',
        message: 'HTTP 501 - error statusText'
    }],
    [[{status: 0}, 'error', 'error thrown'], {
        header: gettext('Connection Refused'),
        message: 'HTTP 0 - error thrown'
    }],
    [[{status: 0, statusText: 'error statusText'}, 'parseerror', 'error thrown'], {
        header: gettext('Connection Refused'),
        message: 'JSON parse error'
    }],
    [[{status: 0, statusText: 'error statusText', responseText: 'error responseText'}, 'error', 'error thrown'], {
        header: gettext('Connection Refused'),
        message: 'error responseText'
    }]
], function(response, expected, assert) {
    var query;
    var ajaxFaker = new FunctionFaker({
        instance: $,
        method: 'ajax',
        callable: function(options) {
            options.error.apply(undefined, response);
        }
    });

    ajaxFaker.with(function() {
        query = creme.utils.ajaxQuery('mock/error', {warnOnFail: true});
        query.start();
    });

    assert.equal(query.isRunning(), true);

    var dialog = this.assertOpenedDialog();
    assert.equal(dialog.find('.header').html(), expected.header);
    assert.equal(dialog.find('.message').html(), expected.message);

    this.closeDialog();

    assert.equal(query.isRunning(), false);

    ajaxFaker.with(function() {
        query = creme.utils.ajaxQuery('mock/error', {warnOnFail: false});
        query.start();
    });

    this.assertClosedDialog();
    assert.equal(query.isRunning(), false);
});

}(jQuery));
