import { ClassicEditor } from '@ckeditor/ckeditor5-editor-classic';
import { Command, Plugin } from '@ckeditor/ckeditor5-core';
import { Widget, toWidget, viewToModelPositionOutsideModelElement } from '@ckeditor/ckeditor5-widget';
import { Model, addListToDropdown, createDropdown } from '@ckeditor/ckeditor5-ui';
import { Collection } from '@ckeditor/ckeditor5-utils';

import './theme/placeholder.css';

export class Placeholder extends Plugin {
    static get requires() {
        return [ PlaceholderEditing, PlaceholderUI ];
    }
}

class PlaceholderCommand extends Command {
    execute({ value }) {
        const editor = this.editor;
        const selection = editor.model.document.selection;

        editor.model.change(writer => {
            // Create a <placeholder> element with the "name" attribute (and all the selection attributes)...
            const placeholder = writer.createElement('placeholder', {
                ...Object.fromEntries(selection.getAttributes()),
                ...value
            });

            // ... and insert it into the document. Put the selection on the inserted element.
            editor.model.insertObject(placeholder, null, null, { setSelection: 'on' });
        });
    }

    refresh() {
        const model = this.editor.model;
        const selection = model.document.selection;

        const isAllowed = model.schema.checkChild(selection.focus.parent, 'placeholder');

        this.isEnabled = isAllowed;
    }
}

class PlaceholderUI extends Plugin {
    init() {
        const editor = this.editor;
        const t = editor.t;
        const config = editor.config.get('placeholderConfig');
        const placeholders = config.types || [];

        // The "placeholder" dropdown must be registered among the UI components of the editor
        // to be displayed in the toolbar.
        editor.ui.componentFactory.add('placeholder', locale => {
            const dropdownView = createDropdown(locale);

            // Populate the list in the dropdown with items.
            addListToDropdown(dropdownView, getDropdownItemsDefinitions(placeholders));

            dropdownView.set({
                class: 'ck-placeholder-dropdown'
            });

            dropdownView.buttonView.set({
                // The t() function helps localize the editor. All strings enclosed in t() can be
                // translated and change when the language of the editor changes.
                label: config.dropdownTitle || t('Placeholder'),
                tooltip: true,
                withText: true
            });

            // Disable the placeholder button when the command is disabled.
            const command = editor.commands.get('placeholder');
            dropdownView.bind('isEnabled').to(command);

            // Execute the command when the dropdown item is clicked (executed).
            this.listenTo(dropdownView, 'execute', evt => {
                editor.execute('placeholder', { value: evt.source.commandParam });
                editor.editing.view.focus();
            });

            return dropdownView;
        });
    }
}

function getDropdownItemsDefinitions(placeholders) {
    return new Collection(placeholders.map(placeholder => {
        return {
            type: 'button',
            model: new Model({
                commandParam: placeholder,
                label: placeholder.label || placeholder.name,
                withText: true
            })
        };
    }));
}

function getPlaceholdersByName(placeholders) {
    const output = {};

    for (const placeholder of placeholders) {
        output[placeholder.name] = placeholder;
    }

    return output;
}

function defaultPlaceholder(name) {
    return {label: name, name: name, help: ''};
}

function isParagraphable(position, nodeOrType, schema) {
    const context = schema.createContext(position);

    // When paragraph is allowed in this context...
    if (!schema.checkChild(context, 'paragraph')) {
        return false;
    }

    // And a node would be allowed in this paragraph...
    if (!schema.checkChild(context.push('paragraph'), nodeOrType)) {
        return false;
    }

    return true;
}

function wrapInParagraph( position, writer ) {
    const paragraph = writer.createElement( 'paragraph' );

    writer.insert( paragraph, position );

    return writer.createPositionAt( paragraph, 0 );
}

class PlaceholderEditing extends Plugin {
    static get requires() {
        return [ Widget ];
    }

