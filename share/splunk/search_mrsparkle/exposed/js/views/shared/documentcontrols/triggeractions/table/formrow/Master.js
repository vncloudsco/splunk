define(
    [
        'underscore',
        'views/Base',
        'views/shared/documentcontrols/triggeractions/table/formrow/SendEmailOptions',
        'views/shared/documentcontrols/triggeractions/table/formrow/RunScriptOptions',
        'views/shared/documentcontrols/triggeractions/table/formrow/ListOptions',
        'views/shared/documentcontrols/triggeractions/table/formrow/LookupOptions',
        'views/shared/documentcontrols/triggeractions/table/formrow/ModAlertOptions',
        'module',
        './Master.pcss'
    ], 
    function(
        _,
        BaseView,
        EmailOptionsView,
        RunScriptOptionsView,
        ListOptionsView,
        LookupControlsView,
        ModAlertOptionsView,
        module,
        css
    ) {
    return BaseView.extend({
        moduleId: module.id,
        tagName: 'tr',
        className: 'more-info',
        attributes: function() {
            return {
                'data-name': this.model.selectedAlertAction.entry.get('name')
            };
        },
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);

            this.children.sendEmailOptions = new EmailOptionsView({
                pdfAvailable: this.options.pdfAvailable,
                model: {
                    document: this.model.document,
                    application: this.model.application
                },
                documentType: this.options.documentType
            });

            this.children.runScriptOptions = new RunScriptOptionsView({
                model: {
                    document: this.model.document,
                    application: this.model.application
                }
            });

            this.children.listOptions = new ListOptionsView({
                model: {
                    alert: this.model.document
                }
            });

            this.children.lookupOptions = new LookupControlsView({
                model: {
                    document: this.model.document
                }
            });

            this.listenTo(this.model.selectedAlertAction, 'remove', this.remove);
        },
        render: function() {
            var actionName = this.model.selectedAlertAction.entry.get('name');
            this.$el.html(this.compiledTemplate({
                _: _
            }));

            switch (actionName) {
                case 'email':
                    this.children.sendEmailOptions.render().appendTo(this.$('td'));
                    break;
                case 'script':
                    this.children.runScriptOptions.render().appendTo(this.$('td'));
                    break;
                case 'list':
                    this.children.listOptions.render().appendTo(this.$('td'));
                    break;
                case 'lookup':
                    this.children.lookupOptions.render().appendTo(this.$('td'));
                    break;
                default:
                    this.children[actionName + 'ModAlertOptions'] = new ModAlertOptionsView({
                        model: {
                            document: this.model.document,
                            alertAction: this.model.selectedAlertAction,
                            alertActionUI: this.model.alertActionUI,
                            application: this.model.application
                        }
                    }).render().appendTo(this.$('td'));
                    break;
            }

            if (!this.model.selectedAlertAction.get('isExpanded')) {
                this.$el.hide();
            }

            return this;
        },
        template: '\
            <td colspan="2"></td>\
        '
    });
});

