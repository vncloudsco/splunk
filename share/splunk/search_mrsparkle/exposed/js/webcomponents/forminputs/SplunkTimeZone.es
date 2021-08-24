import TimeZoneControl from 'views/shared/controls/TimeZone';
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
            this.view = new TimeZoneControl({
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

document.registerElement('splunk-timezone-input', { prototype: proto });
