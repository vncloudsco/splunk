define(
    [
        'underscore',
        'backbone',
        'module',
        'views/Base',
        'views/shared/controls/ControlGroup',
        'views/shared/controls/SyntheticSelectControl',
        'splunk.util',
        'uri/route'
    ],
    function(_, Backbone, module, Base, ControlGroup, SyntheticSelectControl, splunkUtil, route) {
        return Base.extend({
            moduleId: module.id,
             /**
             * @param {Object} options {
             *     model: {
             *         state: <models.Base>,
             *         application: <models.Application>
             *     }
             *     includeControls: [views] an array of views to pass to the emailInclude control group
             *     toLabel: <String> (Optional) Default 'To'
             *     suffix: <String> report|alert|view. Default report
             *     includeSubjectDefaultPlaceholder: <bool> Default false
             * }
             */
            className: 'enable-actions-view',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);

                var defaults = {
                    suffix: 'report',
                    toLabel: _('To').t(),
                    includeSubjectDefaultPlaceholder: false
                };

                _.defaults(this.options, defaults);

                this.children.toEmailAddresses = new ControlGroup({
                    className: 'control-group',
                    controlType: 'Textarea',
                    controlOptions: {
                        modelAttribute: 'action.email.to',
                        ariaLabel: this.options.toLabel,
                        model: this.model.state
                    },
                    label: this.options.toLabel,
                    help: splunkUtil.sprintf(_('Comma separated list of email addresses. %s').t(),' <a href="#" class="show-cc-bcc">' + _("Show CC and BCC").t() + '</a>')
                });

                this.children.ccEmailAddresses = new ControlGroup({
                    className: 'control-group',
                    controlType: 'Textarea',
                    controlOptions: {
                        modelAttribute: 'action.email.cc',
                        model: this.model.state,
                        ariaLabel: _('CC').t(),
                        placeholder: _('optional').t()
                    },
                    label: _('CC').t()
                });

                this.children.bccEmailAddresses = new ControlGroup({
                    className: 'control-group',
                    controlType: 'Textarea',
                    controlOptions: {
                        modelAttribute: 'action.email.bcc',
                        model: this.model.state,
                        ariaLabel: _('BCC').t(),
                        placeholder: _('optional').t()
                    },
                    label: _('BCC').t()
                });

                this.children.emailPriority = new ControlGroup({
                    className: 'control-group',
                    controlType: 'SyntheticSelect',
                    controlOptions: {
                        modelAttribute: 'action.email.priority',
                        model: this.model.state,
                        items:[
                            {label: _('Lowest').t(), value: '5'},
                            {label: _('Low').t(), value: '4'},
                            {label: _('Normal').t(), value: '3'},
                            {label: _('High').t(), value: '2'},
                            {label: _('Highest').t(), value: '1'}
                        ],
                        toggleClassName: 'btn',
                        popdownOptions: {
                            attachDialogTo: '.modal:visible',
                            scrollContainer: '.modal:visible .modal-body:visible'
                        }
                    },
                    label: _('Priority').t()
                });

                var configTokenHelpLink = route.docHelp(
                        this.model.application.get("root"),
                        this.model.application.get("locale"),
                        'learnmore.alert.email.tokens'
                );

                // for backwards compatibility
                var subjectModelAttribute = 'action.email.subject';
                if (splunkUtil.normalizeBoolean(this.model.state.get('action.email.useNSSubject'))) {
                    subjectModelAttribute += '.' + this.options.suffix;
                }
                this.children.emailSubject = new ControlGroup({
                    className: 'control-group',
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: subjectModelAttribute,
                        model: this.model.state,
                        ariaLabel: _('Subject').t(),
                        placeholder: this.options.includeSubjectDefaultPlaceholder? _('Default').t() : ''
                    },
                    label: _('Subject').t(),
                    help: splunkUtil.sprintf(_('The email subject, recipients and message can include tokens that insert text based on the results of the search. %s').t(), ' <a class="help-link" href="' + configTokenHelpLink + '" target="_blank" title="' + _("Splunk help").t() +'">' + _("Learn More").t() + ' <i class="icon-external"></i></a>')
                });

                this.children.emailMessage = new ControlGroup({
                    className: 'control-group',
                    controlType: 'Textarea',
                    controlOptions: {
                        modelAttribute: 'action.email.message.' + this.options.suffix,
                        model: this.model.state,
                        placeholder: _('Default').t(),
                        ariaLabel: _("Message").t(),
                        textareaClassName: 'messagearea'
                    },
                    label: _('Message').t()
                });

                if (this.options.includeControls && this.options.includeControls.length) {
                    this.children.emailInclude = new ControlGroup({
                        controlClass: 'email-include',
                        controlsLayout: 'wrap',
                        controls: this.options.includeControls,
                        label: _('Include').t()
                    });
                }

                this.children.emailContentType = new ControlGroup({
                    className: 'control-group',
                    controlType: 'SyntheticRadio',
                    controlOptions: {
                        modelAttribute: 'action.email.content_type',
                        model: this.model.state,
                        items: [
                            { label: _('HTML & Plain Text').t(), value: 'html' },
                            { label: _('Plain Text').t(), value: 'plain' }
                        ]
                    },
                    label: _('Type').t()
                });
            },
            events: {
                'click a.show-cc-bcc': function(e) {
                    var force = true;
                    this.showAdditionalEmailAddresses(force);
                    e.preventDefault();
                }
            },
            showAdditionalEmailAddresses: function(force) {
                if (force || this.model.state.get('action.email.cc') || this.model.state.get('action.email.bcc')) {
                    this.children.ccEmailAddresses.$el.show();
                    this.children.bccEmailAddresses.$el.show();
                    this.children.toEmailAddresses.$('a.show-cc-bcc').css('display','none');
                } else {
                    this.children.toEmailAddresses.$('a.show-cc-bcc').css('display','block');
                }
            },
            render: function()  {
                this.children.toEmailAddresses.render().appendTo(this.$el);
                this.children.ccEmailAddresses.render().appendTo(this.$el).$el.hide();
                this.children.bccEmailAddresses.render().appendTo(this.$el).$el.hide();
                this.children.emailPriority.render().appendTo(this.$el);
                this.children.emailSubject.render().appendTo(this.$el);
                this.children.emailMessage.render().appendTo(this.$el);
                if (this.children.emailInclude) {
                    this.children.emailInclude.render().appendTo(this.$el);
                }
                this.children.emailContentType.render().appendTo(this.$el);

                this.showAdditionalEmailAddresses();
                return this;
            }
        });
});
