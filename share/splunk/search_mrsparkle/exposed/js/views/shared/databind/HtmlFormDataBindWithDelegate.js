/**
 * This is an extension to the htmlformDialog.
 *
 * This class can have delegates registered . When a deligate is registered , they can hook into the
 * lifecycle methods and provide custom logic.
 *
 * Currently All delegates should be inheriting from the SplunkFormHandlerBase class.
 *
 * Once a delegate is registered it would be notified when the data changes, appripriate life cycle
 * methods are called on them.
 *
 * Example :
 *   "change" is called when the data on target model changes
 *   "validate" is called before save
 *
 */

//TO-DO converting this file to es2015 is causeing some issues with imports. Fix to use es2015

define([
   'jquery',
    'underscore',
    'backbone',
    'util/form_databind',
    'util/form_list_databind',
    'views/shared/databind/HtmlFormDialog'

], function(
    $,
    _,
    Backbone,
    Databind,
    DatabindList,
    HtmlFormDialog
) {

    var PARENT = '<div class="mod-parent"></div>';

    return HtmlFormDialog.extend({

        tag: 'div',
        initialize: function(options) {
            HtmlFormDialog.prototype.initialize.apply(this, arguments);
            this.delegates = null;
            if (options.delegate) {
                this.registerDelegate(options.delegate);
            }
        },

        getForm: function() {
            return this.$('form');
        },

        getFormElement: function() {
            return this.el.querySelectorAll('form');
        },

        registerDelegate: function(delegate) {

            this.delegate = delegate;
            this.delegate.initialize(
                this.getFormElement(),
                {attributePrefix: this.attributePrefix}
            );
        },

        validateForm: function() {

            var errors = [];
            if (this.delegate) {
                errors = this.delegate.validate.call(this.delegate, this.getFormElement(), this.model.target.toJSON(), errors);
                if (errors.length > 0) {
                    // Calling show error here so all the errors ( standard + custom errors user added ) are highlighted
                    this.delegate.showErrors(this.getFormElement());
                }
            }
            return errors;
        },

        save: function() {
            if(this.delegate) {
                this.delegate.save.call(this.delegate, this.getFormElement(), this.model.target.toJSON());
            }
        },

        change: function() {
            if(this.delegate) {
                this.delegate.change.call(this.delegate, this.getFormElement(), this.model.target.toJSON());
            }
        },

        removeIgnoredFieldsFromModel: function() {

            if(!this.delegate) {
                return;
            }

            _.each(this.delegate.ignoreList, function(item) {
                this.model.target.unset(item);
            }, this);
        },

        writeFormValues: function() {
            var formUpdate = this.model.target.toJSON();
            DatabindList.applyFormValues(this.getForm(), formUpdate);
            HtmlFormDialog.prototype.writeFormValues.apply(this, arguments);

            if(this.delegate) {
                formUpdate = this.delegate.writeFormValues.call(this.delegate, formUpdate);
            }

            DatabindList.applyFormValues(this.getForm(), formUpdate);
            Databind.applyFormValues(this.getForm(), formUpdate);
        },

        readFormValues: function() {
            HtmlFormDialog.prototype.readFormValues.apply(this, arguments);
            var modelUpdate = this.model.target.toJSON();
            _(DatabindList.readFormValues(this.getForm())).each(function(value, name) {
                if (name.indexOf(this.attributePrefix) === 0) {
                    modelUpdate[name] = value || [];
                }
            }.bind(this));


            if(this.delegate) {
                modelUpdate = this.delegate.readFormValues.call(this.delegate, modelUpdate);
            }
            this.model.target.set(modelUpdate);

            this.removeIgnoredFieldsFromModel();
            this.change();
        },

        renderContentHtml: function(html) {
            this.$el.append(PARENT);
            this.$el.find('.mod-parent').html(html);
        }
    });
});
