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

creme.D3AreaChart = creme.D3Chart.sub({
    defaultProps: {
        xaxisSize: 30,
        yaxisSize: 20,
        margin: 0,
        visible: true
    },

    _init_: function(options) {
        this._super_(creme.D3Chart, '_init_', options);
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".area-chart");

        if (chart.size() === 0) {
            chart = svg.append("g")
                           .attr('class', 'area-chart d3-chart');

            chart.append("path").attr("class", "area");
            chart.append('g').attr('class', 'x axis');
            chart.append("g").attr("class", "y axis");
        }

        chart.classed('not-visible', !props.visible);

        this._updateChart(sketch, chart, data, props);
        return this;
    },

    _updateChart: function(sketch, chart, data, props) {
        var bounds = creme.svgBounds(sketch.size(), {
            left: props.xaxisSize,
            bottom: props.yaxisSize
        }, props.margin);

        var ymax = d3.max(data, function(d) { return d.y; }) || 1;

        var xscale = d3.scaleBand()
                       .domain(data.map(function(d) { return d.x; }))
                       .rangeRound([0, bounds.width], 0.1);

        var yscale = d3.scaleLinear()
                       .domain([0, ymax])
                       .range([bounds.height, 0]);

        var area = d3.area()
                         .x(function(d) { return xscale(d.x); })
                         .y0(bounds.height)
                         .y1(function(d) { return yscale(d.y); });

        chart.attr('transform', creme.svgTransform().translate(bounds.left, bounds.top));

        chart.selectAll('.x.axis')
                .attr('transform', creme.svgTransform().translate(0, bounds.height))
                .call(d3.axisBottom(xscale).tickSizeOuter(0));

        chart.selectAll('.y.axis')
                .call(d3.axisLeft(yscale).tickSizeOuter(0));

        chart.selectAll(".area")
                 .datum(data)
                 .attr("d", area);
    }
});

}(jQuery));
