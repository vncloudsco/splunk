define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'contrib/text!views/clustering/push/PushErrors.html',
    'views/clustering/push/PushErrors.pcss'
],
    function(
        $,
        _,
        module,
        BaseView,
        Template,
        css
        ) {
        return BaseView.extend({
            moduleId: module.id,
            template: Template,
            events: {
                'click .cluster-errors-more, .cluster-errors-less': function(e) {
                    e.preventDefault();
                    this.$('.cluster-errors-full, .cluster-errors-short').toggle();
                }
            },

            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);
                this.model.pushModel.on('tick', this.render, this);
            },

            digestErrors: function(pushErrors) {
                // flatten the list of errors
                var flatErrors = [];
                for (var i = 0; i < pushErrors.length; i++) {
                    if (_.isArray(pushErrors[i].errors)) {
                        for (var j = 0; j < pushErrors[i].errors.length; j++) {
                            flatErrors.push([pushErrors[i].label, pushErrors[i].errors[j]]);
                        }
                    } else {
                        flatErrors.push([pushErrors[i].label, pushErrors[i].errors]);
                    }
                }
                // concat labels for error text that is the same.
                var dedupLabels = [];
                var dedupErrors = [];
                _.each(flatErrors, function(error) {
                    var findDup = dedupErrors.indexOf(error[1]);
                    if (findDup !== -1) {
                        if (error[0]) {
                            dedupLabels[findDup].push(error[0]);
                        }
                    } else {
                        dedupLabels.push([error[0]]);
                        dedupErrors.push(error[1]);
                    }
                });
                // Only list up to 5 labels.
                var errors = [];
                for (i = 0; i < dedupLabels.length; i++) {
                    var error = '';
                    var labels = _.without(dedupLabels[i], undefined);
                    if (labels.length > 0 && labels.length <= 5) {
                        error = labels.join(', ') + ': ';
                    } else if (labels.length > 5) {
                        error = labels.slice(0, 5).join(', ') + _(', and more').t() + ': ';
                    }
                    error += dedupErrors[i];
                    errors.push(error);
                }
                return errors;
            },

            render: function() {
                var pushErrors = this.model.pushModel.get('errors') || [];
                
                var html = this.compiledTemplate({
                    errors: this.digestErrors(pushErrors),
                    maxErrors: 3
                });
                this.$el.html(html);
                this.$('.cluster-errors-full').hide();
            }
        });

    });