def setup_editor_bundles(settings: dict):
    settings['CREME_OPT_MEDIA_BUNDLES'].append([
        'editor.js',
        'editor/js/tinymceditor.js',
    ])

    settings['CREME_OPT_MEDIA_BUNDLES'].append([
        'editor.css',
    ])
