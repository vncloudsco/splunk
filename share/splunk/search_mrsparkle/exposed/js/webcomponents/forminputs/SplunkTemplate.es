/**
 * This Element would be replaced/ removed when the html template element is supported in all browsers splunk supports
 * For now this element simply trims its contents and hides itself. Other elements who depend on the template
 * would clone the template.
 */
import $ from 'jquery';

const proto = Object.create(HTMLDivElement.prototype, {

    createdCallback: {
        value() {
            const $el = $(this);
            $el.html($.trim($el.html()));
            $el.hide();
        },
    },
});

document.registerElement('splunk-template', { prototype: proto });
