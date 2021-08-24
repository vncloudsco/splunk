'''
General module for defining Splunkd server component configuration information
'''

from splunk.models.base import SplunkRESTModel, Field, BoolField


class SplunkdConfig(SplunkRESTModel):
    '''
    Represents the base Splunkd server configuration.  All fields are 
    read-only.
    '''

    # define endpoint
    resource_default = 'server/info'

    # define fields
    build               = Field()
    guid                = Field()
    is_free             = BoolField(api_name='isFree')
    is_trial            = BoolField(api_name='isTrial')
    license_signature   = Field(api_name='licenseSignature')
    license_state       = Field(api_name='licenseState')
    server_name         = Field(api_name='serverName')
    version             = Field()



class PDFConfig(SplunkRESTModel):
    '''
    Represents the pdfgen configuration. This is currently embedded
    in the email alert action stanza.
    '''

    # define endpoint
    resource_default = 'admin/conf-alert_actions/email'

    # define fields
    paper_orientation   = Field(api_name='reportPaperOrientation')
    paper_size          = Field(api_name='reportPaperSize')

