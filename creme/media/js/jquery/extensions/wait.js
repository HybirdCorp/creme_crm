$.fn.wait = function(time, type) {
        time = time || 1000;
        type = type || "fx";
        return this.queue(type, function() {
            var self = this;
            setTimeout(function() {
                $(self).dequeue();
            }, time);
        });
};

//function refresh()
//{
//    window.document.location.href = window.document.location.href;
//}

//Exemple d'utilisation :
//    function runIt() {
//      $("div").wait()
//              .animate({left:'+=200'},2000)
//              .wait()
//              .animate({left:'-=200'},1500,runIt);
//    }
//    runIt();
