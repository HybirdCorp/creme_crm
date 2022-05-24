/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022  Hybird

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
        xAxisSize: 30,
        xAxisTitle: '',
        yAxisSize: 30,
        yAxisTitle: '',
        barColor: "#4682b4",
        barHilighted: "#66a2d4",
        barSelected: "#d6c2f4",
        barTextColor: "#fff",
        limits: [],
        margin: 0,
        transition: true
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
                fill: props.barColor,
                "shape-rendering": "crispEdges"
            },
            ".bar-chart .bar.selected rect": {
                fill: props.barSelected
            },
            ".bar-chart .bar text": {
                "text-anchor": "middle"
            },
            ".bar-chart .bar text.inner": {
                fill: props.barTextColor
            },
            ".bar-chart .limit": {
                stroke: "#f6c2d4",
                "z-index": 1
            }
        });
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".bar-chart");

        if (chart.size() === 0) {
            chart = svg.append('g').attr('class', 'bar-chart d3-chart');

            chart.append('g')
                    .attr('class', 'x axis')
                    .append('text')
                        .attr('class', 'axis-title')
                        .attr('text-anchor', 'end')
                        .attr('fill', 'currentColor');

            chart.append("g")
                    .attr("class", "y axis")
                    .append('text')
                        .attr('class', 'axis-title')
                        .attr('text-anchor', 'start')
                        .attr('y', 10)
                        .attr('fill', 'currentColor');

            chart.append('g').attr('class', 'bars');
            chart.append('g').attr('class', 'limits');
        }

        this._updateChart(sketch, chart, data, props);
    },

    _updateChart: function(sketch, chart, data, props) {
        var yAxisTitleSize = (props.yAxisTitle ? 20 : 0);
        var xAxisTitleSize = (props.xAxisTitle ? 20 : 0);

        var xAxisTitle = props.xAxisTitle ? '' + props.xAxisTitle + ' →' : '';
        var yAxisTitle = props.yAxisTitle ? '↑ ' + props.yAxisTitle : '';

        var bounds = creme.svgBounds(sketch.size(), {
            left: props.yAxisSize,
            bottom: props.xAxisSize + xAxisTitleSize,
            top: yAxisTitleSize
        }, props.margin);

        var xscale = d3.scaleBand().padding(0.1);
        var yscale = d3.scaleLinear();

        var ymax = d3.max(data, function(d) { return d.y; }) || 1;

        xscale.domain(data.map(function(d) { return d.x; }))
              .range([0, bounds.width], 0.1);

        yscale.domain([0, ymax])
              .range([bounds.height, 0]);

        chart.attr('transform', creme.svgTransform().translate(bounds.left, bounds.top));

        chart.selectAll('.x.axis')
                .attr('transform', creme.svgTransform().translate(0, bounds.height))
                .call(d3.axisBottom(xscale).tickSizeOuter(0));

        chart.selectAll('.x .axis-title')
                .attr('transform', creme.svgTransform().translate(bounds.width, props.xAxisSize))
                .text(xAxisTitle);

        chart.selectAll('.y.axis')
                .call(d3.axisLeft(yscale).tickSizeOuter(0));

        chart.selectAll('.y .axis-title')
                .attr('transform', creme.svgTransform().translate(-props.yAxisSize, -yAxisTitleSize))
                .text(yAxisTitle);

        var items = chart.select('.bars')
                             .selectAll('.bar')
                             .data(data);

        var context = {
            bounds: bounds,
            xscale: xscale,
            yscale: yscale,
            textformat: d3.format(",.0f")
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

        return chart;
    },

    _enterBar: function(enter, context) {
        var selection = this.selection();

        var xscale = context.xscale;
        var yscale = context.yscale;
        var textformat = context.textformat;
        var bounds = context.bounds;

        var bar = enter.append('g')
                          .attr('class', function(d) { return d.selected ? 'bar selected' : 'bar'; })
                          .attr('transform', function(d) {
                              return creme.svgTransform().translate(xscale(d.x), yscale(d.y));
                          });

        bar.append('rect')
               .attr('x', 1)
               .attr('width', xscale.bandwidth())
               .attr('height', function(d) { return bounds.height - yscale(d.y); })
               .on('click', function(d, i) { selection.select(i); });

        bar.append('text')
               .attr('dy', '.75em')
               .attr('class', function(d) { return (bounds.height - yscale(d.y)) > 15 ? 'inner' : 'outer'; })
               .attr('y', function(d) { return (bounds.height - yscale(d.y)) > 15 ? 6 : -12; })
               .attr('x', Math.ceil(xscale.bandwidth() / 2))
               .text(function(d) { return textformat(d.y); });
    },

    _updateBar: function(update, context) {
        var xscale = context.xscale;
        var yscale = context.yscale;
        var textformat = context.textformat;
        var bounds = context.bounds;

        update.attr('class', function(d) { return d.selected ? 'bar selected' : 'bar'; })
              .attr('transform', function(d) {
                  return creme.svgTransform().translate(xscale(d.x), yscale(d.y));
              });

        update.select('rect')
                .attr('width', xscale.bandwidth())
                .attr('height', function(d) { return bounds.height - yscale(d.y); });

        update.select('text')
                .attr('class', function(d) { return (bounds.height - yscale(d.y)) > 15 ? 'inner' : 'outer'; })
                .attr('y', function(d) { return (bounds.height - yscale(d.y)) > 15 ? 6 : -12; })
                .attr('x', Math.ceil(xscale.bandwidth() / 2))
                .text(function(d) { return textformat(d.y); });
    }
});

}(jQuery));
