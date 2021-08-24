define(
    [
        'underscore',
        'module',
        'views/shared/MultiStepModal',
        'views/shared/datasetcontrols/accelerationinfo/dialogs/rebuild/Confirmation',
        'views/shared/datasetcontrols/accelerationinfo/dialogs/rebuild/Failure'
    ],
    function(
        _,
        module,
        MultiStepModal,
        Confirmation,
        Failure
    ) {
        return MultiStepModal.extend({
            moduleId: module.id,

            initialize: function() {
                MultiStepModal.prototype.initialize.apply(this, arguments);

                this.children.confirmation = new Confirmation({
                    model: {
                        tstatsSummarization: this.model.tstatsSummarization
                    }
                });

                this.children.failure = new Failure();

                this.children.confirmation.on('closeModal', function() {
                    this.trigger('refreshRequested');
                    this.remove();
                }, this);

                this.children.confirmation.on('failedRebuild', function() {
                    this.stepViewStack.setSelectedView(this.children.failure);
                    this.children.failure.focus();
                }, this);
            },

            getStepViews: function() {
                return ([
                    this.children.confirmation,
                    this.children.failure
                ]);
            }
        });
    }
);