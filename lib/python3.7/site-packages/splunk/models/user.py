from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField, ListField

class User(SplunkAppObjModel):
    '''
    Represents a Splunk user object.
    '''
    
    resource = 'authentication/users' 

    default_app                   = Field('defaultApp')
    default_app_is_user_override  = BoolField('defaultAppIsUserOverride', is_mutable=False)
    default_app_source_role       = Field('defaultAppSourceRole', is_mutable=False)
    email                         = Field()
    password                      = Field()
    realname                      = Field()
    create_role                   = Field('createrole', is_mutable=False)
    roles                         = ListField(is_mutable=False)
    type                          = Field(is_mutable=False)

    @classmethod
    def get(self, uname):
        '''
        Overriden function lets retrieving user objects by user name instead of id
        '''
        return super(User, self).get('%s/%s' % (self.resource, uname))
