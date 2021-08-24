import PropTypes from 'prop-types';
import BackboneAdapterBase from 'components/BackboneAdapterBase';
import { _ } from '@splunk/ui-utils/i18n';
import ErrorView from 'views/error/Master';
import Backbone from 'backbone';

class Error extends BackboneAdapterBase {
    getView() {
        return new ErrorView({
            model: {
                application: this.props.model.application,
                serverInfo: this.props.serverInfo,
                error: new Backbone.Model({
                    status: this.props.status,
                    message: this.props.message,
                }),
            },
        });
    }
}

Error.propTypes = {
    model: PropTypes.shape({
        application: PropTypes.shape({}),
        serverInfo: PropTypes.shape({}),
    }),
    status: PropTypes.string,
    message: PropTypes.string,
};

Error.defaultProps = {
    model: {
        application: new Backbone.Model({
            content: new Backbone.Model(),
        }),
        serverInfo: new Backbone.Model({
            content: new Backbone.Model(),
        }),
    },
    status: _('404 Not Found'),
    message: _('Page not found!'),
};

export default Error;
