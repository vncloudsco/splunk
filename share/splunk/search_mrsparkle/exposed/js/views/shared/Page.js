define(
    [
        'underscore',
        'jquery',
        'module',
        'views/Base',
        'views/shared/splunkbar/Master',
        'views/shared/litebar/Master',
        'views/shared/litebar/BannerContent',
        'views/shared/appbar/Master',
        'views/shared/instrumentation/optinmodal/Master',
        'views/shared/notification/Notification',
        'helpers/TourHelper'
    ],
    function(
        _,
        $,
        module,
        BaseView,
        SplunkBarView,
        SplunkBarSideView,
        BannerContentView,
        AppBarView,
        OptInModal,
        NotificationModal,
        TourHelper
    ) {
        var PageView = BaseView.extend({
            moduleId: module.id,
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.useSideNav = this.model.user.canUseSidenav();

                if (this.useSideNav) {
                    this.children.sideNav = SplunkBarSideView.create({
                        model: {
                            application: this.model.application,
                            appNav: this.model.appNav,
                            appLocal: this.model.appLocal,
                            user: this.model.user,
                            serverInfo: this.model.serverInfo,
                            config: this.model.config,
                            updateChecker: this.model.updateChecker,
                            userPref: this.model.userPref,
                            webConf: this.model.web
                        },
                        collection: this.collection
                    });

                    this.children.bannerContent = new BannerContentView({
                        collection: this.collection
                    });
                } else {
                    if (this.options.splunkBar) {
                        this.children.splunkBar = SplunkBarView.create({
                            model: {
                                application: this.model.application,
                                appNav: this.model.appNav,
                                appLocal: this.model.appLocal,
                                user: this.model.user,
                                serverInfo: this.model.serverInfo,
                                config: this.model.config,
                                updateChecker: this.model.updateChecker,
                                userPref: this.model.userPref
                            },
                            collection: this.collection,
                            showAppsList: this.options.hasOwnProperty("showAppsList") ? this.options.showAppsList : true
                        });
                    }
                    if (this.options.showAppNav !== false &&
                        this.model.appNav || this.options.showAppNav) {
                        this.children.appBar = AppBarView.create({
                            section: this.options.section || '',
                            model: {
                                application: this.model.application,
                                appNav: this.model.appNav,
                                user: this.model.user,
                                serverInfo: this.model.serverInfo
                            },
                            collection: this.collection
                        });
                    }
                }
            },
            render: function() {
                this.renderLoadingMessage();
                this.renderHeader();
                // If we're on cloud, or the user does not have the capability to edit instrumentation settings,
                // just skip trying to load the opt-in modal.
                var notCloud = this.model.serverInfo && !this.model.serverInfo.isCloud(),
                    hasInstrumentationCapability = this.model.user && this.model.user.canEditInstrumentation && this.model.user.canEditInstrumentation();
                if (notCloud && hasInstrumentationCapability) {
                    this.renderOptInModal();
                } else {
                    this.renderTour();
                }

                return this;
            },
            renderHeader: function() {
                if (this.useSideNav) {
                    this.$('header').append(this.children.sideNav.el);
                    var bannerContent = this.children.bannerContent.render();
                    this.$('header').prepend(bannerContent.el);
                    bannerContent.$el.hide();
                } else {
                    if (this.options.splunkBar) {
                        this.$('header').append(this.children.splunkBar.render().el);
                    }
                    if (this.options.showAppNav !== false &&
                        this.model.appNav || this.options.showAppNav) {
                        this.$('header').append(this.children.appBar.el);
                    }
                }
            },
            renderOptInModal: function() {
                this.children.optInModal = new OptInModal({
                    model: {
                        application: this.model.application,
                        userPref: this.model.userPref,
                        optIn: this.model.optIn
                    },
                    onHide: function() {
                        // Show tour modal after opt in modal is hidden.
                        this.renderTour();
                    }.bind(this)
                });
                this.children.optInModal.render().appendTo($("body"));
            },
            skipOptInModal: function() {
                if (this.children.optInModal) {
                    this.children.optInModal.hide(true);
                }
            },
            renderNotification: function() {
                var notCloud = this.model.serverInfo && !this.model.serverInfo.isCloud(),
                    isAdmin = this.model.user.isAdmin(),
                    shouldShowNotification = this.model.userPref.shouldShowNotification();
                
                if (notCloud && isAdmin && shouldShowNotification) {
                    this.children.notificationModal = new NotificationModal({
                        model: {
                            userPref: this.model.userPref,
                            application: this.model.application
                        }
                    });
                    this.children.notificationModal.render().appendTo($("body"));
                }
            },
            renderTour: function() {
                if (!TourHelper.tour) {
                    TourHelper.renderTour(this.model.tour, this.model.application, this.model.user, this.collection.tours);
                }
                // Show notification modal if tour modal is not shown
                if (!this.model.tour || !this.model.tour.entry.get('name') || this.model.tour.isDisabled()) {
                    this.renderNotification();
                }
            },
            killTour: function() {
                TourHelper.killTour();
            },
            renderLoadingMessage: function() {
                var html = this.compiledTemplate({
                    loadingMessage: this.options.loadingMessage || '',
                    _: _
                });
                this.$el.html(html);
            },
            template: '\
                <a aria-label="<%- _("Screen reader users, click here to skip the navigation bar").t() %>"\
                    class="navSkip" href="#navSkip" tabIndex="1"><%- _("Skip Navigation").t() %> &gt;\
                </a>\
                <header role="banner"></header>\
                <div id="navSkip" tabindex="-1"></div> \
                <div class="main-section-body" role="main">\
                    <% if (loadingMessage) { %>\
                        <div class="loading-message"><%- loadingMessage %></div>\
                    <% } %>\
                </div>\
            '
        });

        return PageView;
    }
);
