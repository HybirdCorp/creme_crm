/*!
 * Part of jQuery Migrate - v1.2.1 - 2013-05-08
 * https://github.com/jquery/jquery-migrate
 * Copyright 2005, 2013 jQuery Foundation, Inc. and other contributors
 * Copyright 2015  Hybird
 * 
 * Licensed MIT
 */

(function($) {

    var uaMatch = function( ua ) {
        ua = ua.toLowerCase();
    
        var match = /(chrome)[ \/]([\w.]+)/.exec( ua ) ||
            /(webkit)[ \/]([\w.]+)/.exec( ua ) ||
            /(opera)(?:.*version|)[ \/]([\w.]+)/.exec( ua ) ||
            /(msie) ([\w.]+)/.exec( ua ) ||
            ua.indexOf("compatible") < 0 && /(mozilla)(?:.*? rv:([\w.]+)|)/.exec( ua ) ||
            [];
    
        return {
            browser: match[ 1 ] || "",
            version: match[ 2 ] || "0"
        };
    };

    // Don't clobber any existing jQuery.browser in case it's different
    var matched = uaMatch( navigator.userAgent );
    var browser = {};

    if ( matched.browser ) {
        browser[ matched.browser ] = true;
        browser.version = matched.version;
    }

    // Chrome is Webkit, but Webkit is also Safari.
    if ( browser.chrome ) {
        browser.webkit = true;
    } else if ( browser.webkit ) {
        browser.safari = true;
    }

    $.browserInfo = function() {
        return browser;
    }

    $.matchBrowserVersion = function(pattern) {
        return browser.version.match('^(' + pattern + ')$') !== null;
    }

    $.matchIEVersion = function() {
        var pattern = '';

        for(var i = 0; i < arguments.length; ++i) {
            var version =  arguments[i] + '\.[\\d]+';
            pattern += i > 0 ? '|' + version : version;
        }

        return (browser.msie === true) && $.matchBrowserVersion(pattern);
    }
})($);
