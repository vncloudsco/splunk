import LabelControl from 'views/shared/controls/LabelControl';
import SplunkInputBase from './SplunkInputBase';

const proto = Object.create(SplunkInputBase, {

    createdCallback: {
        value(...args) {
            SplunkInputBase.createdCallback.apply(this, args);
        },
    },

    attachedCallback: {
        value(...args) {
            SplunkInputBase.attachedCallback.apply(this, args);
            this.view = new LabelControl({
                el: this,
                model: this.model,
                modelAttribute: 'value',
            });
            this.view.render();
        },
    },

    detachedCallback: {
        value(...args) {
            SplunkInputBase.detachedCallback.apply(this, args);
            if (this.view) {
                this.view.remove();
            }
        },
    },
});

document.registerElement('splunk-label', { prototype: proto });
