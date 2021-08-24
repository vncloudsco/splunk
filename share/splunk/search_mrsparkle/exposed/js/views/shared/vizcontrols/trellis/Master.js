/*
 * A pop-down dialog that provides trellis controls for a visualization based on a provided schema.
 *
 * This view renders the activator button and wires up dynamically creating and showing the dialog child view.
 */

define([
            'jquery',
            'underscore',
            'module',
            'views/Base',
            './Dialog',
            './Master.pcss',
            'bootstrap.tooltip'
        ],
        function(
            $,
            _,
            module,
            BaseView,
            Dialog,
            css
        ) {

    return BaseView.extend({
        moduleId: module.id,

        className: 'btn-group',

        events: {
            'click .trellis': function(e) {
                e.preventDefault();

                if (!this.options.enabled) {
                    return;
                }

                var $target = $(e.currentTarget);

                this.children.trellis = new Dialog({
                    model: {
                        report: this.model.report,
                        application: this.model.application
                    },
                    className: 'popdown-dialog popdown-dialog-draggable popdown-dialog-trellis',
                    formatterDescription: this.options.formatterDescription,
                    onHiddenRemove: true,
                    saveOnApply: this.options.saveOnApply
                });
                this.children.trellis.render().activate().appendTo($('body'));
                this.children.trellis.show($target);
                $target.addClass('active');

                this.listenTo(this.children.trellis, 'hidden', function() {
                    $target.removeClass('active');
                });
            }
        },

        setFormatterDescription: function(formatterDescription) {
            this.options.formatterDescription = formatterDescription;
        },

        tooltip: function(options) {
            this.$('a.popdown-toggle').tooltip(options);
        },

        render: function() {
            this.$el.html(this.compiledTemplate());

            this.tooltip({
                title: _('Use trellis layout').t()
            });

            return this;
        },

        disable: function(){
            this.options.enabled = false;
            this.$('a.popdown-toggle').addClass('disabled');
        },

        enable: function(){
            this.options.enabled = true;
            this.$('a.popdown-toggle').removeClass('disabled');
        },

        template: '\
            <a class="btn-pill popdown-toggle trellis" href="#">\
                <i class="icon-trellis-layout"/><span class="link-label"><%- _("Trellis").t() %></span>\
            </a>\
        '

    });

});
