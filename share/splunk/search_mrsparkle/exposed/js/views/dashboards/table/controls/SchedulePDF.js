define(
    [
        'module',
        'jquery',
        'underscore',
        'backbone',
        'util/console',
        'util/pdf_utils',
        'models/services/ScheduledView',
        'models/shared/Cron',
        'views/Base',
        'views/shared/Modal',
        'views/shared/controls/ControlGroup',
        'views/shared/EmailOptions',
        'views/shared/ScheduleSentence',
        'views/shared/FlashMessages',
        'uri/route',
        './SchedulePDF.pcss'
    ],
    function (module,
              $,
              _,
              Backbone,
              console,
              pdfUtils,
              ScheduledViewModel,
              Cron,
              BaseView,
              Modal,
              ControlGroup,
              EmailOptions,
              ScheduleSentence,
              FlashMessagesView,
              route,
              css) {

        var ControlWrapper = BaseView.extend({
            render: function () {
                if (!this.el.innerHTML) {
                    this.$el.html(_.template(this.template, {
                        label: this.options.label || '',
                        controlClass: this.options.controlClass || '',
                        body: _.template(this.options.body || '')(this.model ? (this.model.toJSON ? this.model.toJSON() : this.model) : {})
                    }));
                }
                var target = this.$('.controls');
                _.each(this.options.children, function (child) {
                    child.render().appendTo(target);
                });
                return this;
            },
            template: '<label class="control-label"><%- label %></label><div class="controls <%- controlClass %>"><%= body %></div>'
        });


        return Modal.extend({
            moduleId: module.id,
            className: 'modal schedule-pdf modal-wide',
            /**
             * @param {Object} options {
             *     model: {
             *         scheduledView: <models.services.ScheduledView>,
             *         dashboard: <models.services.data.ui.Views>
             *     }
             * }
             */
            initialize: function () {
                Modal.prototype.initialize.apply(this, arguments);


                this.model.inmem = new ScheduledViewModel.Entry.Content(this.model.scheduledView.entry.content.toJSON());
                // default come froma different model.  Since this is async, we should only do as needed
                if (!this.model.inmem.get('action.email.papersize')) {
                    pdfUtils.getEmailAlertSettings().done(_.bind(function (emailSettings) {
                        // Since async souble check that user hasn't set this yet
                        if (!this.model.inmem.get('action.email.papersize')) {
                            this.model.inmem.set('action.email.papersize', emailSettings.entry.content.get('reportPaperSize'));
                        }
                    }, this));
                }
                if (!this.model.inmem.get('action.email.paperorientation')) {
                    pdfUtils.getEmailAlertSettings().done(_.bind(function (emailSettings) {
                        // Since async souble check that user hasn't set this yet
                        if (!this.model.inmem.get('action.email.paperorientation')) {
                            this.model.inmem.set('action.email.paperorientation', emailSettings.entry.content.get('reportPaperOrientation'));
                        }
                    }, this));
                }
                var cronModel = this.model.cron = Cron.createFromCronString(this.model.inmem.get('cron_schedule') || '0 6 * * 1');
                this.listenTo(cronModel, 'change', function () {
                    this.model.inmem.set('cron_schedule', cronModel.getCronString());
                }, this);

                //reset flashmessages to clear pre-existing flash messages on 'cancel' or 'close' of dialog
                this.on('hide', this.model.scheduledView.error.clear, this.model.scheduledView.error);

                var helpLink = route.docHelp(
                    this.model.application.get("root"),
                    this.model.application.get("locale"),
                    'learnmore.alert.email'
                );

                this.children.flashMessages = new FlashMessagesView({
                    model: {
                        scheduledView: this.model.scheduledView,
                        content: this.model.inmem
                    }
                });

                this.children.name = new ControlGroup({
                    controlType: 'Label',
                    controlOptions: {
                        modelAttribute: 'label',
                        model: this.model.dashboard.entry.content
                    },
                    label: _('Dashboard').t()
                });

                this.children.schedule = new ControlGroup({
                    controlType: 'SyntheticCheckbox',
                    controlOptions: {
                        modelAttribute: 'is_scheduled',
                        model: this.model.inmem,
                        save: false
                    },
                    label: _("Schedule PDF").t()
                });

                this.children.scheduleSentence = new ScheduleSentence({
                    model: {
                        cron: this.model.cron,
                        application: this.model.application
                    },
                    lineOneLabel: _("Schedule").t(),
                    popdownOptions: {
                        attachDialogTo: '.modal:visible',
                        scrollContainer: '.modal:visible .modal-body:visible'
                    }
                });

                this.children.emailOptions = new EmailOptions({
                    model: {
                        state: this.model.inmem,
                        application: this.model.application
                    },
                    toLabel: _('Email To').t(),
                    suffix: 'view'
                });

                this.children.paperSize = new ControlGroup({
                    className: 'control-group',
                    controlType: 'SyntheticSelect',
                    controlOptions: {
                        modelAttribute: 'action.email.papersize',
                        model: this.model.inmem,
                        items: [
                            { label: _("A2").t(), value: 'a2' },
                            { label: _("A3").t(), value: 'a3' },
                            { label: _("A4").t(), value: 'a4' },
                            { label: _("A5").t(), value: 'a5' },
                            { label: _("Letter").t(), value: 'letter' },
                            { label: _("Legal").t(), value: 'legal' }
                        ],
                        save: false,
                        toggleClassName: 'btn',
                        popdownOptions: {
                            attachDialogTo: '.modal:visible',
                            scrollContainer: '.modal:visible .modal-body:visible'
                        }
                    },
                    label: _("Paper Size").t()
                });

                this.children.paperLayout = new ControlGroup({
                    controlType: 'SyntheticRadio',
                    controlOptions: {
                        modelAttribute: 'action.email.paperorientation',
                        model: this.model.inmem,
                        items: [
                            { label: _("Portrait").t(), value: 'portrait' },
                            { label: _("Landscape").t(), value: 'landscape' }
                        ],
                        save: false
                    },
                    label: _("Paper Layout").t()
                });

                this.children.previewLinks = new ControlWrapper({
                    body: '<div class="preview-actions">' +
                    '<div class="test-email"><a href="#" class="action-send-test">' + _("Send Test Email").t() + '</a></div> ' +
                    '<a href="#" class="action-preview">' + _("Preview PDF").t() + '</a>' +
                    '</div>'
                });

                this.model.inmem.on('change:is_scheduled', this._toggle, this);
            },
            events: $.extend({}, Modal.prototype.events, {
                'click .action-send-test': function (e) {
                    e.preventDefault();
                    this.model.inmem.validate();
                    if (this.model.inmem.isValid()) {
                        var $status = this.$('.test-email'), flashMessages = this.children.flashMessages.flashMsgCollection;
                        $status.html(_("Sending...").t());
                        pdfUtils.sendTestEmail(
                            this.model.dashboard.entry.get('name'),
                            this.model.dashboard.entry.acl.get('app'),
                            this.model.inmem.get('action.email.to'),
                            {
                                ccEmail: this.model.inmem.get('action.email.cc'),
                                bccEmail: this.model.inmem.get('action.email.bcc'),
                                emailSubject: this.model.inmem.get('action.email.subject.view'),
                                emailMessage: this.model.inmem.get('action.email.message.view'),
                                paperSize: this.model.inmem.get('action.email.papersize'),
                                paperOrientation: this.model.inmem.get('action.email.paperorientation'),
                                sendTestEmail: '1'
                            }
                        ).done(function () {
                            $status.html('<i class="icon-check"></i> ' + _("Email sent.").t());
                        }).fail(function (error) {
                            $status.html('<span class="error"><i class="icon-warning-sign"></i> ' + _("Failed!").t() + '</span>');
                            if (error) {
                                flashMessages.add({
                                    type: 'warning',
                                    html: _("Sending the test email failed: ").t() + _.escape(error)
                                });
                            }
                        }).always(function () {
                            setTimeout(function () {
                                $status.html('<a href="#" class="action-send-test">' + _("Send Test Email").t() + '</a>');
                            }, 5000);
                        });
                    }
                },
                'click .action-preview': function (e) {
                    e.preventDefault();
                    var orientationSuffix = '',
                        orientation = this.model.inmem.get('action.email.paperorientation'),
                        pageSize = this.model.inmem.get('action.email.papersize') || 'a2';
                    if (orientation === 'landscape') {
                        orientationSuffix = '-landscape';
                    }
                    pdfUtils.getRenderURL(
                        this.model.dashboard.entry.get('name'), this.model.dashboard.entry.acl.get('app'), {
                            'paper-size': pageSize + orientationSuffix,
                            'inline': '1'
                        }
                    ).done(function (url) {
                        window.open(url);
                    });
                },
                'click .modal-btn-primary': function (e) {
                    e.preventDefault();
                    this.model.inmem.validate();
                    if (this.model.inmem.isValid()) {
                        //use == instead of === in first part of conditional to cover false and 0
                        if (this.model.inmem.get('is_scheduled') == false && this.model.scheduledView.entry.content.get('is_scheduled') === false) {
                            this.hide();
                        } else {
                            this.model.scheduledView.entry.content.set(this.model.inmem.toJSON());
                            var modal = this;
                            this.model.scheduledView.save({}, {
                                success: function () {
                                    modal.hide();
                                },
                                error: function(model) {
                                    //reset model.entry.content to previous state when there is an error in saving.
                                    model.entry.content.set(model.entry.content.previousAttributes());
                                }
                            });
                        }
                    }
                }
            }),
            _toggle: function () {
                var action = this.model.inmem.get('is_scheduled') ? 'show' : 'hide';
                this.children.scheduleSentence.$el[action]();
                this.$emailOptions[action]();
                this.children.paperSize.$el[action]();
                this.children.paperLayout.$el[action]();
                this.children.previewLinks.$el[action]();

            },
            render: function () {
                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Edit PDF Schedule").t());
                this.children.flashMessages.render().prependTo(this.$(Modal.BODY_SELECTOR));
                this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL_COMPLEX);
                this.children.name.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));
                this.children.schedule.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));

                this.children.scheduleSentence.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));

                this.$(Modal.BODY_FORM_SELECTOR).append('<fieldset class="email-options outline"></fieldset>');
                this.$emailOptions = this.$el.find('.email-options');
                this.children.emailOptions.render().appendTo(this.$emailOptions);

                this.children.paperSize.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));
                this.children.paperLayout.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));

                this.children.previewLinks.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));

                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_SAVE);
                this._toggle();
                return this;
            }
        });
    }
);
