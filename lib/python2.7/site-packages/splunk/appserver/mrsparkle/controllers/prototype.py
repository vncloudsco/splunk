import cherrypy
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page

import formencode
from formencode import validators
import logging


logger = logging.getLogger('splunk.appserver.controllers.prototype')

class YearBornValidator(validators.FancyValidator):
    """
    An example of a custom form validator
    you can use this as
    userage = YearBornValidator()
    or
    yearborn = YearBornValidator(min_age=21, max_age=110)
    """
    min_age = 12
    max_age = 100
    messages = {
        'invalid': 'Please enter a valid year between %(minYear)i and %(maxYear)i',
    }
    def _to_python(self, value, state):
        import time
        thisyear = time.localtime()[0] 
        minyear = thisyear - self.max_age
        maxyear = thisyear - self.min_age
        try:
            year = int(value)
        except (ValueError, TypeError):
            raise formencode.api.Invalid(self.message('invalid', state, minYear=minyear, maxYear=maxyear), value, state)
        if year < minyear or year > maxyear: 
            raise formencode.api.Invalid(self.message('invalid', state, minYear=minyear, maxYear=maxyear), value, state)
        return year

    _from_python = _to_python


class TestForm(formencode.Schema):
    """
    Example form used with PrototypeController.form1
    Have a look at validators.py to see all the other available validators
    """
    allow_extra_fields = False
    email = validators.Email() # match an email address, could also add resolve_domain=True for additional checks
    name = formencode.All( # require all enclosed validators to pass, could also use formencode.Any
        validators.String(not_empty=True, min=2, max=50),
        validators.PlainText()
        )
    yearborn = YearBornValidator()



class PrototypeController(BaseController):
    """
    Handle experimental ideas and code
    """

    @expose_page(False, methods=['GET', 'POST'])
    def form1(self, **kw):
        """A simple example of using form validation"""
        form = TestForm()
        form_errors = {}
        form_defaults = {}
        error = None
        if cherrypy.request.method == 'POST':
            try:
                form_data = form.to_python(kw)
                return """Form Parsed OK"""
            except formencode.api.Invalid as e:
                form_defaults = kw
                if e.error_dict:
                    form_errors = e.error_dict
                else:
                    error = e.msg

        return self.render_template('prototype/form1.html', { 
                'error' : error,
                'form_defaults' : form_defaults,
                'form_errors' : form_errors
        })

    @expose_page(False)
    def sparklines(self):
        """Example jquery.sparkline.js usage"""
        return self.render_template('prototype/sparklines.html')

    @expose_page(False)
    def scroll_performance(self):
        """Test page for scroll bar performance testing"""
        return self.render_template('prototype/scroll_performance.html')

    @expose_page(False)
    def new_layout(self):
        return self.render_template('prototype/new_layout.html')
