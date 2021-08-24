define(
    [
        'jquery',
        'underscore',
        'backbone',
        'views/Base',
        'splunkjs/mvc',
        'splunkjs/mvc/settings',
        'splunk.util',
        'mixins/viewlogging',
        'dashboard/mixins/ComponentBindingMixin'
    ],
    function($,
             _,
             Backbone,
             BaseView,
             mvc,
             Settings,
             SplunkUtil,
             ViewloggingMixin,
             ComponentBindingMixin) {

        var defaultViewOptions = {
            register: true // whether to register into mvc.Components
        };

        var sprintf = SplunkUtil.sprintf;
        var BaseDashboardView = BaseView.extend(_.extend({}, ViewloggingMixin, ComponentBindingMixin, {
            viewOptions: {},
            omitFromSettings: [],
            _uniqueIdPrefix: 'view_',
            /**
             * Creates a new view.
             *
             * @param options.id    (optional) ID of this view.
             *                      Defaults to an automatically generated ID.
             * @param options.el    (optional) Preexisting <div> in which this view
             *                      will be rendered.
             * @param options.settings
             *                      A Settings model instance to use instead of creating
             *                      our own.
             * @param options.settingsOptions
             *                      Initial options for this view's settings model.
             * @param options.*     Initial attributes for this view's settings model.
             *                      See subclass documentation for details.
             * @param settingsOptions
             *                      Initial options for this view's settings model.
             */
            constructor: function(options, settingsOptions) {
                options = options || {};
                settingsOptions = settingsOptions || {};

                options.settingsOptions = _.extend(
                    options.settingsOptions || {},
                    settingsOptions);

                // Internal property to track object lifetime.
                // With this flag we want to prevent invoking methods / code
                // on already removed instance.
                this._removed = false;

                // Get an ID or generate one
                if (!options.id) {
                    this.id = _.uniqueId(this._uniqueIdPrefix || 'view_');
                    this.autoId = true;
                } else {
                    this.id = options.id;
                    this.autoId = options.autoId || false;
                }
                this.options = _.extend({}, this.options, options);
                if (this.options.moduleId) {
                    this.moduleId = this.options.moduleId;
                }
                this.viewOptions = _.defaults(this.viewOptions, defaultViewOptions);
                var returned = BaseView.prototype.constructor.apply(this, arguments);
                // Register self in the global registry
                if (this.viewOptions.register) {
                    mvc.Components.registerInstance(this.id, this, {replace: settingsOptions.replace});
                }

                return returned;
            },
            /**
             * Initializes this view's settings model based on the contents of
             * this.options.
             *
             * Protected.
             */
            configure: function() {

                var settings = this.options.settings;
                if (settings && (settings instanceof Settings)) {
                    this.settings = settings;
                    // use the ownSettings flag to keep track of the ownership of this.settings,
                    // so that the view can decide whether to dispose this.settings or to just remove
                    // event listeners that are related to the view itself.
                    this.ownSettings = false;
                    return this;
                }

                // Reinterpret remaining view options as settings attributes.
                var localOmitFromSettings = (this.omitFromSettings || []).concat(
                    ['model', 'collection', 'el', 'attributes', 'className',
                        'tagName', 'events', 'settingsOptions', 'deferreds', 'autoId']);
                var settingsAttributes = _.omit(this.options, localOmitFromSettings);
                var settingsOptions = this.options.settingsOptions;

                // Now, we create our default settings model.
                this.settings = new Settings(settingsAttributes, settingsOptions);
                this.ownSettings = true;

                return this;
            },
            remove: function() {
                this._removed = true;

                /*
                 SPL-131532: should not call dispose() on settings model when this view doesn't own
                 the settings model, because in some cases settings model is shared across multiple
                 views. Calling dispose() will call deepOff() which will call off() with no arguments,
                 so that all event listeners are removed while the model itself is still there.

                 This causes problem in DashboardElement, this._settingsSync is two-way sync between
                 settings model and elementReport model. Now the event listeners (specifically 'change'
                 event listener) of settings model are removed, so that elementReport model will not
                 update when settings model changes, thus elementReport model and settings model are
                 out of sync.

                 This bug happens when switching between dashboard mode: edit -> view -> edit. When
                 edit -> view happens, Headers.js calls remove on ElementEditor.js, which calls this
                 function. So when view -> edit, settings and elementReport models are out of sync.
                 */
                if (this.ownSettings) {
                    this.settings.dispose();
                } else {
                    this.settings.off(null, null, this);
                }

                // Call our super class
                BaseView.prototype.remove.apply(this, arguments);

                // Remove it from the registry
                if (this.viewOptions.register && mvc.Components.get(this.id) === this) {
                    mvc.Components.revokeInstance(this.id);
                }

                return this;
            },
            dispose: function() {
                this.remove();
            },
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.configure();
            },
            /**
             * @param {string} classes Class names of a dom element. Note this is NOT a css selector.
             */
            createOrFind: function(classes, parent, tag) {
                classes = classes.split(' ');
                parent = parent || this.$el;
                tag = tag || "div";
                var selector = _(classes).map(function(clazz) {
                    return "." + clazz;
                }).join('');
                var $dom = parent.children(selector);
                if (!$dom.length) {
                    var domStr = sprintf('<%s class="%s"></%s>', tag, classes.join(' '), tag);
                    $dom = $(domStr).prependTo(parent);
                }
                return $dom;
            },
            addChild: function(component) {
                component.render().$el.appendTo(this.$el);
            },
            getChildElements: function(selector) {
                return _(this.$el.find(selector)).chain()
                    .map(function(el) {
                        return $(el).attr('id');
                    })
                    .map(_.bind(mvc.Components.get, mvc.Components))
                    .filter(_.identity)
                    .value();
            },
            render: function() {
                BaseView.prototype.render.apply(this, arguments);
                return this;
            },
            isEditMode: function() {
                return this.model.state.get('mode') == 'edit';
            },
            // layout manager will actually show or hide it
            show: function() {
                this.$el.removeClass('hidden').trigger('elementVisibilityChanged');
            },
            hide: function() {
                this.$el.addClass('hidden').trigger('elementVisibilityChanged');
            }
        }));
        return BaseDashboardView;
    }
);
