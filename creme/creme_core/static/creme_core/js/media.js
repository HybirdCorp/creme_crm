/* globals media_url */
/* eslint no-unused-vars: "off" */
function creme_media_url(url) {
    return media_url((window.THEME_NAME || '') + "/" + url);
};
