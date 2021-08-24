import socket
import smtplib
import splunk.mining.dcutils as dcu

logger = dcu.getLogger()

class SecureSMTP(smtplib.SMTP):
    """
        Subclass the SMTP library to wrap create the secure connection using the
        ssl.SSLContext.wrap_socket API instead of the ssl.wrap_socket API.
        We need to change the way we setup a secure connection (starttls),
        how we send and receive data when using that secure connection.
    """

    def starttls(self, sslContext=None):
        """Puts the connection to the SMTP server into TLS mode.

        If there has been no previous EHLO or HELO command this session, this
        method tries ESMTP EHLO first.

        If the server supports TLS, this will encrypt the rest of the SMTP
        session. If you provide the keyfile and certfile parameters,
        the identity of the SMTP server and client can be checked. This,
        however, depends on whether the socket module really checks the
        certificates.

        This method may raise the following exceptions:

         SMTPHeloError            The server didn't reply properly to
                                  the helo greeting.

        :param sslContext: An ssl.SSLContext object used by the connection
        """

        self.ehlo_or_helo_if_needed()
        if not self.has_extn("starttls"):
            raise smtplib.SMTPException("STARTTLS extension not supported by server.")
        if sslContext == None:
            raise ValueError("starttls() requires a sslContext parameter.")
        (resp, reply) = self.docmd("STARTTLS")

        logger.debug('STARTTLS response = %d' % resp)

        if resp == 220:
            # smtplib calls ssl.wrap_socket(self.sock, keyfile, certfile)
            # Switch to use ssl.SSLContext.wrap_socket(socket) since it exposes
            # more ssl settings
            self.sock = sslContext.wrap_socket(self.sock)
            self.file = self.sock.makefile('rb')

            # RFC 3207:
            # The client MUST discard any knowledge obtained from
            # the server, such as the list of SMTP service extensions,
            # which was not obtained from the TLS negotiation itself.
            self.helo_resp = None
            self.ehlo_resp = None
            self.esmtp_features = {}
            self.does_esmtp = 0
        return (resp, reply)

class SecureSMTP_SSL(SecureSMTP):
    """
        This is a subclass derived from SecureSMTP that connects over an SSL
        encrypted socket. It requires passing in a ssl.SSLContext object
    """

    default_port = smtplib.SMTP_SSL_PORT

    def __init__(self, host='', port=0, local_hostname=None,
                 sslContext=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):

        if sslContext == None:
            raise ValueError("SecureSMTP_SSL requires a sslContext parameter.")
        self.sslContext = sslContext
        SecureSMTP.__init__(self, host, port, local_hostname, timeout)

    def _get_socket(self, host, port, timeout):
        logger.debug('connect: %s %s' % (host, port))
        new_socket = socket.create_connection((host, port), timeout)
        # smtplib calls ssl.wrap_socket(self.sock, keyfile, certfile)
        # Switch to use ssl.SSLContext.wrap_socket(socket) since it exposes
        # more ssl settings
        new_socket = self.sslContext.wrap_socket(new_socket)
        self.file = new_socket.makefile('rb')

        return new_socket


