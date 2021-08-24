import merge from 'lodash/merge';
import { defaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';

import { sprintf } from '@splunk/ui-utils/format';
import { _ } from '@splunk/ui-utils/i18n';

import ModalChangeStatusDefault from '@splunk/base-lister/modals/ChangeStatus';

// Update this to extend Component and pass handleChangeStatus in as a prop.
// Need to wait for BaseLister to be refactored to allow that.
class ModalChangeStatus extends ModalChangeStatusDefault {
    static propTypes = {
        ...ModalChangeStatusDefault.propTypes,
    };

    static defaultProps = {
        ...ModalChangeStatusDefault.defaultProps,
    };

    callFetch = () => fetch(`${this.props.objectsCollectionPath}/${this.props.object[
            this.props.idAttribute
        ]
            .split('/')
            .pop()}?output_mode=json`,
        merge({}, defaultFetchInit, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: sprintf('disabled=%s',
                this.props.object.content.disabled === true ? '0' : '1'),
        }))
        .then(handleResponse(200))
        .catch(handleError(_('Something went wrong.')));

    handleChangeStatus = () => {
        this.callFetch()
            .then(() => {
                this.handleSuccess();
                this.props.handleRefreshListing();
            }, (error) => {
                this.setState({
                    isWorking: false,
                    errorMessage: this.props.errorFormatter(sprintf(
                        _('Could not %s %s.'),
                        this.actionLabel.toLowerCase(),
                        this.props.objectNameSingular.toLowerCase(),
                    ), error.message),
                });
            });
    };
}

export default ModalChangeStatus;