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

creme.D3TextWrap = creme.D3Drawable.sub({
    defaultProps: {
        lineHeight: '1.2em',
        maxWidth: 0
    },

    draw: function(node, datum, i) {
        var props = this.props();

        var computedWidth = node.getComputedTextLength();
        var expectedWidth = Object.isFunc(props.maxWidth) ? props.maxWidth.bind(node)(datum, i) : props.maxWidth;
        var lineHeight = props.lineHeight;

        if (computedWidth <= expectedWidth) {
            return;
        }

        var text = d3.select(node);
        var words = text.text().split(/\s+/);

        if (words.length < 2) {
            return;
        }

        var avgCharSize = (computedWidth / text.text().length);
        var lines = [];
        var line = words.shift();
        var word = words.shift();

        while (word) {
            var next = line + ' ' + word;

            if (next.length * avgCharSize > expectedWidth) {
                lines.push(line);
                line = word;
            } else {
                line = next;
            }

            word = words.shift();
        }

        lines.push(line);

        text.text("")
            .selectAll("tspan")
            .data(lines)
                .join("tspan")
                    .text(function(d) { return d; })
                    .attr("x", 0)
                    .attr("dy", function(d, i) {
                        return i === 0 ? null : lineHeight;
                     });
    }
});

creme.d3TextWrap = function(options) {
    return creme.d3Drawable({
        instance: new creme.D3TextWrap(options),
        props: ['lineHeight', 'maxWidth']
    });
};

}(jQuery));
