(function($, QUnit) {
"use strict";

window.FakeD3Chart = creme.D3Chart.sub({
    defaultProps: {
        x: 3,
        y: 7,
        width: 52,
        height: 107
    },

    _draw: function(sketch, data, props) {
        var items = sketch.svg().selectAll('rect')
                                .data(data);

        items.enter()
                 .append('rect')
                     .attr('x', props.x)
                     .attr('y', function(d, i) { return props.y + i * props.height; })
                     .attr('width', props.width)
                     .attr('height', props.height)
                     .attr('fill', function(d) { return d.color; });

        items.attr('y', function(d, i) { return props.y + i * props.height; })
             .attr('fill', function(d) { return d.color; });

        items.exit().remove();
    }
});

window.QUnitSketchMixin = {
    createD3Node: function(html) {
        return d3.select($('<div>').get()[0]).html(html);
    },

    mapD3Attr: function (name, selection) {
        return selection.nodes().map(function(node) {
            return node.getAttribute(name);
        });
    },

    createD3ChartBrickHtml: function(options) {
        options = $.extend({
            data: [],
            props: {},
            header: ''
        }, options || {});

        var content;

        if (!Object.isEmpty(options.data)) {
            content = (
                '<div class="brick-header">${header}</div>' +
                '<div class="brick-d3-content"></div>' +
                '<script class="sketch-chart-data" type="application/json"><!--${data} --></script>'
            ).template({
                data: JSON.stringify(options.data),
                header: options.header
            });
        } else {
            content = '<div class="brick-d3-content brick-empty"></div>';
        }

        if (!Object.isEmpty(options.props)) {
            content += (
                '<script class="sketch-chart-props" type="application/json"><!--${props} --></script>'
            ).template({
                props: JSON.stringify(options.props)
            });
        }

        return this.createBrickHtml($.extend({
            content: content
        }, options));
    },

    createD3ChartBrick: function(options) {
        var html = this.createD3ChartBrickHtml(options);

        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return widget;
    },

    assertD3Nodes: function(svg, expected) {
        var assert = this.assert;

        Object.entries(expected).forEach(function(entry) {
            var selector = entry[0];
            var expected = entry[1];

            if (Object.isNumber(expected)) {
                assert.equal(
                    svg.selectAll(selector).size(),
                    expected,
                    'SVG element "${selector}" count should be ${expected}'.template({selector: selector, expected: expected})
                );
            } else {
                for (var attr in expected) {
                    var idx = 0;

                    svg.selectAll(selector).call(function(node) {
                        var val = Object.isFunc(node[attr]) ? node[attr].bind(node)() : node.attr(attr);

                        assert.equal(val, expected[attr], 'SVG element "${selector}"@${idx} attribute "${attr}" should be ${expected}'.template({
                            selector: selector,
                            idx: idx,
                            attr: attr,
                            expected: expected[attr]
                        }));
                    });
                }
            }
        });
    }
};

}(jQuery, QUnit));
