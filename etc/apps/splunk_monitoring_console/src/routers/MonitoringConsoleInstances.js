define(
    [
        'jquery',
        'underscore',
        'backbone',
        'routers/Base',
        'models/classicurl',
        'models/services/search/TimeParser',
        'splunk_monitoring_console/views/instances/Master'
    ],
    function(
        $,
        _,
        Backbone,
        BaseRouter,
        classicurl,
        TimeParser,
        InstancesView
    ) {
        return BaseRouter.extend({
            initialize: function() {
                BaseRouter.prototype.initialize.apply(this, arguments);
                this.fetchAppLocals = true;
                this.fetchVisualizations = true;
                this.fetchVisualizationFormatters = false;
                this.setPageTitle(_('Instances').t());
                this.loadingMessage = _('Loading...').t();
                this.classicurlDfd = $.Deferred();

                $.when(this.deferreds.appLocals).done(function() {
                    this.model.appLocal = this.collection.appLocals.find(function(appLocal) {
                        return appLocal.entry.get('name') === this.model.application.get('app');
                    }, this);
                }.bind(this));
            },
            page: function(locale, app, page) {
                BaseRouter.prototype.page.apply(this, arguments);
                classicurl.fetch().done(function() {
                    this.classicurlDfd.resolve();
                }.bind(this));

                // add navigation
                this.deferreds.pageViewRendered.done(function(){
                    if (this.shouldRender) {
                        $('.preload').replaceWith(this.pageView.el);

                        if (this.model.appLocal.entry.content.get('configured')) {
                            // Distributed Mode
                            $.when(this.classicurlDfd).done(function() {
                                // NOTE: here we need to convert from epoch to user's local time, thus we need to fetch TimeParser
                                // TODO: re-visit this logic in Ember
                                var earliest = classicurl.get('earliest');
                                var latest = classicurl.get('latest');
                                var earliestDfd = $.Deferred();
                                var latestDfd = $.Deferred();
                                var earliestModel = new TimeParser();
                                var latestModel = new TimeParser();

                                if (earliest && latest) {
                                    earliestModel.fetch({
                                        data: {
                                            time: earliest
                                        }
                                    }).done(function() {
                                            earliestDfd.resolve();
                                        });
                                    latestModel.fetch({
                                        data: {
                                            time: latest
                                        }
                                    }).done(function() {
                                            latestDfd.resolve();
                                        });
                                }
                                else {
                                    earliestDfd.resolve();
                                    latestDfd.resolve();
                                }

                                $.when(earliestDfd, latestDfd).done(function() {
                                    this.instancesView = new InstancesView({
                                        model: {
                                            appLocal: this.model.appLocal,
                                            application: this.model.application,
                                            earliestModel: earliestModel,
                                            latestModel: latestModel
                                        }
                                    });
                                    $('.main-section-body').replaceWith(this.instancesView.render().$el);
                                }.bind(this));
                            }.bind(this));
                        }
                        else {
                            // Standalone Mode
                            window.location.href = 'standalone';
                        }

                    }
                }.bind(this));
            }
        });
    }
);
