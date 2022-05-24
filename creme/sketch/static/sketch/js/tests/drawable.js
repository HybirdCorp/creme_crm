/* globals QUnitSketchMixin */
(function($) {

QUnit.module("creme.D3Drawable", new QUnitMixin(QUnitSketchMixin));

QUnit.test('creme.D3Drawable', function(assert) {
    var drawable = new creme.D3Drawable();

    deepEqual(drawable.props(), {});

    this.assertRaises(function() {
        drawable.draw({}, 0);
    }, Error, 'Error: Not implemented');
});

QUnit.test('creme.D3Drawable (props)', function(assert) {
    var FakeDrawable = creme.D3Drawable.sub({
        defaultProps: {
            a: 12, b: 'text'
        }
    });

    deepEqual(new FakeDrawable().props(), {a: 12, b: 'text'});
    deepEqual(new FakeDrawable({c: true, b: 8}).props(), {a: 12, b: 8, c: true});
    deepEqual(new FakeDrawable().props({c: true, b: 8}).props(), {a: 12, b: 8, c: true});
});

QUnit.test('creme.D3Drawable (props)', function(assert) {
    var drawable = creme.d3Drawable({
        instance: new creme.D3Drawable({a: 12, b: 'text'}),
        props: ['a', 'b', 'c']
    });

    deepEqual(drawable.props(), {a: 12, b: 'text'});
    equal(drawable.prop('a'), 12);
    equal(drawable.a(), 12);
    equal(drawable.prop('b'), 'text');
    equal(drawable.b(), 'text');
    equal(drawable.prop('c'), undefined);
    equal(drawable.c(), undefined);

    drawable.prop('a', 8);
    drawable.prop('c', true);

    deepEqual(drawable.props(), {a: 8, b: 'text', c: true});
    equal(drawable.a(), 8);
    equal(drawable.b(), 'text');
    equal(drawable.c(), true);

    drawable.a(17.5).b('othertext');
    deepEqual(drawable.props(), {a: 17.5, b: 'othertext', c: true});
});

QUnit.test('creme.d3Drawable (not implemented)', function(assert) {
    var drawable = creme.d3Drawable({
        instance: new creme.D3Drawable({a: 12, b: 'text'}),
        props: ['a', 'b']
    });

    this.assertRaises(function() {
        drawable({}, 0);
    }, Error, 'Error: Not implemented');
});

QUnit.test('creme.d3Drawable (render)', function(assert) {
    var FakeDrawable = creme.D3Drawable.sub({
        defaultProps: {
            a: 12, b: 'text'
        },

        draw: function(d, i) {
            d.fake = 'it!';
            d.index = i;
        }
    });

    var drawable = creme.d3Drawable({
        instance: new FakeDrawable(),
        props: ['a', 'b']
    });

    var output = {};

    drawable(output, 12);

    equal(output.fake, 'it!');
    equal(output.index, 12);
});

QUnit.test('creme.d3LegendRow', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var legend = creme.d3LegendRow().data(['A', 'B', 'C']);

    sketch.svg().append('g').call(legend);

    this.assertD3Nodes(sketch.svg(), {
        '.legend-item': 3
    });
});

QUnit.test('creme.d3LegendColumn', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var legend = creme.d3LegendColumn().data(['A', 'B', 'C']);

    sketch.svg().append('g').call(legend);

    this.assertD3Nodes(sketch.svg(), {
        '.legend-item': 3
    });
});

QUnit.test('creme.d3LimitStack', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var limits = creme.d3LimitStack().data([12, 105, 78]);

    sketch.svg().append('g').call(limits);

    this.assertD3Nodes(sketch.svg(), {
        '.limit': 3
    });
});

}(jQuery));
