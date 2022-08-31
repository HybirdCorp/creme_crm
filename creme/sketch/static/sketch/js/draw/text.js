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
        maxWidth: 0,
        wordBreakSeparator: '-',
        breakAll: false
    },

    breakWord: function(text, props) {
        var node = text.node();
        var computedWidth = node.getComputedTextLength();
        var avgCharSize = (computedWidth / text.text().length);

        var words = text.text().split(/\s+/);
        var lines = [];
        var line = words.shift();

        words.forEach(function(word) {
            var next = line + ' ' + word;

            if (next.length * avgCharSize > props.maxWidth) {
                lines.push(line);
                line = word;
            } else {
                line = next;
            }
        });

        lines.push(line);
        return lines;
    },

    breakAll: function(text, props) {
        var node = text.node();
        var computedWidth = node.getComputedTextLength();
        var avgCharSize = (computedWidth / text.text().length);
        var maxWordLength = Math.ceil(props.maxWidth / avgCharSize) - props.wordBreakSeparator.length;

        var lines = [];
        var words = text.text().split(/\s+/);
        var line = '';

        words.forEach(function(word) {
            if (word.length > maxWordLength) {
                if (line) {
                    lines.push(line);
                }

                line = word;

                while (line.length > maxWordLength) {
                    lines.push(line.substring(0, maxWordLength) + props.wordBreakSeparator);
                    line = line.substring(maxWordLength);
                }
            } else if (line) {
                var next = line + ' ' + word;

                if (next.length * avgCharSize > props.maxWidth) {
                    lines.push(line);
                    line = word;
                } else {
                    line = next;
                }
            } else {
                line = word;
            }
        });

        lines.push(line);
        return lines;
    },

    draw: function(node, datum, i) {
        var props = this.props();
        var text = d3.select(node);
        var lines = props.breakAll ? this.breakAll(text, props) : this.breakWord(text, props);

        if (lines.length > 1) {
            text.text("")
                .selectAll("tspan")
                   .data(lines)
                   .join("tspan")
                       .text(function(d) { return d; })
                       .attr("x", 0)
                       .attr("dy", function(d, i) {
                           return i === 0 ? null : props.lineHeight;
                       });
        }
    }
});

creme.d3TextWrap = function(options) {
    return creme.d3Drawable({
        instance: new creme.D3TextWrap(options),
        props: ['lineHeight', 'maxWidth', 'wordBreakSeparator', 'breakAll']
    });
};

}(jQuery));
