/* globals media_url */
/* eslint no-unused-vars: "off" */
function static_url(url) {
    return window.STATIC_URL + url;
};

function creme_media_url(url) {
    return static_url((window.THEME_NAME || '') + "/" + url);
};
