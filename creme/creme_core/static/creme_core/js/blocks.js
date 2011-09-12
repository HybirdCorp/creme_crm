/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2009-2011  Hybird

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

creme.blocks = {
    __registeredBlocks: {},
    collapsed_class: 'collapsed',
    hide_fields_class: 'hide_empty_fields'
};

creme.blocks.register = function(block_id) {
    var $block = $(block_id);

    if ($block.size() == 1) {
        this.__registeredBlocks[block_id] = $block;
    } else {
        console.log('creme.blocks.register::block_id is not unique:' + block_id);
    }
};

creme.blocks.get_block = function(block_id) {
    return this.__registeredBlocks[block_id];
};

creme.blocks.saveState = function(block, state) {
    var collapsed_class = this.collapsed_class;
    var hide_fields_class = this.hide_fields_class;

    var stateToSend = {}

    var isOpen = state['isOpen'];
    var showEmptyFields = state['showEmptyFields']

    if (typeof(isOpen) != "undefined") {
        stateToSend['is_open'] = +isOpen;
    }

    if (typeof(showEmptyFields) != "undefined") {
        stateToSend['show_empty_fields'] = +showEmptyFields;
    }

    if (!$.isEmptyObject(stateToSend)) {
        creme.ajax.json.post('/creme_core/blocks/reload/set_state/' + block[0].id + '/', stateToSend, function(data, status) {
            if (isOpen) {
                block.removeClass(collapsed_class);
            } else {
                block.addClass(collapsed_class);
            }

            if (showEmptyFields) {
                block.removeClass(hide_fields_class);
            } else {
                block.addClass(hide_fields_class);
            }
        }, null, true);
    }
};

creme.blocks._applyOpenState = function(block) {
    if (block.hasClass(this.collapsed_class)) {
        creme.utils.tableCollapse(block.find('.collapser'), false);
    }
};

creme.blocks._applyShowFieldState = function(block) {
    if (block.find('.view_more, .view_less').size() > 0) {//Apply state only when toggle button is present
//        var $lines = block.find('tbody td:empty').parent('tr');
        var $lines = block.find('tbody tr:has(td:empty)').filter(function(i) {
            return !($(this).find('td:not(:empty)').size() > 0);
        })

        if (block.hasClass(this.hide_fields_class)) {
            $lines.hide();
        } else {
            $lines.show();
            block.removeClass(this.hide_fields_class);
        }
    }
};

creme.blocks.toggleEmptyFields = function(button) {
    var $button = $(button);
    var $block = $button.parents('table[id!=].table_detail_view');
    var state = {action : "hide"};

    if ($button.hasClass('view_less')) {
        $button.removeClass('view_less').addClass('view_more');
    } else {
        $button.removeClass('view_more').addClass('view_less');
        state = {action : "show"};
        $block.removeClass(this.hide_fields_class);
    }
    $block.trigger('creme-blocks-field-display-changed', state);
    creme.blocks._applyShowFieldState($block);
}

creme.blocks.applyState = function(block) {
    this._applyOpenState(block);
    this._applyShowFieldState(block);
};

creme.blocks.bindEvents = function() {
    var __registeredBlocks = this.__registeredBlocks;

    for (var i in __registeredBlocks) {
        var block = __registeredBlocks[i];

        block.bind('creme-table-collapse', function(e, params) {
            creme.blocks.saveState($(this), {isOpen: (params.action == 'show')})
        });

        block.bind('creme-blocks-field-display-changed', function(e, params) {
            creme.blocks.saveState($(this), {showEmptyFields: (params.action == 'show')})
        });

        creme.blocks.applyState(block);
    }
};
