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
 * https://observablehq.com/@d3/mobile-patent-suits
 */
creme.D3GraphRelationChart = creme.D3Chart.sub({
    defaultProps: {
        margin: 0,
        nodeFillColor: "white",
        nodeStrokeColor: "#ccc",
        nodeStrokeSize: 2,
        nodeEdgeCountStep: 4,
        nodeSize: 10,
        nodeTextColor: "black",
        edgeColors: d3.schemeCategory10,
        maxIteration: 100,
        transition: true,
        showLegend: true,
        /*
         * TODO : This chart does not support updates so we have to disable the
         * "redraw on resize" feature for now.
         */
        drawOnResize: false
    },

    _init_: function(options) {
        this._super_(creme.D3Chart, '_init_', options);
    },

    hierarchy: function(data) {
        var relations = {};
        var nodes = {};
        var edge_counts = {};

        var edges = data.filter(function(d) { return d.relation; })
                        .map(function(d) {
                            relations[d.relation.id] = d.relation;
                            edge_counts[d.id] = (edge_counts[d.id] || 0) + 1;

                            if (d.parent) {
                                edge_counts[d.parent] = (edge_counts[d.parent] || 0) + 1;
                            }

                            return {
                                target: d.id,
                                source: d.parent,
                                data: d
                            };
                        });

        data.forEach(function(d) {
            nodes[d.id] = {
                id: d.id,
                edgeCount: edge_counts[d.id] || 0,
                data: {
                    url: d.url,
                    label: d.label
                }
            };
        });

        return {
            nodes: Object.values(nodes),
            types: Object.values(relations),
            edges: edges
        };
    },

    exportProps: function() {
        return {
            transition: false
        };
    },

    _nodeRadius: function(props) {
        return function(d) {
            return props.nodeSize + ((d.edgeCount || 0) * props.nodeEdgeCountStep);
        };
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".graphs-relation-chart");

        if (chart.size() === 0) {
            chart = svg.append("g")
                           .attr('class', 'graphs-relation-chart d3-chart');

            svg.append('g').attr('class', 'legend');
        }

        this._updateChart(sketch, chart, data, props);
        return this;
    },

    _updateChart: function(sketch, chart, data, props) {
        var svg = sketch.svg();
        var bounds = creme.svgBounds(sketch.size(), {
            left: props.xaxisSize,
            bottom: props.yaxisSize
        }, props.margin);

        var graphData = this.hierarchy(data);

        var typeColorScale = d3.scaleOrdinal(
            graphData.types.map(function(d) { return d.id; }),
            d3.schemeCategory10
        );

        var typeColor = function(d) {
            return typeColorScale(d.id);
        };

        var alphaDecay = 1.0 - Math.pow(0.001, (1.0 / props.maxIteration));

        var simulation = d3.forceSimulation()
                           .stop()
                           .nodes(graphData.nodes)
                           .alphaDecay(alphaDecay);

        simulation.force('link', d3.forceLink(graphData.edges).id(function(node) { return node.id; }))
                  .force('charge', d3.forceManyBody().strength(-400))
                  .force('center', d3.forceCenter(bounds.width / 2, bounds.height / 2))
                  // The collision force, for preventing the vertices from overlapping
                  .force('collide', d3.forceCollide().radius(70).iterations(2));

        svg.append("defs")
              .selectAll('marker')
              .data(graphData.types)
              .join('marker')
                   .attr("id", function(d) {
                       return "graphs-relation-arrow-" + d.id;
                   })
                   .attr("viewBox", "0 -5 10 10")
                   .attr("refX", 4)
                   .attr("refY", 0)
                   .attr("markerWidth", 6)
                   .attr("markerHeight", 6)
                   .attr("orient", "auto")
                   .append("path")
                       .attr("fill", typeColor)
                       .attr("d", "M0,-5L10,0L0,5");

        if (props.showLegend) {
            var legends = creme.d3LegendColumn()
                                    .swatchColor(typeColor)
                                    .swatchSize({width: 20, height: 25})
                                    .spacing(0)
                                    .text(function(d) { return d.label; })
                                    .data(graphData.types);

            sketch.svg().select('.legend').call(legends);
        }

        var link = chart.append("g")
                            .attr('class', 'graph-edges')
                            .attr("fill", "none")
                            .attr("stroke-width", 1.5)
                        .selectAll("path")
                            .data(graphData.edges)
                            .join('path')
                                .attr('class', 'graph-edge')
                                .attr("stroke", function(d) {
                                    return typeColorScale(d.data.relation.id);
                                })
                                .attr("marker-end", function(d) {
                                    return 'url(#graphs-relation-arrow-' + d.data.relation.id + ')';
                                });

        var node = chart.append("g")
                            .attr('class', 'graph-nodes')
                            .attr("fill", "currentColor")
                            .attr("stroke-linecap", "round")
                            .attr("stroke-linejoin", "round")
                        .selectAll("g")
                            .data(graphData.nodes)
                            .join('g')
                                .attr('class', 'graph-node');

        node.append("circle")
                .attr("fill", props.nodeFillColor)
                .attr("stroke", props.nodeStrokeColor)
                .attr("stroke-width", props.nodeStrokeSize)
                .attr("r", this._nodeRadius(props));

        node.append("a")
                .attr("x", 8)
                .attr("y", "0.31em")
                .attr("xlink:href", function(d) { return d.data.url; })
                .attr("target", function(d) {
                     return !d.data.url ? '_blank' : undefined;
                 })
                .append("text")
                    .attr("y", "0.31em")
                    .attr('text-anchor', 'middle')
                    .text(function(d) { return d.data.label; })
                    .attr("fill", props.nodeTextColor)
                    .clone(true)
                        .lower()
                        .attr("fill", "none")
                        .attr("stroke", "#fff")
                        .attr("stroke-width", 2);

        var zoom = d3.zoom();

        // HACK : Fix SVGLength.value property issue in tests
        // (see https://github.com/Webiks/force-horse/issues/19#issuecomment-826728521)
        zoom.extent([[0, 0], [bounds.width, bounds.height]]);
        zoom.on("zoom", function(e) {
            chart.attr("transform", e.transform);
        });

        var applyState = this._applySimulationState.bind(this);

        if (props.transition) {
            simulation.on("tick", function() {
                applyState(link, node, props);
            });

            simulation.restart();
        } else {
            simulation.tick(props.maxIteration);
            applyState(link, node, props);
        }

        svg.call(zoom)
           .call(zoom.transform, d3.zoomIdentity);

        return chart;
    },

    _applySimulationState: function(link, node, props) {
        var radius = this._nodeRadius(props);

        link.attr("d", function(d) {
            var xdiff = d.target.x - d.source.x;
            var ydiff = d.target.y - d.source.y;

            var targetRadius = radius(d.target) + 5 + (props.nodeStrokeSize / 2);

            var r = Math.hypot(xdiff, ydiff);
            var distance = Math.sqrt((xdiff * xdiff) + (ydiff * ydiff));

            var ratio = (distance - targetRadius) / distance;

            var xoffset = xdiff * ratio;
            var yoffset = ydiff * ratio;

            return 'M${source_x},${source_y}\nA${r},${r} 0 0,1 ${target_x},${target_y}'.template({
                source_x: d.source.x,
                source_y: d.source.y,
                target_x: d.source.x + xoffset,
                target_y: d.source.y + yoffset,
                r: r
            });
        });

        node.attr("transform", function(d) {
            return creme.svgTransform().translate(d.x, d.y);
        });
    }
});

}(jQuery));
