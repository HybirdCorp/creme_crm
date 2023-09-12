/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2023  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

(function($) {
"use strict";

creme.D3LineChart = creme.D3Chart.sub({
    defaultProps: {
        xAxisSize: 25,
        xAxisTitle: '',
        yAxisSize: 30,
        yAxisTitle: '',
        yAxisTickFormat: null,
        minDotInterval: 40,
        colors: "#4682b4",
        lineColors: "#4682b4",
        lineStroke: 2,
        limits: [],
        margin: 0,
        transition: true,
        visible: true,
        xScroll: null,
        overflow: false,
        showTooltip: true,
        tooltipDirection: 'n',
        tooltipHtml: function(e, d) { return d.y; },
        showDots: true,
        dotVisibility: 'unit',
        dotRadius: 5
    },

    _init_: function(options) {
        this._super_(creme.D3Chart, '_init_', options);
    },

    exportStyle: function(props) {
        return creme.svgRulesAsCSS({
            ".line-chart": {
                font: "10px sans-serif"
            },
            ".line-chart .dot": {
                "fill": "currentColor",
                "stroke-width": 0
            },
            ".line-chart .line path": {
                "fill": "none",
                "stroke-width": 1.5
            },
            ".line-chart .limit": {
                stroke: "#f6c2d4",
                "z-index": 1
            }
        });
    },

    exportProps: function() {
        return {
            transition: false,
            drawOnResize: false,
            xScroll: false,
            overflow: true,
            showTooltip: false,
            dotVisibility: 'always',
            isExport: true
        };
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".line-chart");

        if (chart.size() === 0) {
            chart = svg.append('g').attr('class', 'line-chart d3-chart');
            this._setupChart(sketch, chart, props);
        }

        chart.classed('not-visible', !props.visible);

        this._updateChart(sketch, chart, data, props);
    },

    chartData: function(data) {
        return data.map(function(d, i) {
            return {
                index: i,
                x: d.x,
                y: d.y,
                color: d.color,
                data: d
            };
        });
    },

    _setupChart: function(sketch, chart, props) {
        var body = chart.append('g').attr('class', 'x-scroll-body');
        body.append('g').attr('class', 'x axis');
        body.append('g').attr('class', 'lines');

        chart.append('g').attr('class', 'limits');
        chart.append("g").attr("class", "y axis");

        this.scroll = creme.d3Scroll().target(body);
    },

    _updateChart: function(sketch, chart, data, props) {
        var bounds = creme.svgBounds(sketch.size(), props.margin);
        var xScroll = props.xScroll;
        var overflow = props.overflow;

        data = this.chartData(data);
        var yDataInfo = creme.d3NumericDataInfo(data, function(d) { return d.y; });

        var ymax = yDataInfo.max || 1;
        var yAxisFontSize = creme.d3FontSize(chart.select('.y.axis'));
        var yAxisTickFormat = props.yAxisTickFormat || creme.d3NumericAxisFormat(yDataInfo);

        // 2em height for the title
        var yAxisTitleHeight = yAxisFontSize * 2;

        // 6px tick line + 3em width for the label
        var yAxisSize = Math.max(props.yAxisSize, 6 + (yAxisFontSize * 3));

        var colorize = creme.d3Colorize()
                                .scale(d3.scaleOrdinal()
                                             .domain([0, data.length])
                                             .range(creme.d3ColorRange(props.colors, {size: data.length})));

        var lineColors = d3.scaleOrdinal()
                                .domain([0, data.length])
                                .range(creme.d3ColorRange(props.lineColors, {size: data.length}));

        data = colorize(data);

        chart.attr('transform', creme.svgTransform().translate(bounds.left, bounds.top));

        bounds = creme.svgBounds(bounds, {left: yAxisSize});

        // Guess if scrolling is needed : min bar width * bar number > bounds
        if (xScroll === null) {
            xScroll = Boolean(props.minDotInterval * data.length > bounds.width);
            overflow = xScroll;
        }

        var xAxisWidth = overflow ? Math.max(props.minDotInterval * data.length, bounds.width) : bounds.width;

        chart.classed('x-scroll', xScroll);

        var xscale = d3.scalePoint()
                            .domain(data.map(function(d) { return d.x; }))
                            .range([0, xAxisWidth - (props.minDotInterval * 0.6) - 3])
                            .round(true)
                            .padding(0.1)
                            .align(0.5);

        chart.select('.x.axis')
                .call(creme.d3BottomAxis()
                                .scale(xscale)
                                .minHeight(props.xAxisSize)
                                .tickWrapWidth(xscale.step())
                                .label(props.xAxisTitle))
                .attr('transform', function() {
                    return creme.svgTransform().translate(
                        yAxisSize - 1,
                        bounds.height - Math.floor(this.getBBox().height)
                    );
                });

        // Re-calculate bounds with the X-axis height AFTER text wrap
        var xAxisHeight = Math.floor(chart.select('.x.axis').node().getBBox().height);

        bounds = creme.svgBounds(bounds, {
            bottom: xAxisHeight,
            top: yAxisTitleHeight
        });

        var yscale = d3.scaleLinear();
        yscale.domain([0, ymax])
              .range([bounds.height, 0]);

        chart.selectAll('.y.axis')
                  .attr('transform', creme.svgTransform().translate(yAxisSize, yAxisTitleHeight))
                  .call(creme.d3LeftAxis()
                                  .fill(overflow ? '#fff' : 'none')
                                  .scale(yscale)
                                  .tickFormat(yAxisTickFormat)
                                  .ticks(yDataInfo.integer ? Math.min(yDataInfo.gap, 8) : 8)
                                  .label(props.yAxisTitle));

        var linepath;

        if (data.length === 1) {
            // With a single value we cannot build a path. So we build an horizontal path from 0 to max width.
            linepath = function(data) {
                var posy = yscale(data[0].y);
                var posx = xscale(data[0].x);
                return 'M0,0C' + [0, posy, posx, posy, xAxisWidth - (props.minDotInterval * 0.6) - 3, posy].join(',');
            };
        } else {
            linepath = d3.line()
                            .curve(d3.curveMonotoneX)  // Just add that to have a curve instead of segments
                            .x(function(d) { return xscale(d.x); })
                            .y(function(d) { return yscale(d.y); });
        }

        var context = {
            props: props,
            bounds: bounds,
            xscale: xscale,
            yscale: yscale,
            linepath: linepath,
            lineColors: lineColors
        };

        if (props.showTooltip) {
            context.tooltip = creme.d3Tooltip()
                                        .direction(props.tooltipDirection)
                                        .on('show', function(e, d) {
                                            e.container
                                                 .style('background', d.color)
                                                 .style('color', d.textColor);
                                        })
                                        .html(props.tooltipHtml);
        }

        var lines = chart.select('.lines')
                             .attr('transform', creme.svgTransform().translate(yAxisSize, yAxisTitleHeight))
                             .selectAll('.line')
                                .data([data]);

        this._enterLine(lines.enter(), context);
        this._updateLine(props.transition ? lines.transition() : lines, context);
        lines.exit().remove();

        if (props.showDots) {
            if (props.dotVisibility === 'unit') {
                // Retrieve position of the mouse within abscissa axis and hilight the according
                // dot.
                var scale = xscale.invert ? xscale : d3.scaleLinear([0, data.length], xscale.range());
                var node = chart.select('.lines').node();

                chart.select('.lines')
                         .attr('pointer-events', 'bounding-box')
                         .on('mousemove', function(e) {
                             var rect = node.getBoundingClientRect();
                             var pos = Math.floor(scale.invert(e.clientX - rect.left - node.clientLeft));

                             chart.selectAll('.dot').each(function(d, index) {
                                 d3.select(this).classed('dot-unit-hilight', index === pos);
                             });
                         })
                         .on('mouseleave', function(e) {
                             chart.selectAll('.dot').classed('dot-unit-hilight', false);
                         });
            }

            var dots = lines.selectAll('.dot')
                                 .data(function(d) { return d; });

            this._enterDot(dots.enter(), context);
            this._updateDot(props.transition ? dots.transition() : dots, context);
            dots.exit().remove();
        }

        if (props.limits) {
            var limits = creme.d3LimitStack()
                                    .bounds(bounds)
                                    .scale(yscale)
                                    .data(props.limits);

            chart.select('.limits').call(limits);
        }

        this.scroll.bounds(bounds)
                   .disabled(!xScroll)
                   .innerSize({width: xAxisWidth});

        sketch.svg().call(this.scroll);

        return chart;
    },

    _enterLine: function(enter, context) {
        var props = context.props;
        var line = enter.append('g')
                            .attr('class', 'line');

        line.append('path')
                .datum(function(d) { return d; })
                .attr("fill", "none")
                .attr("stroke", function(d, i) { return context.lineColors(i); })
                .attr("stroke-width", props.lineStroke)
                .attr("d", context.linepath);

        if (props.showDots) {
            var dots = line.selectAll('.dot')
                               .data(function(d) { return d; });

            this._enterDot(dots.enter(), context);
        }

        return enter;
    },

    _updateLine: function(update, context) {
        update.select('path')
                  .attr("d", context.linepath);
    },

    _enterDot: function(enter, context) {
        var selection = this.selection();
        var props = context.props;
        var dot = enter.append('circle')
                           .attr('color', function(d) { return d.color; })
                           .attr('cx', function(d) { return context.xscale(d.x); })
                           .attr('cy', function(d) { return context.yscale(d.y); })
                           .attr('class', ['dot', 'dot-' + props.dotVisibility].join(' '))
                           .attr('r', props.dotRadius)
                           .attr('stroke', function(d) {
                               // Use the color of the line as stroke color.
                               return d3.select(this.parentNode.querySelector('path')).attr('stroke');
                           });

        dot.on('click', function(e, d) { selection.select(d.index); });

        if (context.tooltip) {
             dot.on('mouseenter', context.tooltip.show)
                .on('mouseleave', context.tooltip.hide);
        };
    },

    _updateDot: function(update, context) {
        var props = context.props;

        update.attr('fill', function(d) { return d.color; })
              .attr('cx', function(d) { return context.xscale(d.x); })
              .attr('cy', function(d) { return context.yscale(d.y); })
              .attr('class', ['dot', 'dot-' + props.dotVisibility].join(' '))
              .attr('r', props.dotRadius);
    }
});

}(jQuery));
