;(function($){
/**
 * creme extension functions of jqGrid
 * http://hybird.org
 * rbeck@hybird.org
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/

$.fn.extend({
    addButton : function (elem, p) {
        p = $.extend({
            caption : "newButton",
            title: '',
            buttonicon : 'ui-icon-newwin',
            onClickButton: null,
            position : "last"
        }, p ||{});
        return this.each(function() {
            if( !this.grid)  { return; }
            if( elem.indexOf("#") != 0) { elem = "#"+elem; }
			var findnav = $(elem)[0];
            if (findnav) {
                var tbd = $("<div></div>");
                $(tbd).addClass('ui-pg-button ui-corner-all').append("<div class='ui-pg-div'><span class='ui-icon "+p.buttonicon+"'></span>"+p.caption+"</div>");
                if(p.id) {$(tbd).attr("id",p.id);}
                /*if(p.position=='first'){
                    if(findnav.rows[0].cells.length ===0 ) {
                        $("tr",findnav).append(tbd);
                    } else {
                        $("tr td:eq(0)",findnav).before(tbd);
                    }
                } else {
                    $("tr",findnav).append(tbd);
                }*/
                $(tbd,findnav)
                .attr("title",p.title  || "")
                .click(function(e){
                    if ($.isFunction(p.onClickButton) ) { p.onClickButton(); }
                    return false;
                })
                .hover(
                    function () {$(this).addClass("ui-state-hover");},
                    function () {$(this).removeClass("ui-state-hover");}
                );
                $(findnav).append(tbd);
            }
        });
    }
});
})(jQuery);