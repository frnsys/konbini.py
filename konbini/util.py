from flask_mail import Message
from flask import current_app, render_template

def send_email(tos, subject, template, reply_to=None, bcc=None, **kwargs):
    reply_to = reply_to or current_app.config['MAIL_REPLY_TO']
    msg = Message(subject,
                body=render_template('shop/email/{}.txt'.format(template), **kwargs),
                html=render_template('shop/email/{}.html'.format(template), **kwargs),
                recipients=tos,
                reply_to=reply_to,
                bcc=bcc)
    mail = current_app.extensions.get('mail')
    mail.send(msg)

