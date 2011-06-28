/*
 * File : jquery.utils
 * Author : rbeck
 * Date : $8 sept. 2009 11:35:21$
 */

//check trouve sur http://www.jquery.info/spip.php?article24
$.fn.check = function(mode) {
        var mode = mode || 'on'; // si mode non défini, défaut: 'on'
        return this.each(function() {
                switch(mode) {
                case 'on':
                        this.checked = true;
                        break;
                case 'off':
                        this.checked = false;
                        break;
                case 'toggle':
                        this.checked = !this.checked;
                        break;
                }
        });
};

$.fn.uncheck = function(){
    return $(this).check('off');
};

$.fn.toggleCheck = function(){
    return $(this).check('toggle');
};

$.fn.getValues = function(){
    var arrOfSelected = new Array();
    this.each(function(){
        arrOfSelected.push($(this).val());
    });
    return arrOfSelected;
}

$.isEmptyObject = function( obj ) {//Extracted method from jQuery 1.4. TODO: Remove me when upgrading to a jQuery version >=1.4
    for ( var name in obj ) {
        return false;
    }
    return true;
}