    init() {
        this._defineSchema();
        this._defineConverters();

        const editor = this.editor;

        editor.commands.add('placeholder', new PlaceholderCommand(editor));

        editor.editing.mapper.on(
            'viewToModelPosition',
            viewToModelPositionOutsideModelElement(
                 editor.model,
                 viewElement => viewElement.hasClass('placeholder')
            )
        );

        editor.config.define('placeholderConfig', {
            types: []
        });
    }

    _defineSchema() {
        const schema = this.editor.model.schema;

        schema.register('placeholder', {
            // Behaves like a self-contained inline object (e.g. an inline image)
            // allowed in places where $text is allowed (e.g. in paragraphs).
            // The inline widget can have the same attributes as text (for example linkHref, bold).
            inheritAllFrom: '$inlineObject',

            // The placeholder can have many types, like date, name, surname, etc:
            allowAttributes: [ 'name', 'label', 'help' ],
            allowWhere: '$text',

            isInline: true
        });
    }

    _defineConverters() {
        const conversion = this.editor.conversion;
        const placeholdersByName = getPlaceholdersByName(
            this.editor.config.get('placeholderConfig.types') || []
        );

        /*
         * Read raw source and build editor data model.
         */
        conversion.for('upcast').add(dispatcher => {
            dispatcher.on('text', (evt, data, { schema, consumable, writer }) => {
                let position = data.modelCursor;

                // When node is already converted then do nothing.
                if ( !consumable.test( data.viewItem ) ) {
                    return;
                }

                if (!schema.checkChild( position, '$text' )) {
                    if (!isParagraphable( position, '$text', schema)) {
                        return;
                    }

                    position = wrapInParagraph(position, writer);
                }

                consumable.consume(data.viewItem);

                // The following code is the difference from the original text upcast converter.
                let modelCursor = position;

                for (const part of data.viewItem.data.split( /(?={{.*?}})|(?<=}})/ )) {
                    var node;

                    if (part.startsWith('{{')) {
                        const name = part.slice(2, -2);
                        const placeholder = placeholdersByName[name] || defaultPlaceholder(name);

                        node = writer.createElement('placeholder', placeholder);
                    } else {
                        node = writer.createText(part);
                    }

                    writer.insert( node, modelCursor );
                    modelCursor = modelCursor.getShiftedBy(node.offsetSize);
                }

                data.modelRange = writer.createRange(position, modelCursor);
                data.modelCursor = data.modelRange.end;
            });
        });

        /*
         * Read source html and build editor data model.
         */
        conversion.for('upcast').elementToElement({
            view: {
                name: 'span',
                classes: [ 'placeholder' ]
            },
            model: (viewElement, { writer: modelWriter }) => {
                // Extract the "name" from "{{name}}".
                const name = viewElement.getChild(0).data.slice(2, -2);
                const placeholder = placeholdersByName[name] || defaultPlaceholder(name);

                return modelWriter.createElement('placeholder', placeholder);
            }
        });

        /*
         * Read data model and build edition widget 
         */
        conversion.for('editingDowncast').elementToElement({
            model: 'placeholder',
            view: (modelItem, { writer: viewWriter }) => {
                const help = modelItem.getAttribute('help');
                const label = modelItem.getAttribute('label');

                const widgetElement = viewWriter.createContainerElement('span', (
                    help ? {
                        class: 'placeholder',
                        title: help,
                        alt: help
                    } : {
                        class: 'placeholder'
                    }
                ));

                // Insert the placeholder name (as a text).
                const innerText = viewWriter.createText(label);
                viewWriter.insert(viewWriter.createPositionAt(widgetElement, 0), innerText);

                // Enable widget handling on a placeholder element inside the editing view.
                return toWidget(widgetElement, viewWriter);
            }
        });

        /*
         * Read data model and write source html
         */
        conversion.for('dataDowncast').elementToElement({
            model: 'placeholder',
            view: (modelItem, { writer: viewWriter }) => {
                const name = modelItem.getAttribute('name');

                const widgetElement = viewWriter.createContainerElement('span', {
                    class: 'placeholder',
                });

                const innerText = viewWriter.createText('{{' + name + '}}');
                viewWriter.insert(viewWriter.createPositionAt(widgetElement, 0), innerText);

                return widgetElement;
            }
        });
    }
}
