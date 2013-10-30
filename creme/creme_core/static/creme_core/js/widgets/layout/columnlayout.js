/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2013  Hybird

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

creme.layout = creme.layout || {}

creme.layout.ColumnSortLayout = creme.layout.Layout.sub({
    _init_: function(options)
    {
        var options = $.extend({
            columns: 1
        }, options || {});

        this._super_(creme.layout.Layout, '_init_', options);

        this.columns(options.columns);
        this.comparator(options.comparator);

        this.onLayout(this._onLayout);
        this.onAdded(this.layout);
        this.onRemoved(this.layout);
        this.onResize(this.layout);
    },

    /*
     * Only needed by sub lists as columns algorithm
     * 
    children: function() {
        return $('> *:not(.ui-layout), > .ui-layout > *', this._target).filter(this._filter);
    },
    */

    comparator: function(comparator)
    {
        if (comparator === undefined)
            return this._comparator;

        this._comparator = $.proxy(comparator, this);
        return this;
    },

    columns: function(columns)
    {
        if (columns === undefined)
            return this._columns;

        if (Object.isType(columns, 'string') && columns.endsWith('px')) {
            var size = parseInt(columns.substr(0, columns.length - 2));
            columns = isNaN(size) ? 1 : function() {return Math.floor(this.container().width() / size);}
        }

        this._columns = Object.isFunc(columns) ? columns : function() {return columns;};
        return this; 
    },

    _onLayout: function(event, container)
    {
        var sortables = Array.copy(this.children().get());
        var column_count = Math.max(this._columns(), 1);
        var column_list = [];
        var column_item_count = Math.ceil(sortables.length / column_count);

        try {
            sorted = sortables.sort(this._comparator);
        } catch(e) {}

        for(var index = 0; index < column_count; ++index) {
            column_list.push([]);
        }

        sortables.forEach(function(item, index) {
            column_list[Math.floor(index / column_item_count)].push($(item));
        });

//        column_list.forEach(function(column, index) {
//            console.log('column: ', index, ' ', column.map(function(item) {return $(item).attr('name');}));
//        });

        /*
         * Create sub lists as columns
         * 
        $('> .ui-layout-column', container).remove();

        column_list.forEach(function(column, index) {
            var column_container = $('<ul>').addClass('ui-layout-column').appendTo(container);

            column.forEach(function(item, index) {
                $(item).remove().appendTo(column_container);
            });
        });
        */

        /*
         * Order lines by column and eval item size.
         * 
        for(var line = 0; line < column_item_count; ++line)
        {
            column_list.forEach(function(column) {
                if (column.length > line) {
                    $(column[line]).css('min-width', '%f%%'.format(100/column_count)).remove().appendTo(container);
                } else {
                    $('<li>').addClass('ui-layout-column empty').appendTo(container);
                }
            });
        }
        */

        /*
         * Order lines by column
         */
        container.attr('ui-layout-columns', column_count);

        $('> .ui-layout.column.empty', container).remove();
        this.children().remove();

        for(var line = 0; line < column_item_count; ++line)
        {
            column_list.forEach(function(column) {
                if (column.length > line) {
                    container.append(column[line]);
                } else {
                    container.append($('<li>').addClass('ui-layout column empty'));
                }
            });
        }
    }
});


creme.layout.CSSColumnLayout = creme.layout.Layout.sub({
    _init_: function(options)
    {
        var options = $.extend({
            columns: 1
        }, options || {});

        this._super_(creme.layout.Layout, '_init_', options);

        this.columns(options.columns);

        this.onLayout(this._onLayout);
        this.onAdded(this.layout);
        this.onRemoved(this.layout);
        this.onResize(this.layout);
    },

    columnWidth: function() {
        return Math.floor(this.container().width() / this.columns()); 
    },

    columns: function(columns)
    {
        if (columns === undefined) {
            return this._columns ? this._columns() : 1;
        }

        this._columns = Object.isFunc(columns) ? columns : function() {return columns;};
        return this;
    },

    _onLayout: function(event, container)
    {
        var container = this.container();
        var column_width = this.columnWidth();

        column_width = '' + column_width + 'px;'

        container.attr('style', '-webkit-column-width:' + column_width +
                                '-moz-column-width:' + column_width +
                                '-column-width:' + column_width);
    }
});
