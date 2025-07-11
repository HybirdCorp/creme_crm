/* global FunctionFaker */

(function($) {

QUnit.module("creme.sketch.utils", new QUnitMixin());

QUnit.test('creme.svgTransform', function(assert) {
    var transform = creme.svgTransform();
    assert.equal('', transform.toString());

    transform.translate(5, 10);
    assert.equal('translate(5,10)', transform.toString());

    transform.scale(1.5, 1.5);
    assert.equal('translate(5,10) scale(1.5,1.5)', transform.toString());

    transform.rotate(45);
    assert.equal('translate(5,10) scale(1.5,1.5) rotate(45)', transform.toString());

    transform.scale(undefined, 12);
    assert.equal('translate(5,10) scale(1.5,1.5) rotate(45) scale(0,12)', transform.toString());
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
    assert.deepEqual(expected, creme.svgBounds.apply(null, args));
});

QUnit.test('creme.svgBounds (self)', function(assert) {
    var bounds = {width: 300, height: 200};

    bounds = creme.svgBounds(bounds, 5);
    assert.deepEqual({
        top: 5,
        left: 5,
        width: 300 - (5 * 2),
        height: 200 - (5 * 2)
    }, bounds);

    bounds = creme.svgBounds(bounds, {left: 30});
    assert.deepEqual({
        top: 5,
        left: 5 + 30,
        width: 300 - (5 * 2) - 30,
        height: 200 - (5 * 2)
    }, bounds);

    bounds = creme.svgBounds(bounds, {bottom: 8});
    assert.deepEqual({
        top: 5,
        left: 5 + 30,
        width: 300 - (5 * 2) - 30,
        height: 200 - (5 * 2) - 8
    }, bounds);
});

QUnit.test('creme.svgAsXml', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var svg = d3.select(element.get()[0]).append("svg");

    assert.equal(
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

    assert.equal(
        creme.svgAsXml(svg.node()),
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="auto" height="auto">\n' +
            $(svg.node()).html() + '\n' +
        '</svg>'
    );

    svg.attr('width', 200)
       .attr('height', 300);

    assert.equal(
        creme.svgAsXml(svg.node()),
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="300">\n' +
            $(svg.node()).html() + '\n' +
        '</svg>'
    );

    assert.equal(
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

    var done = assert.async();

    var expected = new Blob([
        '<?xml version="1.0" standalone="no"?>',
        creme.svgAsXml(svg.node())
    ], { type: "image/svg+xml;charset=utf-8" });

    setTimeout(function() {
        creme.svgAsBlob(function(blob) {
            assert.deepEqual(blob, expected);
            done();
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

    var done = assert.async();

    setTimeout(function() {
        creme.svgAsBlob(function(blob) {
            assert.equal(blob.type, 'image/png');
            done();
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
    assert.equal(creme.svgRulesAsCSS(rules), expected);
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
    assert.equal(creme.svgBoundsRadius(bounds), expected);
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

    assert.equal(selection.size(), data.length);
    assert.deepEqual(expected, creme.d3FontSize(selection));
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
        assert.ok(callbackFailure);
    }

    var done = assert.async();

    window.requestAnimationFrame(function() {
        assert.equal(observe.calls().length, expected.observe, 'ResizeObserver.observe');
        assert.equal(unobserve.calls().length, expected.unobserve, 'ResizeObserver.unobserve');
        done();
    });
});

QUnit.parametrize('creme.d3NumericDataInfo', [
    [[], {min: 0, max: 0, integer: true, gap: 0, average: 0}],
    [[0, 10, 2, 3], {min: 0, max: 10, integer: true, gap: 10, average: 3.75}],
    [[-53, 10, 2, 3], {min: -53, max: 10, integer: true, gap: 63, average: -9.5}],
    [[-53, 10.75, 10.749, 3], {min: -53, max: 10.75, integer: false, gap: 63.75, average: -7.13}]
], function(data, expected, assert) {
    var info = creme.d3NumericDataInfo(data);

    assert.deepEqual({
        min: info.min,
        max: info.max,
        integer: info.integer,
        gap: info.gap,
        average: parseFloat(info.average.toFixed(2))
    }, expected);
});

QUnit.parametrize('creme.d3NumericFormat', [
    [[0, 10, 2, 3], ['0', '10', '2', '3']],
    [[0, 100, 25, 3], ['0', '100', '25', '3']],
    [[350, 1520, 25, 4], ['350', '1.52k', '25', '4']],
    [[3350, 4420, 25, 4], ['3.35k', '4.42k', '25', '4']],
    [[7350, 5420, 25, 4], ['7.35k', '5.42k', '25', '4']],
    [[1350, 10520, 25, 4], ['1.35k', '10.5k', '25.0', '4.00']],
    [[0, 0, 1922, 6620, 5121, 12725.82, 999, 10932.75, 0, 383, 2099, 1064, 0, 0, 0, 545, 0, 0],
     ['0.00', '0.00', '1.92k', '6.62k', '5.12k', '12.7k', '999', '10.9k', '0.00', '383', '2.10k', '1.06k', '0.00', '0.00', '0.00', '545', '0.00', '0.00']
    ],
    [[0, 0, 2823, 6801.15, 3782.9, 5.9484, 2024, 1818, 0, 1250, 3158, 0, 1028, 0, 0, 0, 0, 0],
     ['0.0', '0.0', '2.8k', '6.8k', '3.8k', '5.9', '2.0k', '1.8k', '0.0', '1.3k', '3.2k', '0.0', '1.0k', '0.0', '0.0', '0.0', '0.0', '0.0']
    ],
    [[0, 0.5, 0.75, 1], ['0.00', '0.50', '0.75', '1.00']],
    [[30.78, 5.5, 2.75, 1], ['30.78', '5.50', '2.75', '1.00']],
    [[237.87, 43.5, 7.75, 104.85], ['237.87', '43.5', '7.75', '104.85']],
    [[237.87, 10043.5, 7.75, 104.85], ['238', '10.0k', '7.75', '105']],
    [[10502370.87, 65510043.5, 7.75, 10400.85], ['10.5M', '65.5M', '7.75', '10.4k']]
], function(data, expected, assert) {
    var info = creme.d3NumericDataInfo(data);
    var format = creme.d3NumericFormat(info);
    assert.deepEqual(data.map(format), expected);
});

QUnit.parametrize('creme.d3NumericAxisFormat', [
    [[0, 10, 2, 3], ['0', '10', '2', '3']],
    [[0, 100, 25, 3], ['0', '100', '25', '3']],
    [[350, 1520, 25, 4], ['350', '1.5k', '25', '4.0']],
    [[1350, 10520, 25, 4], ['1.4k', '11k', '25', '4.0']],

    [[0, 0.5, 0.75, 1], ['0.00', '0.50', '0.75', '1.00']],
    [[30.78, 5.5, 2.75, 1], ['30.78', '5.50', '2.75', '1.00']],
    [[237.87, 43.5, 7.75, 104.85], ['240', '44', '7.8', '100']],
    [[237.87, 10043.5, 7.75, 104.85], ['240', '10k', '7.8', '100']]
], function(data, expected, assert) {
    var format = creme.d3NumericAxisFormat(creme.d3NumericDataInfo(data));
    assert.deepEqual(data.map(format), expected);
});

}(jQuery));
