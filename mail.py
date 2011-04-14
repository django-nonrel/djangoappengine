from email.MIMEBase import MIMEBase
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ImproperlyConfigured
from google.appengine.api import mail as aeemail

def _send_deferred(message):
    message.send()

class EmailBackend(BaseEmailBackend):
    can_defer = False

    def send_messages(self, email_messages):
        num_sent = 0
        for message in email_messages:
            if self._send(message):
                num_sent += 1
        return num_sent

    def _copy_message(self, message):
        """Create and return App Engine EmailMessage class from message."""
        gmsg = aeemail.EmailMessage(sender=message.from_email,
                                    to=message.to,
                                    subject=message.subject,
                                    body=message.body)
        if message.extra_headers.get('Reply-To', None):
            gmsg.reply_to = message.extra_headers['Reply-To']
        if message.bcc:
            gmsg.bcc = list(message.bcc)
        if message.attachments:
            # Must be populated with (filename, filecontents) tuples
            attachments = []
            for attachment in message.attachments:
                if isinstance(attachment, MIMEBase):
                    attachments.append((attachment.get_filename(),
                                        attachment.get_payload(decode=True)))
                else:
                    attachments.append((attachment[0], attachment[1]))
            gmsg.attachments = attachments
        # Look for HTML alternative content
        if isinstance(message, EmailMultiAlternatives):
            for content, mimetype in message.alternatives:
                if mimetype == 'text/html':
                    gmsg.html = content
                    break
        return gmsg

    def _send(self, message):
        try:
            message = self._copy_message(message)
        except (ValueError, aeemail.InvalidEmailError), err:
            import logging
            logging.warn(err)
            if not self.fail_silently:
                raise
            return False
        if self.can_defer:
            self._defer_message(message)
            return True
        try:
            message.send()
        except aeemail.Error:
            if not self.fail_silently:
                raise
            return False
        return True

    def _defer_message(self, message):
        from google.appengine.ext import deferred
        deferred.defer(_send_deferred, message)

class AsyncEmailBackend(EmailBackend):
    can_defer = True
