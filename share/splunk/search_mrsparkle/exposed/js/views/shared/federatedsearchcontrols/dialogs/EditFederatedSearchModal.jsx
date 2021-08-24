import React from 'react';
import _ from 'underscore';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import Modal from '@splunk/react-ui/Modal';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Button from '@splunk/react-ui/Button';
import Select from '@splunk/react-ui/Select';
import Text from '@splunk/react-ui/Text';
import SearchInput from 'views/shared/react/searchinput/SearchInput';
import UserModel from 'models/shared/User';
import FlashMessages from 'views/shared/react/FlashMessages';
// eslint-disable-next-line no-unused-vars
import css from 'views/shared/federatedsearchcontrols/dialogs/EditFederatedSearchModal.pcss';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name EditFederatedSearchModal
     * @extends {views.ReactAdapterBase}
     * @description A modal for editing an existing federated search.
     *
     * @param {Object} options
     * @param {Object} options.model The model supplied to this class
     * @param {Object} options.collection The collection supplied to this class
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.store = {};

        this.listenTo(this.model.state, 'change:open', this.render);
    },

    renderContent() {
        const contentModel = this.model.inmem.entry.content;
        const SplSearchInput = (
            <SearchInput
                model={{
                    user: this.model.user,
                    content: contentModel,
                    application: this.model.application,
                    searchAttribute: 'search',
                    searchAssistant: (this.model.user.getSearchAssistant() === UserModel.SEARCH_ASSISTANT.FULL)
                        ? UserModel.SEARCH_ASSISTANT.COMPACT
                        : undefined,
                }}
                collection={{
                    searchBNFs: this.collection.searchBNFs,
                }}
            />
        );
        const open = this.model.state.get('open');
        const name = this.model.inmem.entry.get('name');

        const description = contentModel.get('description');

        const federatedProviderName = contentModel.get('federated.provider');
        const federatedProvider = this.collection.federations.findByEntryName(federatedProviderName);
        if (!federatedProvider) {
            contentModel.set('federated.provider', undefined);
        }

        const providers = this.collection.federations.getNameItems().map(
            provider => <Select.Option key={provider.value} value={provider.value} label={provider.label} />,
        );
        return (
            <Modal
                data-test="edit-federated-search-modal"
                onRequestClose={this.options.onClose}
                open={open}
                style={{ width: '600px' }}
            >
                <Modal.Header
                    title={_('Edit Federated Search').t()}
                    onRequestClose={this.options.onClose}
                />
                <Modal.Body>
                    <FlashMessages
                        model={{
                            inmem: this.model.inmem,
                            content: contentModel,
                        }}
                    />
                    <ControlGroup label={_('Title').t()}>
                        <div
                            className="edit-federated-search-title"
                            data-test="title"
                            ref={
                                // eslint-disable-next-line no-return-assign
                                (c => (this.model.state.set('titleRef', c)))
                            }
                        >
                            {name}
                        </div>
                    </ControlGroup>
                    <ControlGroup label={_('Description').t()}>
                        <Text
                            data-test="description"
                            defaultValue={description}
                            autoFocus
                            placeholder={_('optional').t()}
                            onChange={this.options.onDescriptionChanged}
                        />
                    </ControlGroup>
                    <ControlGroup label={_('Search').t()}>
                        {SplSearchInput}
                    </ControlGroup>
                    <ControlGroup label={_('Federated Provider').t()}>
                        <Select
                            data-test="federated-provider"
                            defaultValue={federatedProvider && federatedProvider.id}
                            onChange={this.options.onProviderChanged}
                            placeholder={_('Select provider...').t()}
                        >
                            {providers}
                        </Select>
                    </ControlGroup>
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        data-test="cancel-button"
                        appearance="secondary"
                        onClick={this.options.onClose}
                        label={_('Cancel').t()}
                    />
                    <Button
                        data-test="save-button"
                        appearance="primary"
                        onClick={this.options.onSubmit}
                        label={_('Save').t()}
                    />
                </Modal.Footer>
            </Modal>
        );
    },

    getComponent() {
        return (
            <BackboneProvider store={this.store} model={this.model}>
                {this.renderContent()}
            </BackboneProvider>
        );
    },
});
