define(
    [
        'underscore',
        'backbone',
        'module',
        'views/Base',
        'views/shared/EmailOptions',
        'views/shared/controls/SyntheticCheckboxControl',
        'views/shared/controls/SyntheticSelectControl',
        'models/search/Report',
        'splunk.util',
        './SendEmailOptions.pcss'
    ],
    function(_,
        Backbone,
        module,
        Base,
        EmailOptions,
        SyntheticCheckboxControl,
        SyntheticSelectControl,
        ReportModel,
        splunkUtil,
        css
    ) {
        return Base.extend({
            moduleId: module.id,
            /**
             * @param {Object} options {
             *     model: {
             *         document: <models.search.Report>,
             *         application: <models.Application>
             *     }
             *     documentType: <String> The type of the document model, report|alert. 
             *         Defaults using the isAlert function to determine the type.
             *     pdfAvailable: <Boolean> If PDF generation is available.
             * }
             */
            tagName: 'form',
            className: 'form-horizontal form-complex sendemail-options',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);

                 var defaults = {
                    documentType: this.model.document.isAlert() ? ReportModel.DOCUMENT_TYPES.ALERT : ReportModel.DOCUMENT_TYPES.REPORT
                };

                _.defaults(this.options, defaults);

                var isAlert = (this.options.documentType === ReportModel.DOCUMENT_TYPES.ALERT),
                    documentTypeString = isAlert ? _("Alert").t() : _("Report").t(),
                    includeControls = [
                        new SyntheticCheckboxControl({
                            modelAttribute: 'action.email.include.view_link',
                            model: this.model.document.entry.content,
                            label: splunkUtil.sprintf(_('Link to %s').t(), documentTypeString)
                        }),
                        new SyntheticCheckboxControl({
                            modelAttribute: 'action.email.include.results_link',
                            model: this.model.document.entry.content,
                            label: _('Link to Results').t()
                        }),
                        new SyntheticCheckboxControl({
                            modelAttribute: 'action.email.include.search',
                            model: this.model.document.entry.content,
                            label: _('Search String').t()
                        }),
                        new SyntheticCheckboxControl({
                            additionalClassNames: 'include-inline',
                            modelAttribute: 'action.email.inline',
                            model: this.model.document.entry.content,
                            label: _('Inline').t()
                        }),
                        new SyntheticSelectControl({
                            additionalClassNames: 'include-inline-format',
                            modelAttribute: 'action.email.format',
                            menuWidth: 'narrow',
                            model: this.model.document.entry.content,
                            items: [
                                { label: _('Table').t(), value: 'table' },
                                { label: _('Raw').t(), value: 'raw' },
                                { label: _('CSV').t(), value: 'csv' }
                            ],
                            labelPosition: 'outside',
                            popdownOptions: {
                                attachDialogTo: '.modal:visible',
                                scrollContainer: '.modal:visible .modal-body:visible'
                            }
                        })
                    ];

                if (isAlert) {
                    includeControls.push(
                        new SyntheticCheckboxControl({
                            modelAttribute: 'action.email.include.trigger',
                            model: this.model.document.entry.content,
                            label: _('Trigger Condition').t()
                        })
                    );
                }

                includeControls.push(
                    new SyntheticCheckboxControl({
                        modelAttribute: 'action.email.sendcsv',
                        model: this.model.document.entry.content,
                        label: _('Attach CSV').t()
                    })
                );

                if (isAlert) {
                    includeControls.push(
                        new SyntheticCheckboxControl({
                            modelAttribute: 'action.email.include.trigger_time',
                            model: this.model.document.entry.content,
                            label: _('Trigger Time').t()
                        })
                    );
                }
                
                if (this.options.pdfAvailable) {
                    includeControls.push(
                        new SyntheticCheckboxControl({
                            modelAttribute: 'action.email.sendpdf',
                            model: this.model.document.entry.content,
                            label: _('Attach PDF').t()
                        })
                    );
                }

                this.children.emailOptions = new EmailOptions({
                    model: {
                        state: this.model.document.entry.content,
                        application: this.model.application
                    },
                    includeControls: includeControls,
                    suffix: this.options.documentType,
                    includeSubjectDefaultPlaceholder: true
                });

                this.model.document.entry.content.on('change:action.email.format', function(){
                    if (!this.model.document.entry.content.get('action.email.inline')) {
                        this.model.document.entry.content.set('action.email.inline', 1);
                    }
                }, this);
            },
            render: function()  {
                this.children.emailOptions.render().appendTo(this.$el);
                return this;
            }
        });
});
