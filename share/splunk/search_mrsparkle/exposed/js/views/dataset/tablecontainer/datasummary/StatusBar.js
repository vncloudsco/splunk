define(
    [
        'underscore',
        'jquery',
        'module',
        'models/datasets/DataSummarySearchJob',
        'views/Base',
        'views/shared/controls/SyntheticSelectControl',
        'views/shared/SearchResultsPaginator',
        'views/shared/delegates/Dock',
        'uri/route',
        'splunk.util',
        'splunk.window'
    ],
    function(
        _,
        $,
        module,
        DataSummarySearchJob,
        BaseView,
        SyntheticSelectControl,
        SearchResultsPaginator,
        Dock,
        route,
        splunkUtils,
        splunkWindow
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'data-summary-status-bar table-caption',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
            },

            events: {
                'click .cancel': function(e) {
                    e.preventDefault();

                    this.model.dataSummaryJob.handleJobDestroy();
                    this.model.dataSummaryJob.entry.content.set('dispatchState', DataSummarySearchJob.CANCELED);
                },

                'click .inspect': function(e) {
                    e.preventDefault();

                    splunkWindow.open(
                        route.jobInspector(
                            this.model.application.get('root'),
                            this.model.application.get('locale'),
                            this.model.application.get('app'),
                            this.model.dataSummaryJob.id
                        ),
                        'splunk_job_inspector',
                        {
                            width: 870,
                            height: 560,
                            menubar: false
                        }
                    );
                },

                'click .restart': function(e) {
                    e.preventDefault();

                    this.model.dataSummaryJob.trigger('restart');
                }
            },

            startListening: function() {
                this.listenTo(this.model.dataSummaryJob, 'jobProgress', this.render);
                this.listenTo(this.model.dataSummaryJob.entry.content, 'change:dispatchState', this.render);
            },

            getMessage: function() {
                var dispatchState = this.model.dataSummaryJob.entry.content.get('dispatchState'),
                    resultPreviewCount = this.model.dataSummaryJob.entry.content.get('resultPreviewCount'),
                    inspectText = _('Inspect').t(),
                    cancelText = _('Cancel').t(),
                    restartText = _('Restart').t(),
                    message;

                if (this.model.dataSummaryJob.isNew()) {
                    message = _('Summarize fields job is starting...').t();
                } else if (this.model.dataSummaryJob.isFailed()) {
                    message = splunkUtils.sprintf(_('Summarize fields job failed. %s').t(), '<a href="#" class="inspect" title="' + inspectText + '">' + inspectText + '</a>');
                } else if (dispatchState === DataSummarySearchJob.QUEUED) {
                    message = splunkUtils.sprintf(_('Summarize fields job is queued... %s').t(), '<a href="#" class="cancel" title="' + cancelText+ '">' + cancelText + '</a>');
                } else if (dispatchState === DataSummarySearchJob.PARSING) {
                    message = splunkUtils.sprintf(_('Summarize fields job is parsing... %s').t(), '<a href="#" class="cancel" title="' + cancelText + '">' + cancelText + '</a>');
                } else if (dispatchState === DataSummarySearchJob.RUNNING) {
                    message = splunkUtils.sprintf(_('Summarize fields job is running... %s').t(), '<a href="#" class="cancel" title="' + cancelText + '">' + cancelText + '</a>');
                } else if (dispatchState === DataSummarySearchJob.FINALIZING) {
                    message = splunkUtils.sprintf(_('Summarize fields job is finalizing... %s').t(), '<a href="#" class="cancel" title="' + cancelText + '">' + cancelText + '</a>');
                } else if (dispatchState === DataSummarySearchJob.CANCELED) {
                    message = splunkUtils.sprintf(_('Summarize fields job was cancelled. %s').t(), '<a href="#" class="restart" title="' + restartText + '">' + restartText + '</a>');
                } else if (dispatchState === DataSummarySearchJob.DONE) {
                    message = _('Summarize fields job is done!').t();
                }

                return message;
            },

            render: function() {
                this.$el.html(this.compiledTemplate({
                    _: _,
                    message: this.getMessage()
                }));

                this.children.dock = new Dock({
                    el: this.el,
                    affix: '.table-caption-inner'
                });

                return this;
            },

            template: '\
                <div class="table-caption-inner">\
                    <div class="message">\
                        <%= message %>\
                    </div>\
                </div>\
            '
        });
    }
);
