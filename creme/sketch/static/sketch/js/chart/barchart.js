/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022-2023  Hybird

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

creme.D3BarChart = creme.D3Chart.sub({
    defaultProps: {
        xAxisSize: 25,
        xAxisTitle: '',
        yAxisSize: 30,
        yAxisTitle: '',
        yAxisTickFormat: null,
        barMinWidth: 60,
        colors: "#4682b4",
        barTextFormat: null,
        limits: [],
        margin: 0,
        transition: true,
        visible: true,
        xScroll: null,
        overflow: false
    },

    _init_: function(options) {
        this._super_(creme.D3Chart, '_init_', options);
    },

    exportStyle: function(props) {
        return creme.svgRulesAsCSS({
            ".bar-chart": {
                font: "10px sans-serif"
            },
            ".bar-chart .bar rect": {
                "shape-rendering": "crispedges"
            },
            ".bar-chart .bar.selected rect": {
                "opacity": "0.8"
            },
            ".bar-chart .bar text": {
                "text-anchor": "middle"
            },
            ".bar-chart .bar text.inner.dark-bg": {
                "font-weight": 600
            },
            ".bar-chart .bar text.outer": {
                "fill": "black"
            },
            ".bar-chart .limit": {
                stroke: "#f6c2d4",
                "z-index": 1
            }
        });
    },

    exportOptions: function(data, options, props) {
        if (props.overflow) {
            var margin = props.margin ? props.margin.left + props.margin.right : 0;
            var width = (data.length * props.barMinWidth) + props.yAxisSize + margin;

            return {
                width: Math.max(width, options.width || 0)
            };
        }

        return {};
    },

    exportProps: function() {
        return {
            transition: false,
            drawOnResize: false,
            xScroll: false,
            overflow: true
        };
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".bar-chart");

        if (chart.size() === 0) {
            chart = svg.append('g').attr('class', 'bar-chart d3-chart');
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
        body.append('g').attr('class', 'bars');

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
        var barTextFormat = props.barTextFormat || creme.d3NumericFormat(yDataInfo);
        var yAxisTickFormat = props.yAxisTickFormat || creme.d3NumericAxisFormat(yDataInfo);

        // 2em height for the title
        var yAxisTitleHeight = yAxisFontSize * 2;

        // 6px tick line + 3em width for the label
        var yAxisSize = Math.max(props.yAxisSize, 6 + (yAxisFontSize * 3));

        var colorize = creme.d3Colorize()
                                .scale(d3.scaleOrdinal()
                                             .domain([0, data.length])
                                             .range(creme.d3ColorRange(props.colors, {size: data.length})));

        data = colorize(data);

        chart.attr('transform', creme.svgTransform().translate(bounds.left, bounds.top));

        bounds = creme.svgBounds(bounds, {left: yAxisSize});

        // Guess if scrolling is needed : min bar width * bar number > bounds
        if (xScroll === null) {
            xScroll = Boolean(props.barMinWidth * data.length > bounds.width);
            overflow = xScroll;
        }

        var xAxisWidth = overflow ? Math.max(props.barMinWidth * data.length, bounds.width) : bounds.width;

        chart.classed('x-scroll', xScroll);

        var xscale = d3.scaleBand()
                            .domain(data.map(function(d) { return d.x; }))
                            .range([0, xAxisWidth], 0.1)
                            .padding(0.1);

        chart.select('.x.axis')
                .call(creme.d3BottomAxis()
                                .scale(xscale)
                                .minHeight(props.xAxisSize)
                                .tickWrapWidth(xscale.bandwidth())
                                .label(props.xAxisTitle))
                .attr('transform', function() {
                    return creme.svgTransform().translate(
                        yAxisSize,
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
                                  .fill('#fff')
                                  .scale(yscale)
                                  .tickFormat(yAxisTickFormat)
                                  .ticks(yDataInfo.integer ? Math.min(yDataInfo.gap, 8) : 8)
                                  .label(props.yAxisTitle));

        var items = chart.select('.bars')
                             .attr('transform', creme.svgTransform().translate(yAxisSize, yAxisTitleHeight))
                             .selectAll('.bar')
                             .data(data);

        var context = {
            bounds: bounds,
            xscale: xscale,
            yscale: yscale,
            textformat: barTextFormat
        };

        this._enterBar(items.enter(), context);
        this._updateBar(props.transition ? items.transition() : items, context);
        items.exit().remove();

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

    _enterBar: function(enter, context) {
        var selection = this.selection();

        var xscale = context.xscale;
        var yscale = context.yscale;
        var textformat = context.textformat;
        var bounds = context.bounds;

        function isInnerText(d) {
            return (bounds.height - yscale(d.y)) > 15;
        }

        var bar = enter.append('g')
                          .attr('class', 'bar')
                          .classed('selected', function(d) { return d.data.selected; })
                          .attr('transform', function(d) {
                              return creme.svgTransform().translate(xscale(d.x), yscale(d.y));
                          });

        bar.append('rect')
               .attr('x', 1)
               .attr('width', xscale.bandwidth())
               .attr('height', function(d) { return bounds.height - yscale(d.y); })
               .attr("fill", function(d) { return d.color; })
               .on('click', function(e, d) { selection.select(d.index); });

        bar.append('text')
               .classed('dark-bg', function(d) { return d.isDarkColor; })
               .attr('dy', '.75em')
               .attr('class', function(d) {
                   return isInnerText(d) ? (d.isDarkColor ? 'inner dark-bg' : 'inner') : 'outer';
               })
               .attr('fill', function(d) { return d.textColor; })
               .attr('y', function(d) { return isInnerText(d) ? 6 : -12; })
               .attr('x', Math.ceil(xscale.bandwidth() / 2))
               .text(function(d) { return textformat(d.y); });
    },

    _updateBar: function(update, context) {
        var xscale = context.xscale;
        var yscale = context.yscale;
        var textformat = context.textformat;
        var bounds = context.bounds;

        function isInnerText(d) {
            return (bounds.height - yscale(d.y)) > 15;
        }

        update.selection().classed('selected', function(d) { return d.data.selected; });

        update.attr('transform', function(d) {
                  return creme.svgTransform().translate(xscale(d.x), yscale(d.y));
              });

        update.select('rect')
                .attr("fill", function(d) { return d.color; })
                .attr('width', xscale.bandwidth())
                .attr('height', function(d) { return bounds.height - yscale(d.y); });

        update.select('text')
                .attr('class', function(d) {
                    return isInnerText(d) ? (d.isDarkColor ? 'inner dark-bg' : 'inner') : 'outer';
                })
                .attr('fill', function(d) { return d.textColor; })
                .attr('y', function(d) { return isInnerText(d) ? 6 : -12; })
                .attr('x', Math.ceil(xscale.bandwidth() / 2))
                .text(function(d) { return textformat(d.y); });
    }
});

}(jQuery));
