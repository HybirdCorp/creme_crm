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

QUnit.parametrize('creme.d3TextWrap (word-break)', [
    ['', {'.wrapit': {html: ''}}],
    ['short', {'.wrapit': {html: 'short'}}],
    ['toolongbutasingleword', {'.wrapit': {html: 'toolongbutasingleword'}}],
    ['a bit too long', {
        '.wrapit': {
            html: [
                '<tspan x="0">a bit too</tspan>',
                '<tspan x="0" dy="1.73em">long</tspan>'
            ].join('')
        }
    }],
    ['real long text toolongbutasingleword that seems to never finish', {
        '.wrapit': {
            html: [
                '<tspan x="0">real long</tspan>',
                '<tspan x="0" dy="1.73em">text</tspan>',
                '<tspan x="0" dy="1.73em">toolongbutasingleword</tspan>',
                '<tspan x="0" dy="1.73em">that seems</tspan>',
                '<tspan x="0" dy="1.73em">to never</tspan>',
                '<tspan x="0" dy="1.73em">finish</tspan>'
            ].join('')
        }
    }]
], function(message, expected, assert) {
    var element = $('<div style="width: 100px; height: 100px; font-size: 10px; font-weight: normal; font-family: monospace;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch().bind(element);

    // Get approx width on 10 characters as reference (use monospace font)
    var text10Width = sketch.svg().append('text')
                                  .text('0123456789')
                                  .node()
                                      .getComputedTextLength();

    var node = sketch.svg().append('text')
                           .attr('class', 'wrapit')
                           .text(message);

    this.assertD3Nodes(sketch.svg(), {'.wrapit': {text: message}});

    // Wraps text on 10th character
    node.call(creme.d3TextWrap()
                        .maxWidth(text10Width)
                        .lineHeight('1.73em'));

    this.assertD3Nodes(sketch.svg(), expected);
});

QUnit.parametrize('creme.d3TextWrap (all-break)', [
    ['', {'.wrapit': {html: ''}}],
    ['short', {'.wrapit': {html: 'short'}}],
    ['toolongbutasingleword', {
        '.wrapit': {
            html: [
                '<tspan x="0">toolongbut-</tspan>',
                '<tspan x="0" dy="1.73em">asinglewor-</tspan>',
                '<tspan x="0" dy="1.73em">d</tspan>'
            ].join('')
        }
    }],
    ['a bit too long', {
        '.wrapit': {
            html: [
                '<tspan x="0">a bit too</tspan>',
                '<tspan x="0" dy="1.73em">long</tspan>'
            ].join('')
        }
    }],
    ['real long text toolongbutasingleword that seems to never finish', {
        '.wrapit': {
            html: [
                '<tspan x="0">real long</tspan>',
                '<tspan x="0" dy="1.73em">text</tspan>',
                '<tspan x="0" dy="1.73em">toolongbut-</tspan>',
                '<tspan x="0" dy="1.73em">asinglewor-</tspan>',
                '<tspan x="0" dy="1.73em">d that</tspan>',
                '<tspan x="0" dy="1.73em">seems to</tspan>',
                '<tspan x="0" dy="1.73em">never</tspan>',
                '<tspan x="0" dy="1.73em">finish</tspan>'
            ].join('')
        }
    }]
], function(message, expected, assert) {
    var element = $('<div style="width: 100px; height: 100px; font-size: 10px; font-weight: normal; font-family: monospace;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch().bind(element);

    // Get approx width on 10 characters as reference (use monospace font)
    var text10Width = sketch.svg().append('text')
                                  .text('0123456789')
                                  .node()
                                      .getComputedTextLength();

    var node = sketch.svg().append('text')
                           .attr('class', 'wrapit')
                           .text(message);

    this.assertD3Nodes(sketch.svg(), {'.wrapit': {text: message}});

    // Wraps text and split words on 10th character
    node.call(creme.d3TextWrap()
                        .maxWidth(text10Width)
                        .breakAll(true)
                        .lineHeight('1.73em'));

    this.assertD3Nodes(sketch.svg(), expected);
});

}(jQuery));
