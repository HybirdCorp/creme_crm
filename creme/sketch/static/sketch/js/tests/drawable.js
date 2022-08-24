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
        drawable(d3.select(document.createElement('g')));
    }, Error, 'Error: Not implemented');
});

QUnit.test('creme.d3Drawable (call, single selection)', function(assert) {
    var FakeDrawable = creme.D3Drawable.sub({
        defaultProps: {
            a: 12, b: 'text'
        },

        draw: function(node) {
            d3.select(node).append('g')
                                .attr('class', 'fakeit');
        }
    });

    var drawable = creme.d3Drawable({
        instance: new FakeDrawable(),
        props: ['a', 'b']
    });

    var output = d3.select(document.createElement('g'));

    this.assertD3Nodes(output, {'.fakeit': 0});

    drawable(output);

    this.assertD3Nodes(output, {'.fakeit': 1});
});

QUnit.test('creme.d3Drawable (call, multiple selection)', function(assert) {
    var FakeDrawable = creme.D3Drawable.sub({
        defaultProps: {
            a: 12, b: 'text'
        },

        draw: function(node) {
            d3.select(node).append('g')
                                .attr('class', 'fakeit');
        }
    });

    var drawable = creme.d3Drawable({
        instance: new FakeDrawable(),
        props: ['a', 'b']
    });

    var output = d3.select(document.createElement('g'));
    output.append('g').attr('class', 'a');
    output.append('g').attr('class', 'b');

    this.assertD3Nodes(output, {'.fakeit': 0});

    equal(output.selectAll('g').size(), 2);
    drawable(output.selectAll('g'));

    this.assertD3Nodes(output, {'.fakeit': 2});
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

QUnit.parametrize('creme.d3TextWrap', [
    ['', {'text': {html: ''}}],
    ['short', {'text': {html: 'short'}}],
    ['toolongbutsingleword', {'text': {html: 'toolongbutsingleword'}}],
    ['a bit too long', {
        'text': {
            html: [
                '<tspan x="0">a bit too</tspan>',
                '<tspan x="0" dy="1.73em">long</tspan>'
            ].join('')
        }
    }],
    ['real long text that seems to never finish', {
        'text': {
            html: [
                '<tspan x="0">real long</tspan>',
                '<tspan x="0" dy="1.73em">text that</tspan>',
                '<tspan x="0" dy="1.73em">seems to</tspan>',
                '<tspan x="0" dy="1.73em">never</tspan>',
                '<tspan x="0" dy="1.73em">finish</tspan>'
            ].join('')
        }
    }]
], function(message, expected, assert) {
    var element = $('<div style="width: 100px; height: 100px; font-size: 10px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch().bind(element);
    var wrapper = creme.d3TextWrap().maxWidth(50).lineHeight('1.73em');

    var node = sketch.svg().append('text')
                               .attr('width', '50px')
                               .text(message);

    this.assertD3Nodes(sketch.svg(), {'text': {text: message}});

    node.call(wrapper);

    this.assertD3Nodes(sketch.svg(), expected);
});

}(jQuery));
