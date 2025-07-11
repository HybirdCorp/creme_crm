/* globals QUnitSketchMixin, WheelEvent */
(function($) {

QUnit.module("creme.D3Drawable", new QUnitMixin(QUnitSketchMixin));

QUnit.test('creme.D3Drawable', function(assert) {
    var drawable = new creme.D3Drawable();

    assert.deepEqual(drawable.props(), {});

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

    assert.deepEqual(new FakeDrawable().props(), {a: 12, b: 'text'});
    assert.deepEqual(new FakeDrawable({c: true, b: 8}).props(), {a: 12, b: 8, c: true});
    assert.deepEqual(new FakeDrawable().props({c: true, b: 8}).props(), {a: 12, b: 8, c: true});
});

QUnit.test('creme.d3Drawable (props)', function(assert) {
    var drawable = creme.d3Drawable({
        instance: new creme.D3Drawable({a: 12, b: 'text'}),
        props: ['a', 'b', 'c']
    });

    assert.deepEqual(drawable.props(), {a: 12, b: 'text'});
    assert.equal(drawable.prop('a'), 12);
    assert.equal(drawable.a(), 12);
    assert.equal(drawable.prop('b'), 'text');
    assert.equal(drawable.b(), 'text');
    assert.equal(drawable.prop('c'), undefined);
    assert.equal(drawable.c(), undefined);

    drawable.prop('a', 8);
    drawable.prop('c', true);

    assert.deepEqual(drawable.props(), {a: 8, b: 'text', c: true});
    assert.equal(drawable.a(), 8);
    assert.equal(drawable.b(), 'text');
    assert.equal(drawable.c(), true);

    drawable.a(17.5).b('othertext');
    assert.deepEqual(drawable.props(), {a: 17.5, b: 'othertext', c: true});
});

QUnit.test('creme.d3Drawable (methods)', function(assert) {
    var FakeDrawable = creme.D3Drawable.sub({
        defaultProps: {
            a: 12, b: 'text', label: 'Called : ${label}'
        },

        funcA: function(node, datum, i) {
            d3.select(node).append('text')
                               .attr('class', 'func-a a-${0}'.template([i]))
                               .attr('title', this.prop('label').template({label: datum}));
        },

        funcB: function(node, datum, i) {
            console.log(node, datum, i);
            d3.select(node).classed('func-b b-${0}'.template([i]), true);
        }
    });

    var drawable = creme.d3Drawable({
        instance: new FakeDrawable(),
        props: ['a', 'b'],
        methods: ['funcA', 'funcB']
    });

    assert.equal(true, Object.isFunc(drawable.funcA));
    assert.equal(true, Object.isFunc(drawable.funcB));

    var output = d3.select(document.createElement('g'));

    this.assertD3Nodes(output, {
        '.func-a': 0,
        '.func-b': 0
    });

    var items = output.selectAll('.func-a')
                      .data(['A1', 'A2']);

    items.enter().call(drawable.funcA);

    this.assertD3Nodes(output, {
        '.a-0': {'class': 'func-a a-0', 'title': 'Called : A1'},
        '.a-1': {'class': 'func-a a-1', 'title': 'Called : A2'}
    });

    output.selectAll('.func-a').call(drawable.funcB);

    this.assertD3Nodes(output, {
        '.a-0': {'class': 'func-a a-0 func-b b-0', 'title': 'Called : A1'},
        '.a-1': {'class': 'func-a a-1 func-b b-1', 'title': 'Called : A2'}
    });
});

QUnit.test('creme.d3Drawable (methods, duplicate)', function(assert) {
    var FakeDrawable = creme.D3Drawable.sub({
        defaultProps: {
            title: 'Fake'
        },

        title: function(node, datum, i) {
            d3.select(node).text(this.prop('title'));
        }
    });

    this.assertRaises(function() {
        creme.d3Drawable({
            instance: new FakeDrawable(),
            props: ['title'],
            methods: ['title']
        });
    }, Error, 'Error: A property "title" already exists for this renderer.');
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

    assert.equal(output.selectAll('g').size(), 2);
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
                        .maxWidth(text10Width + 1)  // adds some pixels for errors depending of system fonts.
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
                        .maxWidth(text10Width + 1)  // adds some pixels for errors depending of system fonts.
                        .breakAll(true)
                        .lineHeight('1.73em'));

    this.assertD3Nodes(sketch.svg(), expected);
});

QUnit.test('creme.d3Scroll', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = sketch.svg().append('g');
    var body = chart.append('g');

    chart.attr('width', 300)
         .attr('height', 200);

    body.attr('class', 'x-scroll')
        .attr('width', 500)
        .attr('height', 200);

    var scroll = creme.d3Scroll()
                          .target(body)
                          .innerSize({width: 500});

    chart.call(scroll);

    this.assertD3Nodes(sketch.svg(), {
        '.x-scroll': {transform: 'translate(0,0)'}
    });

    body.node().dispatchEvent(new WheelEvent('wheel', {
        deltaY: 250,
        deltaMode: 1
    }));

    this.assertD3Nodes(sketch.svg(), {
        '.x-scroll': {transform: 'translate(-25,0)'}
    });
});

QUnit.parametrize('creme.d3Tooltip', [
    'c', 'n', 'ne', 'nw', 's', 'se', 'sw', 'e', 'w'
], function(direction, assert) {
    var element = $('<div>').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch().bind(element);

    var chart = sketch.svg().append('g');
    var target = chart.append('circle');

    chart.attr('width', 300)
         .attr('height', 200);

    target.attr('cx', 150)
          .attr('cy', 100)
          .attr('r', 14);

    var tooltip = creme.d3Tooltip()
                           .transition(false)
                           .direction(direction)
                           .html(function(d) { return '<h5>${text}</h5>'.template(d); })
                           .root(element.get(0));

    assert.equal(element.find('.d3-sketch-tooltip').length, 0);

    tooltip.show.bind(target.node())({text: 'Tip a Toe !'});

    var container = element.find('.d3-sketch-tooltip');

    assert.equal(container.length, 1);
    assert.equal(container.html(), '<h5>Tip a Toe !</h5>');
    assert.equal(container.css('opacity'), 1);
    assert.equal(container.is('.tip-' + direction), true);

    tooltip.hide();
    assert.equal(container.css('opacity'), 0);
});

}(jQuery));

