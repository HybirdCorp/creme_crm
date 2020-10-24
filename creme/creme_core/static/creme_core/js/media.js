/* globals media_url */
/* eslint no-unused-vars: "off" */
function creme_media_url(url) {
    return window.STATIC_URL + (window.THEME_NAME || '') + "/" + url;
};
