import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';
import DataBind from 'util/form_databind';

const LIST_ITEM = '<div class="splunk-repeat-item"></div>';
const TEMPLATE_TAG = 'splunk-template';
const KEY_PROPERTY = '@name';

const proto = Object.create(HTMLDivElement.prototype, {

    createdCallback: {
        value() {
            const $el = $(this);
            this.model = new Backbone.Model({ data: $el.data('value') || [] });
            // update data on element. form_list_binding expects data to be set
            this.model.on('change', () => {
                $el.data('value', this.model.get('value'));
            });
            // this would load any default values
        },
    },

    attachedCallback: {
        value() {
            const $el = $(this);
            this.constructTemplates();
            $el.find(TEMPLATE_TAG).remove();
            // When the data change event from the form_list_databind is fired
            $el.on('data', this.handleDataChanged);

            // When any of the child elements of fire a change event it bubbles up to the barent and the internal
            // model is updated
            $el.on('change', () => {
                const data = [];
                const listItems = $el.find('div.splunk-repeat-item');
                _.each(listItems, (item) => {
                    data.push(DataBind.readFormValues(item));
                });
                this.model.set('value', data);
            });

            // This would load any default values
            $el.trigger('change');
        },
    },

    detachedCallback: {
        value() {
            this.model.off();
        },
    },

    handleDataChanged: {
        value() {
            const $el = $(this);
            this.model.set('value', $el.data('value'));
            this.renderContent();
        },
    },

    /**
     * Store each template contents on the template property of the element
     */
    constructTemplates: {
        value() {
            const $el = $(this);
            const templates = {};
            $el.find(TEMPLATE_TAG).each((index, t) => {
                const temp = $(t);
                let name = temp.attr('name');
                name = name || 'default';
                templates[name] = temp.html();
            });
            this.templates = templates;
        },
    },

    renderContent: {
        value() {
            const $el = $(this);
            const data = this.model.get('value');
            const listItems = $el.find('div.splunk-repeat-item');
            if (data && _.isArray(data)) {
                _.each(data, (item, index) => {
                    if ((listItems.length > 0 && (listItems.length >= index + 1))) {
                        DataBind.applyFormValues(listItems[index], item);
                    } else {
                        this.createNewListItem(item);
                    }
                });
            }
        },
    },

    createNewListItem: {
        value(item) {
            const $el = $(this);
            let template = null;

            if (item[KEY_PROPERTY] && this.templates[item[KEY_PROPERTY]]) {
                template = this.templates[item[KEY_PROPERTY]];
            } else if (this.templates.default) {
                template = this.templates.default;
            } else {
                throw new Error('No template provided');
            }

            template = $(LIST_ITEM).append($(template).clone());
            $el.append(template);
            DataBind.applyFormValues(template, item);
        },
    },
});

document.registerElement('splunk-repeat', { prototype: proto });
