(function($) {
"use strict";

window.QUnitFormMixin = {
    beforeEach: function() {
        var self = this;
        this.resetMockFormSubmitCalls();

        this.qunitFixture().on('submit', 'form', function(e) {
            e.preventDefault();
            self._mockFormSubmitCalls.push($(e.target).attr('action'));
        });
    },

    resetMockFormSubmitCalls: function() {
        this._mockFormSubmitCalls = [];
    },

    mockFormSubmitCalls: function() {
        return this._mockFormSubmitCalls;
    },

    browserValidationMessage: function(element) {
        var e = $(element).get(0);
        e.checkValidity();
        return e.validationMessage;
    }
};

}(jQuery));
