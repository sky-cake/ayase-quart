from quart_wtf import QuartForm
from wtforms.fields import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length

class PostSearchForm(QuartForm):
    comment = StringField("Comment", validators=[DataRequired(), Length(1, 256)])
    submit = SubmitField('Search')

class LoginForm(QuartForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=1, max=64)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=1, max=64)])
    submit = SubmitField('Login')
