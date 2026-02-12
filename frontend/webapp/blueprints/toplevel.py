from flask import Blueprint, render_template
import configparser
from extensions import user_info_wrapper, clear_session_data

_CONFIG_INI = configparser.ConfigParser()
_CONFIG_INI.read("config.ini")
_CUI_COMPONENT = _CONFIG_INI.get("CUI", "COMPONENT", fallback="")
_CUI_OFFICE = _CONFIG_INI.get("CUI", "OFFICE", fallback="")
_CUI_CATEGORIES = _CONFIG_INI.get("CUI", "CATEGORIES", fallback="")
_CUI_LIMITED_DISSEMINATION = _CONFIG_INI.get("CUI", "LIMITED_DISSEMINATION", fallback="")

toplevel_blueprint = Blueprint('toplevel', __name__)

@toplevel_blueprint.route('/')
@user_info_wrapper
def home(username, role):
	return render_template('index.html', username=username, role=role,
			cui_component=_CUI_COMPONENT,
			cui_office=_CUI_OFFICE,
			cui_categories=_CUI_CATEGORIES,
			cui_limited_dissemination=_CUI_LIMITED_DISSEMINATION
	)

@toplevel_blueprint.route('/clear_session/')
def clear_session():
	return clear_session_data(login_redirect=True)
