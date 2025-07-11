(function($) {

QUnit.module("creme.model.ListRenderer", new QUnitMixin({
    assertItems: function(element, expected) {
        var assert = this.assert;
        var items = $('li', element);

        assert.equal(items.length, expected.length);

        items.each(function(index) {
            assert.equal($(this).html(), expected[index]);
        });
    }
}));

QUnit.test('creme.model.ListRenderer.constructor', function(assert) {
    var model = new creme.model.Array();
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    assert.equal(model, renderer.model());
    assert.equal(element, renderer.target());

    renderer = new creme.model.ListRenderer();

    assert.equal(undefined, renderer.model());
    assert.equal(undefined, renderer.target());
});

QUnit.test('creme.model.ListRenderer (empty model)', function(assert) {
    var model = new creme.model.Array();
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    assert.equal($('li', element).length, 0);

    renderer.redraw();

    assert.equal($('li', element).length, 0);
});

QUnit.test('creme.model.ListRenderer (filled model)', function(assert) {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    this.assertItems(element, []);

    renderer.redraw();
    this.assertItems(element, ['a', 'b']);
});

QUnit.test('creme.model.ListRenderer (empty model, add)', function(assert) {
    var model = new creme.model.Array();
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    renderer.redraw();
    this.assertItems(element, []);

    model.append(['a', 'b']);
    this.assertItems(element, ['a', 'b']);
});

QUnit.test('creme.model.ListRenderer (filled, model, add)', function(assert) {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    renderer.redraw();
    this.assertItems(element, ['a', 'b']);

    model.append(['c', 'd']);
    this.assertItems(element, ['a', 'b', 'c', 'd']);
});

QUnit.test('creme.model.ListRenderer (remove)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    renderer.redraw();
    this.assertItems(element, ['a', 'b', 'c', 'd']);

    model.removeAt(1);
    this.assertItems(element, ['a', 'c', 'd']);

    model.removeAt(2);
    this.assertItems(element, ['a', 'c']);
});

QUnit.test('creme.model.ListRenderer (update)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    renderer.redraw();
    this.assertItems(element, ['a', 'b', 'c', 'd']);

    model.set('g', 1);
    this.assertItems(element, ['a', 'g', 'c', 'd']);

    model.set('k', 2);
    this.assertItems(element, ['a', 'g', 'k', 'd']);
});

QUnit.test('creme.model.ListRenderer (switch model)', function(assert) {
    var model = new creme.model.Array();
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    renderer.redraw();
    assert.equal($('option', element).length, 0);

    model.append(['a', 'b']);
    this.assertItems(element, ['a', 'b']);

    model = new creme.model.Array(['x', 'y', 'z']);

    renderer.model(model).redraw();
    this.assertItems(element, ['x', 'y', 'z']);
});

QUnit.test('creme.model.ListRenderer (reset model)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    renderer.redraw();
    this.assertItems(element, ['a', 'b', 'c', 'd']);

    model.reset(['g', 'k']);
    this.assertItems(element, ['g', 'k']);

    model.reset(['x', 'y', 'z', 'a']);
    this.assertItems(element, ['x', 'y', 'z', 'a']);
});

}(jQuery));
