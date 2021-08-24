/**
 * Webcomponent wrapper round DateControl. DateControl can not work with a regular backbone model so this component
 * does not inherit from the  inputbase.
 */
import $ from 'jquery';
import DateControl from 'views/shared/controls/DateControl';
import DateInputModel from 'models/shared/DateInput';

const proto = Object.create(HTMLDivElement.prototype, {

    createdCallback: {
        value() {
            const $el = $(this);
            $el.html($.trim($el.html()));
            this.model = new DateInputModel({ value: $(this).attr('value') });
            if ($el.attr('value')) {
                this.model.setFromJSDate(new Date($el.attr('value')));
            }
        },
    },

    attachedCallback: {
        value() {
            const $el = $(this);
            this.model.on('change', () => {
                $el.attr('value', this.model.jsDate({ includeTime: false }).toJSON());
                $el.trigger('change');
            });

            this.view = new DateControl({
                el: this,
                model: this.model,
                required: this.model.get('required'),
            });
            this.view.render();
        },
    },

    attributeChangedCallback: {
        value(name, previousValue, value) {
            if (name === 'value') {
                this.model.setFromJSDate(new Date(value));
            }
        },
    },

    detachedCallback: {
        value() {
            this.model.off();
            if (this.view) {
                this.view.remove();
            }
        },
    },
});

document.registerElement('splunk-date-input', { prototype: proto });
