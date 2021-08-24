import Main from '@splunk/base-lister/Main';
import PropTypes from 'prop-types';

class TokensMain extends Main {
    static propTypes = {
        ...Main.propTypes,
        checkTokenAuth: PropTypes.func.isRequired,
    };

    /**
     * Overwritting handleRefreshListing to check for token auth status before fetching items.
     */
    handleRefreshListing = (newData) => {
        this.props.checkTokenAuth();
        this.setState({
            fetchingCollection: true,
            fetchingCount: true,
            selectedRows: [],
            errorMessage: '',
        });
        this.handleRefreshListingInternal(newData);
    };
}

export default TokensMain;
