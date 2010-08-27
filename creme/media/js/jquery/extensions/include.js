//Moins pratique mais plus rapide de mettre l'extension "a la main"
function include(url, extension)
{
    if(url.indexOf('/site_media/') == -1) return;
    try
    {
        var head = window.document.getElementsByTagName('head')[0];
        if(extension && extension == 'js')
        {
            var script = window.document.createElement('script');
            script.setAttribute('src', url);
            script.setAttribute('type', 'text/javascript');
            script.setAttribute('charset', 'utf-8');
            head.appendChild(script);
        }
        else if(extension && extension == 'css')
        {
            var css = window.document.createElement('link');
            css.setAttribute('rel', 'stylesheet');
            css.setAttribute('href', url);
            css.setAttribute('type', 'text/css');
            head.appendChild(css);
        }
    }
    catch(e)
    {
        alert('Message de debug a retirer function js include() {}');
        alert(e);
    }
}

creme.include = function(url, extension, callback)
{
    if($('script[src!=""][src*="'+url+'"]').size() <= 0)
    {
        include(url, extension);
    }
    
    if(typeof(callback)=="function")
    {
        var args = Array.prototype.slice.apply(arguments, [3]);
        callback.apply(null, args);
    }
}
creme.include('/site_media/js/i18n.js','js');
include('/site_media/js/jquery/extensions/jquery.utils.js','js');
include('/site_media/js/jquery/extensions/wait.js','js');
include('/site_media/js/jquery/extensions/highlight.js','js');
include('/site_media/css/fg-menu-3.0/fg.menu.css','css');
include('/site_media/js/creme/creme.utils.js','js');
creme.include('/site_media/js/models/properties.js','js');
creme.include('/site_media/js/models/activities.js','js'); //TODO: improve the js system to remove this file from here.....
creme.include('/site_media/js/creme/creme.ajax.js','js');
creme.include('/site_media/js/creme/creme.menu.js','js');