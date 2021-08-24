define(
        [
            'jquery',
            'underscore',
            'module',
            'views/Base',
            'views/shared/controls/ControlGroup',
            'uri/route'
        ],
        function(
            $,
            _,
            module,
            Base,
            ControlGroup,
            route
        ) {
        return Base.extend({
            moduleId: module.id,
            className: 'form form-horizontal',
            /**
            * @param {Object} options {
            *        model: {
            *            inmem: <models.Report>,
            *            report: <models.Report>,
            *            application: <models.Application>
            *        }
            * }
            **/
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);

                //views
                if (this.model.report.isNew()) {
                    this.$el.addClass('form-complex');
                    this.children.nameInput = new ControlGroup({
                        controlType: 'Text',
                        controlOptions: {
                            modelAttribute: 'name',
                            model: this.model.inmem.entry.content
                        },
                        label: _('Report Title').t()
                    });
                } else {
                    this.children.nameLabel = new ControlGroup({
                        controlType: 'Label',
                        controlOptions: {
                            modelAttribute: 'name',
                            model: this.model.inmem.entry
                        },
                        label: _('Report').t()
                    });
                }

                // The view is populated with a new report model (so this is a create workflow) but is_scheduled
                // is already true then the checkbox is not needed. This is used for a create scheduled report workflow.
                if (!(this.model.report.isNew() && this.model.report.entry.content.get('is_scheduled'))) {
                    var checkBoxLabel = this.model.inmem.entry.content.get('disabled') ? _("Enable and Schedule Report").t() : _('Schedule Report').t(),
                        configScheduleHelpLink = route.docHelp(
                            this.model.application.get("root"),
                            this.model.application.get("locale"),
                            'learnmore.report.scheduled'
                        );

                    this.children.scheduleCheck = new ControlGroup({
                        controlType: 'SyntheticCheckbox',
                        controlOptions: {
                            modelAttribute: 'scheduled_and_enabled',
                            model: this.model.inmem
                        },
                        label: checkBoxLabel,
                        help: '<a href="' + configScheduleHelpLink + '" target="_blank">' + _("Learn More").t() + ' <i class="icon-external"></i></a>'
                    });
                }

            },
            render: function() {
                if (this.model.report.isNew()) {
                    this.children.nameInput.render().appendTo(this.$el);
                } else {
                    this.children.nameLabel.render().appendTo(this.$el);
                }

                if (this.model.inmem.entry.content.get('disabled')) {
                    this.$el.append('<div>' + _('This report is currently disabled.').t() + '</div>');
                }

                if (this.children.scheduleCheck) {
                    this.children.scheduleCheck.render().appendTo(this.$el);
                }

                return this;
            }
        });
    }
);
