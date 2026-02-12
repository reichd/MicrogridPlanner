import os
from dotenv import dotenv_values
import configparser
from flask import Flask
from flask_cors import CORS
from extensions import mysql, mail
from blueprints.authentication import authentication_blueprint
from blueprints.toplevel import toplevel_blueprint
from blueprints.tools import tools_blueprint
from blueprints.simulate import simulate_blueprint
from blueprints.sizing import sizing_blueprint
from blueprints.resilience import resilience_blueprint 

_CONFIG_ENV = dotenv_values(os.path.join(os.path.dirname(os.getcwd()),"database-authentication.env"))
_CONFIG_INI = configparser.ConfigParser()
_CONFIG_INI.read("config.ini")
_DEBUG = _CONFIG_INI.getboolean("FRONTEND","DEBUG")
_CUI_LABELS = _CONFIG_INI.getboolean("CUI", "LABELS", fallback=False)
_USERNAME_LOGIN_DISABLE = _CONFIG_INI.getboolean("USERNAME_LOGIN", "DISABLE", fallback=False)
_CAC_LOGIN_ENABLE = _CONFIG_INI.getboolean("CAC_LOGIN", "ENABLE", fallback=False)

_CONFIG_INI_GLOBAL = configparser.ConfigParser()
_CONFIG_INI_GLOBAL.read(os.path.join(os.path.dirname(os.getcwd()),"config.ini"))

app = Flask(__name__) 
CORS(app)
if _DEBUG: app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

app.secret_key = _CONFIG_INI_GLOBAL.get("SECURITY","SECRET_KEY")

app.config["MAIL_SERVER"]= _CONFIG_INI_GLOBAL.get("MAIL","MAIL_SERVER")
app.config["MAIL_PORT"] = _CONFIG_INI_GLOBAL.get("MAIL","MAIL_PORT")
app.config["MAIL_USERNAME"] = _CONFIG_INI_GLOBAL.get("MAIL","MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = _CONFIG_INI_GLOBAL.get("MAIL","MAIL_PASSWORD", fallback=None)
app.config["MAIL_USE_TLS"] = _CONFIG_INI_GLOBAL.getboolean("MAIL","MAIL_USE_TLS")
app.config["MAIL_USE_SSL"] = _CONFIG_INI_GLOBAL.getboolean("MAIL","MAIL_USE_SSL")
app.config["MAIL_REPLY_TO"] = _CONFIG_INI_GLOBAL.get("MAIL","MAIL_REPLY_TO")
mail.init_app(app)

app.config["MYSQL_HOST"] = _CONFIG_ENV["MYSQL_HOST"]
app.config["MYSQL_PORT"] = int(_CONFIG_ENV["MYSQL_PORT"])
app.config["MYSQL_USER"] = _CONFIG_ENV["MYSQL_USER"]
app.config["MYSQL_PASSWORD"] = _CONFIG_ENV["MYSQL_PASSWORD"]
app.config["MYSQL_DB"] = _CONFIG_ENV["MYSQL_DATABASE"]
mysql.init_app(app)


    # --- Make available to ALL templates ---
@app.context_processor
def inject_global_ui_flags():
    return {
        "include_cui": _CUI_LABELS,
        "admin_email": _CONFIG_INI_GLOBAL.get("MAIL","MAIL_REPLY_TO"),
        "username_login_disable": _USERNAME_LOGIN_DISABLE,
        "cac_login_enable": _CAC_LOGIN_ENABLE
    }

app.register_blueprint(authentication_blueprint, url_prefix="/account")
app.register_blueprint(toplevel_blueprint, url_prefix="/")
app.register_blueprint(tools_blueprint, url_prefix="/tools/")
app.register_blueprint(simulate_blueprint, url_prefix="/tools/simulate/")
app.register_blueprint(sizing_blueprint, url_prefix="/tools/sizing/")
app.register_blueprint(resilience_blueprint, url_prefix="/tools/resilience/")

if __name__ == "__main__":
    app.run(
        host=_CONFIG_INI.get("FRONTEND","HOST"),
        port=_CONFIG_INI.get("FRONTEND","PORT"),
        debug=_DEBUG
    )
