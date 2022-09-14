/* global FunctionFaker */

(function($) {

QUnit.module("creme.sketch.utils", new QUnitMixin());

QUnit.test('creme.svgTransform', function(assert) {
    var transform = creme.svgTransform();
    equal('', transform.toString());

    transform.translate(5, 10);
    equal('translate(5,10)', transform.toString());

    transform.scale(1.5, 1.5);
    equal('translate(5,10) scale(1.5,1.5)', transform.toString());

    transform.rotate(45);
    equal('translate(5,10) scale(1.5,1.5) rotate(45)', transform.toString());

    transform.scale(undefined, 12);
    equal('translate(5,10) scale(1.5,1.5) rotate(45) scale(0,12)', transform.toString());
});

QUnit.parametrize('creme.svgBounds', [
    [
        [],
        {top: 0, left: 0, width: 0, height: 0}
    ],
    [
        [{width: 20, height: 25}],
        {top: 0, left: 0, width: 20, height: 25}
    ],
    [
        [{width: 20, height: 25}, 3],
        {top: 3, left: 3, width: 20 - (3 + 3), height: 25 - (3 + 3)}
    ],
    [
        [{width: 20, height: 25}, {top: 5, bottom: 8, left: 3}],
        {top: 5, left: 3, width: 20 - 3, height: 25 - (5 + 8)}
    ],
    [
        [{width: 20, height: 25}, {top: 5, bottom: 8, left: 3, right: 2}],
        {top: 5, left: 3, width: 20 - (3 + 2), height: 25 - (5 + 8)}
    ],
    [
        [{width: 20, height: 25}, {top: 5, bottom: 80, left: 33, right: 2}],
        {top: 5, left: 33, width: 0, height: 0}
    ],
    [
        [{width: 20, height: 25}, {top: 5, bottom: 8, left: 3}, {top: 7, right: 6}],
        {top: 5 + 7, left: 3, width: 20 - (3 + 6), height: 25 - (5 + 7 + 8)}
    ],
    [
        [{width: 20, height: 25}, 3, 2],
        {top: 5, left: 5, width: 20 - 10, height: 25 - 10}
    ]
], function(args, expected, assert) {
    deepEqual(expected, creme.svgBounds.apply(null, args));
});

QUnit.test('creme.svgBounds (self)', function(assert) {
    var bounds = {width: 300, height: 200};

    bounds = creme.svgBounds(bounds, 5);
    deepEqual({
        top: 5,
        left: 5,
        width: 300 - (5 * 2),
        height: 200 - (5 * 2)
    }, bounds);

    bounds = creme.svgBounds(bounds, {left: 30});
    deepEqual({
        top: 5,
        left: 5 + 30,
        width: 300 - (5 * 2) - 30,
        height: 200 - (5 * 2)
    }, bounds);

    bounds = creme.svgBounds(bounds, {bottom: 8});
    deepEqual({
        top: 5,
        left: 5 + 30,
        width: 300 - (5 * 2) - 30,
        height: 200 - (5 * 2) - 8
    }, bounds);
});

QUnit.test('creme.svgAsXml', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var svg = d3.select(element.get()[0]).append("svg");

    equal(
        creme.svgAsXml(svg.node()),
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="auto" height="auto">\n' +
        '\n' +
        '</svg>'
    );

    svg.append('rect')
           .attr('x', 1)
           .attr('y', 10)
           .attr('width', 30)
           .attr('height', 20)
           .attr('fill', 'red');

    equal(
        creme.svgAsXml(svg.node()),
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="auto" height="auto">\n' +
            $(svg.node()).html() + '\n' +
        '</svg>'
    );

    svg.attr('width', 200)
       .attr('height', 300);

    equal(
        creme.svgAsXml(svg.node()),
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="300">\n' +
            $(svg.node()).html() + '\n' +
        '</svg>'
    );

    equal(
        creme.svgAsXml(svg.node(), {width: 125, height: 333}),
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="125" height="333">\n' +
            $(svg.node()).html() + '\n' +
        '</svg>'
    );
});

QUnit.test('creme.svgAsBlob', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var svg = d3.select(element.get()[0]).append("svg");

    svg.attr('width', 200).attr('height', 300);
    svg.append('rect')
           .attr('x', 10)
           .attr('y', 10)
           .attr('width', 20)
           .attr('height', 20)
           .attr('fill', 'red');

    stop(1);

    var expected = new Blob([
        '<?xml version="1.0" standalone="no"?>',
        creme.svgAsXml(svg.node())
    ], { type: "image/svg+xml;charset=utf-8" });

    setTimeout(function() {
        creme.svgAsBlob(function(blob) {
            deepEqual(blob, expected);
            start();
        }, svg.node());
    });
});

