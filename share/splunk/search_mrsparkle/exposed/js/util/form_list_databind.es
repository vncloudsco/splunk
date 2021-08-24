/**
 * Binds list values to the element,
 * Lists hold array of objects . This data is stored as data "content" on the element
 */
import $ from 'jquery';
import _ from 'underscore';

const CUSTOM_FORM_LIST_ELEMENT_PARENT = 'splunk-repeat';

function getFormElements(formEl) {
    return $(formEl).find(CUSTOM_FORM_LIST_ELEMENT_PARENT);
}

export function readFormValues(formEl) {
    const data = {};

    _(getFormElements(formEl)).each((input) => {
        const $input = $(input);
        const name = $input.attr('name');
        data[name] = $input.data('value') || [];
    });
    return data;
}


export function applyFormValues(formEl, data) {
    _(getFormElements(formEl)).each((input) => {
        const $input = $(input);
        const name = $input.attr('name');
        $input.data('value', data[name]);
        $input.trigger('data');
    });
}
