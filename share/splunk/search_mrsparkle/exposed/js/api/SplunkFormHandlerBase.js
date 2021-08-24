/**
 * Base Class for Mod setup. This class will be initialized by default for modsetup configurations. Base class provides
 * default functionality for the following:
 *
 * 1) Initializes errors ,ignore lists and stores the forms
 * 2) Handles validation using html5 attributes ( splunk web components support "required" and "pattern" validation
 * attributes ) on TextField and TextArea components.
 *     - The default validation mechanism also handles hignlighting the error fields
 *     - Resetting the errors on fields when re-validating
 * 3) Provide methods to manage ignoreList. Adding a field name to ignoreList will ignore the field for validations and
 * the value of the field will not be peristed.  This will be useful for hidden or disabled fields.
 *
 *
 * SplunkFormHandlerBase provides methods hooks in the process of mod setup described below:
 *
 *  - initialize: Could be used to initialize any additional custom components.
 *  - destroy: Can be used for any cleanup
 *  - change: Called when field values change . This could be used to hide/disable other fields when value changes
 *  - validate - resets the errors on fields/ re-validates and highlights error fields and populates this.errors.
 *  - save - called after the validation but defore the save requests are made
 *  - readFormValues - reads values from form to the model
 *  - writeFormValues - writes from model to form
 *  - addError: adds errors to this.error
 *  - showErrors: Highlights fields with errors
 *  - resetErrors: Clears all the error highlighting
 *  - addToIgnoreList: Item added to ignore list will not be validated or saved
 *  - removeFromIgnoreList: Removes item from ignore list
 *
 */
