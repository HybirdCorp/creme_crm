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

/*
 * Inspired by the work of Mike Bostock

 * Copyright 2022 Observable, Inc.
 * Released under the ISC license.
 * https://observablehq.com/@d3/radial-tree
 */
creme.D3RadialTreeChart = creme.D3Chart.sub({
    defaultProps: {
        margin: 0
    },

    _init_: function(options) {
        this._super_(creme.D3Chart, '_init_', options);
    },

    hierarchy: function(data) {
        var stratify = d3.stratify()
                         .id(function(d) { return d.id; })
                         .parentId(function(d) { return d.parent; });;

        var roots = data.filter(function(d) { return !d.parent; });

        if (roots.length > 1) {
            roots.forEach(function(d) {
                d.parent = 'radialtree-root';
            });

            data.push({
                id: 'radialtree-root'
            });
        }

        return stratify(data);
    },

    _draw: function(sketch, data) {
        var props = this.props();
        var svg = sketch.svg();
        var bounds = creme.svgBounds(sketch.size(), {
            left: props.xaxisSize,
            bottom: props.yaxisSize
        }, props.margin);

        var radius = creme.svgBoundsRadius(bounds);

        var treelayout = d3.tree()
                           .size([2 * Math.PI, radius])
                           .separation(function(a, b) {
                               return (a.parent === b.parent ? 1 : 2) / a.depth;
                           });

        var linkpath = d3.linkRadial()
                         .angle(function(d) { return d.x; })
                         .radius(function(d) { return d.y; });

        // Prepare data structure
        var treeData = this.hierarchy(data);

        // Compute the tree layout
        treelayout(treeData);

        var chart = svg.append("g")
                           .attr('class', 'radialtree-chart d3-chart')
                           .attr("transform", creme.svgTransform().translate(bounds.width / 2, bounds.height / 2));

        chart.append("g")
                 .attr("fill", "none")
                 .attr("stroke", "#555")
                 .attr("stroke-opacity", 0.4)
                 .attr("stroke-width", 1.4)
                 .selectAll("path")
                     .data(treelayout.links())
                     .join("path")
                         .attr("d", linkpath);

        var node = chart.append("g")
                           .selectAll("a")
                           .data(treeData.descendants())
                           .join("a")
                               .attr("xlink:href", function(d) {
                                   return d.data.url;
                                })
                               .attr("target", function(d) {
                                   return !d.data.url ? '_blank' : undefined;
                                })
                               .attr("transform", function(d) {
                                   return creme.svgTransform()
                                                   .rotate(d.x * 180 / Math.PI - 90)
                                                   .translate(d.y, 0);
                               });

        node.append("circle")
                .attr("fill", function(d) {
                    return d.children ? "#555" : "#999";
                 })
                .attr("r", 3);

        var descendantLabels = treeData.descendants().map(function(d) {
            return d.data.label;
        });

        if (descendantLabels) {
            node.append("text")
                    .attr("transform", function(d) {
                        return creme.svgTransform().rotate(d.x >= Math.PI ? 180 : 0);
                    })
                    .attr("dy", "0.32em")
                    .attr("x", function(d) {
                        return (d.x < Math.PI) === !d.children ? 6 : -6;
                    })
                    .attr("text-anchor", function(d) {
                        return (d.x < Math.PI) === !d.children ? "start" : "end";
                    })
                    .attr("paint-order", "stroke")
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 3)
                    .text(function(d, i) {
                        return descendantLabels[i];
                    });
        }

        return chart;
    }
});

}(jQuery));