QUnit.test('creme.svgAsBlob (png)', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var svg = d3.select(element.get()[0]).append("svg");

    svg.attr('width', 200).attr('height', 300);
    svg.append('rect')
           .attr('x', 10)
           .attr('y', 10)
           .attr('width', 20)
           .attr('height', 20)
           .attr('fill', 'red');

    stop(1);

    setTimeout(function() {
        creme.svgAsBlob(function(blob) {
            equal(blob.type, 'image/png');
            start();
        }, svg.node(), {encoderType: 'image/png'});
    });
});

QUnit.parametrize('creme.svgCSSRulesAsText', [
    [{}, ''],
    [{
        '.bar': 'font-size: 12px',
        '.bar rect': {
            fill: '#1255ff',
            'z-index': 12
        }
    }, '.bar { font-size: 12px; }\n.bar rect { fill: #1255ff; z-index: 12; }']
], function(rules, expected, assert) {
    equal(creme.svgRulesAsCSS(rules), expected);
});

QUnit.parametrize('creme.svgCSSRulesAsText (invalid)', [
    [{'': {}}, 'Error: CSS selector must be a non empty string']
], function(rules, expected, assert) {
    this.assertRaises(function() {
        creme.svgRulesAsCSS(rules);
    }, Error, expected);
});

QUnit.parametrize('creme.svgBoundsRadius', [
    [{}, 0],
    [{width: 10}, 0],
    [{width: 10, height: 20}, 5],
    [{width: 24, height: 20}, 10]
], function(bounds, expected, assert) {
    equal(creme.svgBoundsRadius(bounds), expected);
});

QUnit.parametrize('creme.d3FontSize', [
    [[], 0],
    [[''], 10],
    [['8px', '', '2.1em'], [8, 10, 21]]
], function(data, expected, assert) {
    var element = $('<svg width="100" height="100" style="font-size:10px;">').appendTo(this.qunitFixture());
    var svg = d3.select(element.get(0));

    svg.selectAll('text')
           .data(data)
           .enter()
               .append('text')
                   .style('font-size', function(d) { return d; });

    var selection = svg.selectAll('text');

    equal(selection.size(), data.length);
    deepEqual(expected, creme.d3FontSize(selection));
});

QUnit.parametrize('creme.d3PreventResizeObserverLoop', [
    false, true
], {
    'no size change': [{width: 100, height: 100}, {width: 100, height: 100}, {unobserve: 0, observe: 0}],
    'width change': [{width: 100, height: 100}, {width: 200, height: 100}, {unobserve: 1, observe: 1}],
    'height change': [{width: 100, height: 100}, {width: 100, height: 200}, {unobserve: 1, observe: 1}]
}, function(callbackFailure, prevSize, nextSize, expected, assert) {
    var element = $('<div>').css(prevSize).appendTo(this.qunitFixture());
    var target = element.get(0);
    var callback = function() {
        target.style.width = '' + nextSize.width + 'px';
        target.style.height = '' + nextSize.height + 'px';

        if (callbackFailure) {
            throw new Error('ResizeObservable callback failure');
        }
    };

    var trigger = creme.d3PreventResizeObserverLoop(callback);

    var observe = new FunctionFaker();
    var unobserve = new FunctionFaker();

    var observer = {
        observe: observe.wrap(),
        unobserve: unobserve.wrap()
    };

    try {
        trigger([{target: target}], observer);
    } catch (e) {
        ok(callbackFailure);
    }

    window.requestAnimationFrame(function() {
        equal(observe.calls().length, expected.observe, 'ResizeObserver.observe');
        equal(unobserve.calls().length, expected.unobserve, 'ResizeObserver.unobserve');
        start();
    });

    stop(1);
});

}(jQuery));
