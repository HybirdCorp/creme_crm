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

creme.D3DonutChart = creme.D3Chart.sub({
    defaultProps: {
        band: 60,
        margin: 0,
        colors: null,
        showLegend: true,
        transition: true
    },

    _init_: function(options) {
        this._super_(creme.D3Chart, '_init_', options);
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".donut-chart");

        if (chart.size() === 0) {
            chart = svg.append("g")
                           .attr('class', 'donut-chart d3-chart');

            chart.append('g').attr('class', 'slices');
            svg.append('g').attr('class', 'legend');
        }

        this._updateChart(sketch, chart, data, props);
        return this;
    },

    _updateChart: function(sketch, chart, data, props) {
        var bounds = creme.svgBounds(sketch.size(), props.margin, {
            left: props.showLegend ? props.legendSize : 0
        });
        var radius = creme.svgBoundsRadius(bounds);
        var colors = props.colors || d3.quantize(function(t) {
            return d3.interpolateSpectral(t * 0.8 + 0.1);
        }, data.length);

        var xkeys = Array.from(new Set(data.map(function(d) { return d.x; })));

        var colorScale;

        if (Array.isArray(colors)) {
            colorScale = d3.scaleOrdinal()
                               .domain([0, data.length])
                               .range(colors);
        } else {
            colorScale = Object.isFunc(colors) ? colors : function() { return props.colors; };
        }

        var arcpath = d3.arc()
                        .innerRadius(Math.max(0, radius - props.band))
                        .outerRadius(radius);

        var pielayout = d3.pie()
                          .sort(null)
                          .value(function(d) { return d.y; });

        chart.attr("transform", creme.svgTransform().translate(bounds.width / 2, bounds.height / 2));

        var items = chart.select('.slices')
                             .selectAll('.slice')
                             .data(pielayout(data));

        if (props.showLegend) {
            var legends = creme.d3LegendColumn()
                                    .swatchColor(colorScale)
                                    .swatchSize({width: 20, height: 25})
                                    .spacing(0)
                                    .data(xkeys.sort());

            sketch.svg().select('.legend').call(legends);
        }

        var context = {
            arcpath: arcpath,
            colorScale: colorScale,
            formatValue: d3.format(',.0f'),
            transition: props.transition
        };

        this._enterItem(items.enter(), context);
        this._updateItem(props.transition ? items.transition() : items, context);
        items.exit().remove();

        return chart;
    },

    _enterItem: function(item, context) {
        var selection = this.selection();

        var arcpath = context.arcpath;
        var colorScale = context.colorScale;
        var formatValue = context.formatValue;

        var arc = item.append('g')
                         .attr('class', function(d) { return d.data.selected ? 'slice selected' : 'slice'; });

        arc.append("path")
               .attr('d', arcpath)
               .attr("fill", function(d) { return colorScale(d.data.x); })
               .on('click', function(d, i) { selection.select(i); });

        arc.append("text")
               .attr("dy", ".35em")
               .style("text-anchor", "middle")
               .text(function(d) { return formatValue(d.data.y); })
               .attr("transform", function(d) {
                    var pos = arcpath.centroid(d);
                    return creme.svgTransform().translate(pos[0], pos[1]);
                })
               .on('click', function(d, i) { selection.select(i); });
    },

    _updateItem: function(item, context) {
        var arcpath = context.arcpath;
        var colorScale = context.colorScale;
        var formatValue = context.formatValue;

        function arcTween(d) {
            this._current = this._current || d;
            var interpolate = d3.interpolate(this._current, d);
            this._current = interpolate(0);
            return function(t) {
                return arcpath(interpolate(t));
            };
        };

        item.attr('class', function(d) { return d.data.selected ? 'slice selected' : 'slice'; });

        if (context.transition) {
            item.select('path').attrTween("d", arcTween);
        } else {
            item.select('path').attr("d", arcpath);
        }

        item.select('path')
                .attr("fill", function(d) { return colorScale(d.data.x); });

        item.select("text")
                .text(function(d) { return formatValue(d.data.y); })
                .attr("transform", function(d) {
                    var pos = arcpath.centroid(d);
                    return creme.svgTransform().translate(pos[0], pos[1]);
                });
    }
});

}(jQuery));
