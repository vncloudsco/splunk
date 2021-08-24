define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'views/Base',
        'views/shared/controls/SyntheticCheckboxControl',
        'util/keyboard',
        'bootstrap.tooltip'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        BaseView,
        SyntheticCheckboxControl,
        KeyboardUtil
        //tooltip
    )
    {
        return BaseView.extend({
            moduleId: module.id,
            tagName: 'thead',
            className: 'table-head',
            /**
             * @param {Object} options {
             *     model: <Backbone.Model>
             *     or model: { // use this if using checkbox and it should be powered by a model different then other columns
             *            state <Backbone.Model>,
             *            checkbox <Backbone.Model>
             *     }
             * }
             */
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                var defaults = {
                    columns: [] // hash: label, sortKey (optional)
                };
                _.defaults(this.options, defaults);
                var model = this.model;
                this.model = {};
                this.model.state = model.state || model;
                if (model.checkbox) {
                    this.model.checkbox = model.checkbox;
                }
                this.activate();
            },
            events: {
                'click th': function(e) {
                    this.handleClick(e);
                    e.preventDefault();
                },
                'keyup th': function(e) {
                    if (e.which === KeyboardUtil.KEYS['ENTER']) {
                        this.handleClick(e);
                    }
                },
                'click th a': function(e) {
                    e.preventDefault();
                },
                'click a.tooltip-link': function(e) {
                    e.preventDefault();
                    $('.tooltip').remove();
                }
            },
            handleClick: function(e) {
                var $target = $(e.currentTarget),
                    sortKey = $target.attr('data-key'),
                    sortDirection = $target.hasClass('asc') ? 'desc': 'asc';
                if (!sortKey) {
                    return true;
                }
                this.model.state.set({sortKey: sortKey, sortDirection: sortDirection});
            },
            startListening: function() {
                this.listenTo(this.model.state, 'change:sortKey change:sortDirection', this.debouncedRender);
            },
            render: function() {
                var html = this.compiledTemplate({
                    _: _,
                    columns: this.options.columns,
                    model: this.model.state
                });
                this.$el.html(html);
                if (this.options.checkboxClassName) {
                    if (this.children.checkbox) {
                        this.children.checkbox.remove();
                    }
                    this.children.checkbox = new SyntheticCheckboxControl({
                        modelAttribute: 'selectAll',
                        model: this.model.checkbox || this.model.state
                    });
                    this.children.checkbox.render().appendTo(this.$('.' + this.options.checkboxClassName));
                }
                this.options.columns.forEach(function(column) {
                    if (column.tooltip) {
                        this.$('.' + column.className).find('.column-tooltip').tooltip({animation:false, title: column.tooltip, container: 'body'});
                    }
                }.bind(this));
                return this;
            },
            template: '\
                <tr class="">\
                    <% _.each(columns, function(value) { %>\
                        <% if (_.isFunction(value.visible) && !value.visible.call()) { return; } %>\
                        <% var sortableClassName = (value.sortKey) ? "sorts" : "" %>\
                        <% var activeClassName = model.get("sortKey") && value.sortKey==model.get("sortKey") ? "active " + model.get("sortDirection") : "" %>\
                        <th scope="col" data-key="<%- value.sortKey || "" %>"\
                            <% if (sortableClassName || value.label) { %>\
                                tabindex="<%- value.tabindex || 0 %>"\
                            <% } %>\
                            class="<%- sortableClassName %> <%- activeClassName %> <%- value.className || "" %>"\
                            <%- value.colSpan ? "colspan=" + value.colSpan : "" %>\
                            <% if (value.ariaLabel) { %>\
                                aria-label="<%- value.ariaLabel %>"\
                            <% } else if (value.label) { %>\
                                aria-label="<%- value.label %>"\
                            <% } %>\
                        >\
                        <% if (value.html) { %>\
                            <%= value.html %>\
                            <% if (value.sortKey) { %>\
                                <i class="icon-sorts <%- activeClassName %>"></i>\
                            <% } %>\
                        <% } else if (value.sortKey) { %>\
                            <a aria-hidden="true"><%- value.label %>\
                                <% if (value.tooltip) { %>\
                                    <a aria-hidden="true" href="#" class="column-tooltip tooltip-link"><%- _("?").t() %></a>\
                                <% } %>\
                                <i class="icon-sorts <%- activeClassName %>"></i>\
                            </a>\
                        <% } else { %>\
                                <%- value.label %>\
                            <% } %>\
                        </th>\
                    <% }) %>\
                </tr>\
            '
        });
    }
);