define([
    'underscore',
    'backbone'
], function(
    _,
    Backbone
) {

    var SplunkFormHandlerBase = function(options) {
        this.errors = [];
        this.ignoreList = [];
        this.options = options ||  {};
    };

    _.extend(SplunkFormHandlerBase.prototype, Backbone.Events, {

        /**
         * Initialize: App developers can override this method to append any custom elements to the form. Any
         * custom elements appended should be managed by the app developer. Example the validation and change
         *
         * handler.
         * @param forms
         * @param options
         */
        initialize: function(forms, options) {

            this.forms = forms;
            this.options = options || {};
            _.each(forms, function(el) {
                el.addEventListener('submit', function(e) {
                    e.preventDefault();
                });
            });
        },

        /**
         * Save is called after validation but before the save requests are made. Any additional save logic like saving
         * to external api's or perform pre-save cleanup could be done here.
         * */
        save: function(forms, data) {

        },

        /**
         * App developers could use the change hook to react to changes on the data. Ex: Hide some components
         * based on the value of another component
         *
         * @param forms
         * @param data
         */
        change: function(forms, data) {

        },

        /**
         * Basic form validation is automatically handled. Fields marked as required or with a pattern will be automatically
         * highlighted if invalid.
         * App developers can override this function to provide custom validation. If additional validations need
         * to be provided then app developers can override this method and call the base method for basic validation
         * + include any custom validation logic.
         *
         * @param forms
         * @param data
         * @param errors
         * @returns {*}
         */
        validate: function(forms, data, errors) {
            this.resetErrors();

            // update local errors
            if (errors) {
                this.errors = errors;
            }

            _.each(forms, function(form) {
                this._validateForm(form);
            }, this);

            return errors;
        },

        _validateForm: function(el) {
            // if the form is invalid add 'error' class
            if (!el.checkValidity()) {
                var elements = el.querySelectorAll(':invalid');

                _.each(elements, function(element) {
                    var name = '',
                        message = '';

                    // closest not supported in IE
                    var el = element,
                        classAdded = false;

                    // If element is in a control group
                    while (el) {
                        if (!name) {
                            name = (el.attributes['name'] && el.attributes['name'].value.startsWith(this.options.attributePrefix))
                                ? el.attributes['name'].value: '';
                            if (name && el.dataset.errorMessage) {
                                message = el.dataset.errorMessage;
                            }
                        }
                        el = el.parentElement;
                    }

                    if (_.contains(this.ignoreList, name)) {
                        return;
                    }

                    this.addError('error', name, message?message:element.validationMessage);
                }, this);
            }
        },

        /**
         * Reads changed values from the form and writes them to the target model. This method can be overridden
         * to add the value of any custom fields that the developer might have included.
         *
         * @param data
         */
        readFormValues: function(data) {
            return data;
        },

        /**
         * Write values from the model to the form
         *
         * @param data
         * @returns {null}
         */
        writeFormValues: function(data) {
            return data;
        },

        /**
         * Override to perform any additional cleanup
         */
        destroy: function() {

        },

        /**
         * Standard way to add error messages.
         *
         * @param type {error | warning}
         * @param name
         * @param message
         */
        addError: function(type, name, message) {
            this.errors.push({
                type: type || 'error',
                html: message,
                name: name
            });
        },

        /**
         * markFields for error will be called form show errors. This method will look for all the fields
         * that have errors and add a "error" class to itself or one of its parent if it is inside a control
         * group.
         *
         * Override to provide custom error handling style.
         * Note : We recursively look for a parent 'control group' element to add the error class. If one does not
         * exist , the error class is added to the element itself.
         */
        markFieldsWithError: function() {

            _.each(this.errors, function(error) {

                var name = error.name,
                    classAdded = false;

                var currentEl = this.getElementWithName(name),
                    el = currentEl;

                 // If element is in a control group
                while (el) {
                    if (el.classList.contains('control-group')) {
                        classAdded = true;
                        el.classList.add('error');
                        break;
                    }
                    el = el.parentElement;

                    // When configuring multiple apps , its best to stop the loop at each app, This would
                    // prevent any side effects due to elements with same name
                    if (el && el.classList.contains('tab-content')) {
                        el = currentEl;
                        break;
                    }
                }

                // In case no control group was used just add the error class to the field itself
                if (el && !classAdded) {
                    el.classList.add('error');
                }
            }, this);
        },

        /**
         * Show error messages to the user
         * @param forms
         *
         */
        showErrors: function(forms) {

            _.each(this.errors, function(item) {

                var errorEl = document.createElement('div');
                errorEl.className = "mod-setup-error-message";
                errorEl.innerHTML = item.html;

                var childEl = this.getElementWithName(item.name);
                if (childEl) {
                    childEl.parentNode.appendChild(errorEl);
                }

            }, this);

            this.markFieldsWithError();
        },

        /**
         * Clear all the errors on the form
         */
        resetErrors: function() {
            _.each(this.forms, function(el) {
                _.each(el.querySelectorAll('.mod-setup-error-message'), function(item) {
                    item.remove();
                }, this);

                this.errors = [];
                var elements = el.querySelectorAll('*');
                _.each(elements, function(element) {

                    // closest not supported in IE
                    var el = element;
                    if (element.classList.contains('error')) {
                        element.classList.remove('error');
                    }

                    while ((el = el.parentElement) && !el.classList.contains('error')) {
                        el.classList.remove('error');
                    }
                }, this);
            }, this);
        },

        /**
         * Items added to the ignore list will not be validated and the values will not be
         * persisted to conf
         * @param item
         */
        addToIgnoreList: function(item) {
            if (!_.contains(this.ignoreList, item)) {
                this.ignoreList.push(item);
            }
        },

        /**
         * Removing an item from ignore list will validate that field and its value will be persisted.
         * @param item
         */
        removeFromIgnoreList: function(item) {
            var index = this.ignoreList.indexOf(item);
            if (index > -1) {
                this.ignoreList.splice(index, 1);
            }
        },

        /**
         * Searches for element in the current forms list
         * @param name
         * @returns {*}
         */
        getElementWithName: function(name) {

            // using a regular for loop here to return when found
            for (var i=0; i< this.forms.length; i++) {
                var el = this.forms[i].querySelector('[name="'+name+'"]');
                if (el) {
                    return el;
                }
            }

            return null;
        }

    });

    _.extend(SplunkFormHandlerBase, {
        extend: Backbone.View.extend
    });

    return SplunkFormHandlerBase;
});
