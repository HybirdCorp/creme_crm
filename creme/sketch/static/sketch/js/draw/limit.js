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

creme.D3LimitStack = creme.D3Drawable.sub({
    defaultProps: {
        zIndex: 1,
        data: [],
        bounds: {top: 0, left: 0, width: 0, height: 0},
        label: function(d, i) { return d; },
        help: function(d, i) { return d; },
        scale: function(d, i) { return d; },
        color: '#000'
    },

    draw: function(node, datum, i) {
        var props = this.props();

        function position(d, i) {
           return creme.svgTransform().translate(
               0, props.scale(d)
           );
        }

        var limits = d3.select(node).selectAll('.limit').data(props.data || []);

        limits.enter()
              .append('line')
                  .attr('class', 'limit')
                  .attr('z-index', props.zIndex)
                  .attr('x2', props.bounds.width)
                  .attr('transform', position)
                  .attr('title', props.help)
                  .attr('fill', props.color);

        limits.attr('transform', position)
              .attr('title', props.help)
              .attr('fill', props.color);

        limits.exit().remove();
    }
});

creme.d3LimitStack = function(options) {
    return creme.d3Drawable({
        instance: new creme.D3LimitStack(options),
        props: ['label', 'help', 'zIndex', 'bounds', 'data', 'scale', 'color']
    });
};

}(jQuery));
