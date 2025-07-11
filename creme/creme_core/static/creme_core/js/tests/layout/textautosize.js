(function($) {

QUnit.module("creme.layout.autosize", new QUnitMixin(QUnitEventMixin, {
}));

QUnit.test('creme.layout.TextAreaAutoSize (default)', function(assert) {
    var layout = new creme.layout.TextAreaAutoSize();
    assert.equal(layout._min, 2);
    assert.equal(layout._max, undefined);
});

QUnit.test('creme.layout.TextAreaAutoSize (options)', function(assert) {
    var layout = new creme.layout.TextAreaAutoSize({
        min: 5, max: 20
    });
    assert.equal(layout._min, 5);
    assert.equal(layout._max, 20);
});

QUnit.test('creme.layout.TextAreaAutoSize (bind)', function(assert) {
    var layout = new creme.layout.TextAreaAutoSize();
    var element = $('<textarea></textarea>');

    assert.equal(layout._delegate, undefined);

    layout.bind(element);

    assert.deepEqual(layout._delegate, element);

    this.assertRaises(function() {
        layout.bind(element);
    }, Error, 'Error: already bound');
});

QUnit.test('creme.layout.TextAreaAutoSize (unbind)', function(assert) {
    var layout = new creme.layout.TextAreaAutoSize();
    var element = $('<textarea></textarea>');

    layout.bind(element);
    assert.deepEqual(layout._delegate, element);

    layout.unbind();
    assert.equal(layout._delegate, undefined);

    this.assertRaises(function() {
        layout.unbind();
    }, Error, 'Error: not bound');
});

QUnit.parametrize('creme.layout.TextAreaAutoSize (initial state)', [
    [$('<textarea></textarea>'), {}, {initial: 1, rows: 2, min: 2}],
    [$('<textarea rows="4"></textarea>'), {}, {initial: 4, rows: 2, min: 2}],
    [$('<textarea rows="NaN"></textarea>'), {}, {initial: 1, rows: 2, min: 2}],
    [$('<textarea rows="4"></textarea>'), {max: 3}, {initial: 4, rows: 2, min: 2, max: 3}],

    [$('<textarea>L1\nL2\nL3\nL4\n</textarea>'), {}, {initial: 1, rows: 5, min: 2}],
    [$('<textarea>L1\nL2\nL3\nL4\n</textarea>'), {max: 3}, {initial: 1, rows: 3, min: 2, max: 3}]
], function(element, options, expected, assert) {
    var layout = new creme.layout.TextAreaAutoSize(options);
    layout.bind(element);

    assert.equal(layout._initial, expected.initial);
    assert.equal(element.attr('rows'), String(expected.rows));
});

QUnit.parametrize('creme.layout.TextAreaAutoSize (change)', [
    [$('<textarea>L1\nL2</textarea>'), 'input', {keyCode: 27}, {rows: 2}],
    [$('<textarea>L1\nL2</textarea>'), 'input', {keyCode: 13}, {rows: 3}]
], function(element, event, eventData, expected, assert) {
    var layout = new creme.layout.TextAreaAutoSize();
    layout.bind(element);

    element.trigger($.Event(event, eventData));
    assert.equal(element.attr('rows'), String(expected.rows));
});

}(jQuery));
