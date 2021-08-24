define (
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/shared/Modal',
        'views/shared/FlashMessages',
        'util/format_numbers_utils',
        'splunk.util'
    ],
    function(
        $,
        _,
        module,
        BaseView,
        ModalView,
        FlashMessage,
        numUtils,
        splunkUtils
    ){
        return BaseView.extend({

            moduleId: module.id,

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.children.flashMessage = new FlashMessage({ model: this.model.tstatsSummarization });
            },

            events: {
                'click .modal-btn-primary:not(.disabled)': function(e) {
                    this.submit();
                    e.preventDefault();
                }
            },

            submit: function() {
                this.$rebuildButton = this.$('.modal-btn-primary');
                this.$rebuildButton.addClass('disabled');
                var resultXHR = this.model.tstatsSummarization.destroy();
                $.when(resultXHR).then(
                    function() {
                        this.trigger('closeModal');
                    }.bind(this),
                    function() {
                        this.trigger('failedRebuild');
                    }.bind(this));
            },

            render: function() {
                var summarySize = this.model.tstatsSummarization.entry.content.get("summary.size");
                var rebuildButton = '<a href="#" class="btn btn-primary modal-btn-primary pull-right">' + _('Rebuild').t() + '</a>';
                this.$el.html(ModalView.TEMPLATE);
                this.$(ModalView.HEADER_TITLE_SELECTOR).html(_("Rebuild Data Model Summary").t());
                $(_.template(this.warningTemplate, {
                    _: _,
                    summarySizeString: numUtils.bytesToFileSize(summarySize),
                    splunkUtils: splunkUtils
                })).appendTo(this.$(ModalView.BODY_SELECTOR));
                this.$(ModalView.FOOTER_SELECTOR).append(ModalView.BUTTON_CANCEL);
                this.$(ModalView.FOOTER_SELECTOR).append(rebuildButton);
                this.children.flashMessage.render().prependTo(this.$(ModalView.BODY_SELECTOR));
                return this;
            },

            warningTemplate: '\
                <div class="alert alert-warning">\
                    <i class="icon-alert"></i>\
                    <%- splunkUtils.sprintf(_("If you carry out this rebuild operation,\
                     the Splunk software will delete the current acceleration summary (%s) \
                     for this data model and rebuild it.  If this data model has a large \
                     summary, this process can take a long time.").t(), summarySizeString) %> \
                    <div class="ask-confirmation"><%- _("Do you want to proceed and rebuild the summary for this datamodel anyway?").t() %></div>\
                </div>\
            '
        });
    });
