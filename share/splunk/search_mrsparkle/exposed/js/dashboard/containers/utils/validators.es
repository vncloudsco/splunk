import _ from 'underscore';
import splunkdUtil from 'splunk.util';

const sprintf = splunkdUtil.sprintf;

export const stringNotEmpty = (value) => {
    let error = '';
    if (!value) {
        error = _('is required').t();
    }
    return error;
};

export const numberWithInRange = (min, max) => (
    (value) => {
        let error = '';
        if (_.isNumber(value)) {
            if (value < min && value > max) {
                error = sprintf(_('should within range (%s,%s)').t(), min, max);
            }
        } else {
            error = _('expected a number').t();
        }
        return error;
    }
);

export const urlHasProtocol = (value) => {
    let error = '';
    if (!/^https?:\/\//.test(value)) {
        error = _('URL should start with http:// or https://').t();
    }
    return error;
};
