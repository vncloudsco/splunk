import $ from 'jquery';
import Backbone from 'backbone';
import PropTypes from 'prop-types';
import Federations from './Federations';

import './DataFabric.pcss';

const DataFabricContainer = ({ collection }) => {
    const federationPage = new Federations({
        collection: {
            federations: collection.federations,
            fshRoles: collection.fshRoles,
        },
    });

    federationPage.render().appendTo($('.main-section-body'));
    return null;
};

DataFabricContainer.propTypes = {
    collection: PropTypes.shape({
        federations: PropTypes.instanceOf(Backbone.Collection).isRequired,
        fshRoles: PropTypes.instanceOf(Backbone.Collection).isRequired,
    }).isRequired,
};

export default DataFabricContainer;
