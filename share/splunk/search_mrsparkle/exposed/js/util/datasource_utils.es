
/* eslint-disable import/prefer-default-export */
/**
 * Pairing the data sources and its provider(search Job or searchmanager)
 * @param dataSources
 * @param providers
 * @param providerIdGetter
 */
export const pairDataSourcesWithProviders = (dataSources = [], providers = [], providerTypeGetter = p => p.name) => {
    const match = {};
    const orphanedDataSources = [];
    let orphanedProviders = providers;
    dataSources.forEach((ds) => {
        const provider = orphanedProviders.find(t => providerTypeGetter(t) === ds.name);
        if (provider) {
            orphanedProviders = orphanedProviders.filter(p => p !== provider);
            match[ds.name] = {
                dataSource: ds,
                provider,
            };
        } else {
            orphanedDataSources.push(ds);
        }
    });
    return {
        match,
        orphanedDataSources,
        orphanedProviders,
    };
};
/* eslint-enable import/prefer-default-export */
