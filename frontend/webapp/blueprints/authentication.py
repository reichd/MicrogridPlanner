from importlib import metadata
from flask import Blueprint, render_template, request, redirect, url_for, session, make_response, flash, jsonify
from flask import current_app as app
from flask_mail import Message
from extensions import mail, mysql, clear_session_data, display_user, json_web_token, hash_generate, hash_verify
import MySQLdb.cursors, re, uuid, datetime, os, math, urllib, json, hashlib
import configparser
import requests
import secrets
import jwt
from cryptography import x509
from cryptography.x509.oid import ExtensionOID, NameOID, ObjectIdentifier
from typing import Optional, Tuple, Dict, Any


_CONFIG_INI = configparser.ConfigParser()
_CONFIG_INI.read("config.ini")
_CONSENT_BANNER = _CONFIG_INI.getboolean("CUI","CONSENT_BANNER",fallback=False)
_USERNAME_LOGIN_DISABLE = _CONFIG_INI.getboolean("USERNAME_LOGIN", "DISABLE", fallback=False)
_CAC_LOGIN_ENABLE = _CONFIG_INI.getboolean("CAC_LOGIN", "ENABLE", fallback=False)
_AZURE = dict(_CONFIG_INI.items("AZURE")) if _CONFIG_INI.has_section("AZURE") else dict()
_AZURE_CLIENT_ID = _AZURE["client_id"] if "client_id" in _AZURE else None
_AZURE_TENANT_ID = _AZURE["tenant_id"] if "tenant_id" in _AZURE else None
_AZURE_CLIENT_SECRET = _AZURE["client_secret"] if "client_secret" in _AZURE else None
_AZURE_EMAIL_DOMAIN = _AZURE["email_domain"] if "email_domain" in _AZURE else None
_CONFIG_INI_GLOBAL = configparser.ConfigParser()
_CONFIG_INI_GLOBAL.read(os.path.join(os.path.dirname(os.getcwd()),"config.ini"))
_APP_URL = _CONFIG_INI_GLOBAL.get("FRONTEND", "URL")
_MAIL_DISABLE_FOR_RUN_LOCAL = _CONFIG_INI_GLOBAL.getboolean("MAIL","MAIL_DISABLE_FOR_RUN_LOCAL",fallback=False)
_ACCOUNT_ACTIVATION_NOT_REQUIRED = "not_required"
_ACCOUNT_ACTIVATION_AUTOMATED = "automated"
_ACCOUNT_ACTIVATION_MANUAL = "manual_approval"
_ACCOUNT_STATUS_NOT_CONFIRMED = "pending"
_ACCOUNT_STATUS_CONFIRMED = "confirmed"
_ACCOUNT_STATUS_ACTIVATED = "activated"

authentication_blueprint = Blueprint('authentication', __name__)

def include_consent_banner():
	"""Returns boolean indicating whether to include consent banner"""
	return _CONSENT_BANNER

def use_azure():
	"""Returns boolean indicating whether Azure requirements have been specified"""
	for param in [_AZURE_CLIENT_ID, _AZURE_TENANT_ID, _AZURE_CLIENT_SECRET, _APP_URL]:
		if param is None or len(param)==0: return False
	return True

def azure_base_url():
	return "https://login.microsoftonline.com/{0}/oauth2/v2.0".format(
		_AZURE_TENANT_ID
	) if _AZURE_TENANT_ID else None

def azure_url(endpoint):
	"""Returns url without query parameters for Azure oauth"""
	return azure_base_url()+endpoint if use_azure() else None

def azure_url_params():
	"""Returns url parameters required for Azure authentication"""
	return { 
		"client_id":_AZURE_CLIENT_ID,
		"redirect_uri":_APP_URL+request.url_rule.rule+"azure",
	  	"scope":"openid email profile",
		"response_type":"code",
	} if use_azure() else None

def azure_account_is_registered(email):
	"""Returns account info if Azure account is registered in app
	Otherwise, returns None"""
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
	account = cursor.fetchone()
	return account

def azure_account_register(email):
	"""Register account if it does not exist
	Return account info"""
	account = azure_account_is_registered(email)
	if account: return account
	hashed_password = hash_generate(secrets.token_urlsafe(20), app.secret_key)
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	cursor.execute('INSERT INTO user (username, password, email, activation_code, role, ip) VALUES (%s, %s, %s,%s, %s, %s)', (email, hashed_password, email, _ACCOUNT_STATUS_ACTIVATED, "Member", request.environ['REMOTE_ADDR'],))
	mysql.connection.commit()
	account = azure_account_is_registered(email)
	return account

def validate_profile_info(username, password, cpassword, email, id=0):
	"""Verify all account profile info submitted meets requirements"""
	msg = ''
	flag = True	
	if _AZURE_EMAIL_DOMAIN in email:
		flag = False
		msg += 'Use Azure ('+_AZURE_EMAIL_DOMAIN+') login instead\n'
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	cursor.execute('SELECT * FROM user WHERE username = %s and id <> %s', (username, id))
	account_username = cursor.fetchone()
	if account_username: 
		flag = False
		msg += 'Username already exists\n'
	cursor.execute('SELECT * FROM user WHERE email = %s and id <> %s', (email, id))
	account_email = cursor.fetchone()
	if account_email:
		flag = False
		msg += 'Email already exists\n'
	elif id==0 and (not username or not password or not cpassword or not email):
		flag = False
		msg += 'Please fill out the form\n'
	if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
		flag = False
		msg += 'Invalid email address\n'
	elif not re.match(r'^[a-z0-9]+$', username):
		flag = False
		msg += 'Username must contain only lowercase letters and numbers\n'
	elif len(username) < 5 or len(username) > 20:
		flag = False
		msg += 'Username must be between 5 and 20 characters long\n'
	elif password and (len(password) < 8 or len(password) > 20):
		flag = False
		msg += 'Password must be between 8 and 20 characters long\n'
	elif password != cpassword:
		flag = False
		msg += 'Passwords do not match\n'
	return flag, msg

def create_session_data(account, rememberme=False, respond_success=True):
	"""Generate session data for input account
	Set a cookie with the app json_web_token for API authentication
	Return a Flask response"""
	session['loggedin'] = True
	session['id'] = account['id']
	session['username'] = account['username']
	session['role'] = account['role']
	resp = make_response("Success", 200) if respond_success \
			else make_response(redirect(url_for('toplevel.home')))
	admin_flag = account['role'] == "Admin"
	resp.set_cookie('jwt', json_web_token(account['id'], app.secret_key, admin=admin_flag))
	try:
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute('UPDATE user SET last_seen = NOW() WHERE id = %s', (session['id'],))
		mysql.connection.commit()
	except MySQLdb.Error:
		print("ERROR IN CONNECTION", flush=True)
	if rememberme:
		rememberme_code = account['rememberme']
		if not rememberme_code:
			str_to_hash = account["username"] + account["password"]
			rememberme_code = hash_generate(str_to_hash, app.secret_key)
		expire_date = datetime.datetime.now() + datetime.timedelta(days=90)
		resp.set_cookie('rememberme', rememberme_code, expires=expire_date)
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute('UPDATE user SET rememberme = %s WHERE id = %s', (rememberme_code, account['id'],))
		mysql.connection.commit()
	return resp

@authentication_blueprint.route('/home', methods=['GET'])
def home():
	"""workaround for JavaScript url redirect"""
	return redirect(url_for('toplevel.home'))

@authentication_blueprint.route('/azure', methods=["GET"])
def azure():
	code = request.args.get('code')
	response = requests.post(
		azure_url("/token"),
		data=dict(
			client_id=_AZURE_CLIENT_ID,
			client_secret=urllib.parse.quote_plus(_AZURE_CLIENT_SECRET),
			code=code,
			grant_type="authorization_code",
			redirect_uri=_APP_URL+request.url_rule.rule,
		),
	)
	data = response.json()
	token = data["access_token"]
	alg = jwt.get_unverified_header(token)["alg"]
	# jwt_decoded = jwt.decode(token, algorithms=[alg], options={"verify_signature":False})
	response_user = requests.get(
		"https://graph.microsoft.com/v1.0/me",
		headers=dict(Authorization="Bearer {0}".format(token)),
	).json()
	email = response_user["mail"]
	if not email:
		email = response_user["userPrincipalName"]
	account = azure_account_register(email)
	response = create_session_data(account, respond_success=False)
	return response

def activate_account(email, username=None, password=None, role=None, user_key=None):
	# Generate a random unique id for activation code
	activation_code = uuid.uuid4()
	# Insert account into database
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	if user_key:
		cursor.execute('SELECT * FROM user WHERE cacid = %s', (user_key,))
		account = cursor.fetchone()
		if account:
			return 'Your CAC has already been linked to an account. Please login instead.'
	if username and password and role:
		cursor.execute('INSERT INTO user (username, password, email, activation_code, role, ip) VALUES (%s, %s, %s, %s, %s, %s)', (username, password, email, activation_code, role, request.environ['REMOTE_ADDR'],))
	if user_key:
		cursor.execute('UPDATE user SET cacid = %s, activation_code = %s WHERE email = %s', (user_key, activation_code, email,))
	mysql.connection.commit()
	# Create new message
	email_info = Message('Account Activation Required', sender = app.config['MAIL_USERNAME'], recipients = [email])
	# Activate Link URL
	activate_link = _APP_URL + url_for('authentication.activate', email=email, code=str(activation_code))
	# Define and render the activation email template
	email_info.body = render_template('authentication-codeshack/activation-email-template.html', link=activate_link)
	email_info.html = render_template('authentication-codeshack/activation-email-template.html', link=activate_link)
	# send activation email to user
	if not _MAIL_DISABLE_FOR_RUN_LOCAL:
		mail.send(email_info)
	# Output message
	return 'Please check your email to activate your account!'

# Common regexes for CAC EDIPI and UPN extraction
EDIPI_10_RE = re.compile(r"\b(\d{10})\b")
UPN_LIKE_RE = re.compile(r"\b(\d{10,16})@(?:mil|smil)\b", re.IGNORECASE)  # sometimes 16-digit PIV-style IDs show up

# Windows UPN OtherName OID often used in cert SAN
# (UPN is commonly stored as OtherName with OID 1.3.6.1.4.1.311.20.2.3)
UPN_OTHERNAME_OID = ObjectIdentifier("1.3.6.1.4.1.311.20.2.3")


def _load_cert_from_nginx_header(cert_header: str) -> x509.Certificate:
    """
    cert_header: URL-escaped PEM from NGINX ($ssl_client_escaped_cert)
    """
    pem_text = urllib.parse.unquote(cert_header).strip()
    return x509.load_pem_x509_certificate(pem_text.encode("utf-8"))


def _extract_edipi_from_subject_dn(cert: x509.Certificate) -> Optional[str]:
    # Try CN first (many environments put EDIPI there, e.g. LAST.FIRST.MI.1234567890) [4](https://public.cyber.mil/)
    try:
        cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if cn_attrs:
            cn = cn_attrs[0].value
            m = EDIPI_10_RE.search(cn)
            if m:
                return m.group(1)
    except Exception:
        pass

    # Try anywhere in the full subject DN string as a fallback
    subj = cert.subject.rfc4514_string()
    m = EDIPI_10_RE.search(subj)
    return m.group(1) if m else None


def _extract_edipi_from_san(cert: x509.Certificate) -> Optional[str]:
    """
    Try to find EDIPI (10-digit) from SAN:
    - rfc822Name emails (sometimes EDIPI@mil appears as UPN-ish)
    - otherName UPN PrincipalName (OID 1.3.6.1.4.1.311.20.2.3) [2](https://stackoverflow.com/questions/79588699/how-to-configure-nginx-to-prompt-the-user-to-select-a-client-certificate-from-os)
    """
    try:
        san = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
    except x509.ExtensionNotFound:
        return None

    # 1) rfc822Name values (emails). Sometimes you’ll see EDIPI@mil instead of a real email. [2](https://stackoverflow.com/questions/79588699/how-to-configure-nginx-to-prompt-the-user-to-select-a-client-certificate-from-os)
    try:
        emails = san.get_values_for_type(x509.RFC822Name)
        for e in emails:
            m = UPN_LIKE_RE.search(e)
            if m and len(m.group(1)) == 10:
                return m.group(1)
    except Exception:
        pass

    # 2) otherName values (UPN PrincipalName is commonly stored here on CAC/PIV in some environments) [2](https://stackoverflow.com/questions/79588699/how-to-configure-nginx-to-prompt-the-user-to-select-a-client-certificate-from-os)
    for on in san.get_values_for_type(x509.OtherName):
        if on.type_id == UPN_OTHERNAME_OID:
            # otherName.value is ASN.1 encoded; often decodes to a UTF8/IA5 string payload.
            raw = on.value
            # Best-effort decode:
            text = None
            for enc in ("utf-8", "utf-16le", "latin1"):
                try:
                    text = raw.decode(enc, errors="ignore")
                    break
                except Exception:
                    continue
            if not text:
                continue
            m = UPN_LIKE_RE.search(text)
            if m and len(m.group(1)) == 10:
                return m.group(1)

    return None

def _subject_key_identifier_hex(cert: x509.Certificate) -> Optional[str]:
    """
    SKI is a good “strong mapping” fallback if present; stable as long as the key remains the same.
    """
    try:
        ski = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_KEY_IDENTIFIER).value
        return ski.digest.hex()
    except x509.ExtensionNotFound:
        return None

def _public_key_spki_sha256(cert: x509.Certificate) -> str:
    """
    Hash the SubjectPublicKeyInfo bytes. This is stable for the same public key.
    """
    spki = cert.public_key().public_bytes(
        encoding=__import__("cryptography.hazmat.primitives.serialization").hazmat.primitives.serialization.Encoding.DER,
        format=__import__("cryptography.hazmat.primitives.serialization").hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return hashlib.sha256(spki).hexdigest()

def _cert_fingerprint_sha256(cert: x509.Certificate) -> str:
    return cert.fingerprint(hashlib.sha256()).hex()

def derive_cac_user_key_from_nginx(
    cert_header: str,
    *,
    prefer_person_id: bool = True
) -> Tuple[str, Dict[str, Any]]:
    """
    Returns:
      (stable_id, metadata)

    stable_id format examples:
      - "edipi:1234567890"      (best: stable person identifier)
      - "ski:<hex>"             (stable as long as key stays same)
      - "spki-sha256:<hex>"     (stable as long as key stays same)
      - "cert-sha256:<hex>"     (stable for this cert; changes on renewal)
      - "issuer-serial:<...>"   (stable for this cert; changes on renewal)

    NOTE: Only EDIPI is a true person-stable identifier in typical DoD usage. [1](https://public.cyber.mil/get-dod-certs/)[2](https://stackoverflow.com/questions/79588699/how-to-configure-nginx-to-prompt-the-user-to-select-a-client-certificate-from-os)
    """
    cert = _load_cert_from_nginx_header(cert_header)

    meta: Dict[str, Any] = {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial": hex(cert.serial_number),
    }

    # --- Tier 1: EDIPI (person-stable when present) ---
    if prefer_person_id:
        edipi = _extract_edipi_from_san(cert) or _extract_edipi_from_subject_dn(cert)
        if edipi:
            meta["method"] = "edipi"
            return f"edipi:{edipi}", meta

    # --- Tier 2: Subject Key Identifier (strong key-based mapping) ---
    ski_hex = _subject_key_identifier_hex(cert)
    if ski_hex:
        meta["method"] = "ski"
        return f"ski:{ski_hex}", meta

    # --- Tier 3: Public key hash (strong key-based mapping) ---
    spki_hash = _public_key_spki_sha256(cert)
    meta["method"] = "spki-sha256"
    return f"spki-sha256:{spki_hash}", meta

    # If you want “always something even if public_key fails” you can extend with:
    # fp = _cert_fingerprint_sha256(cert)
    # return f"cert-sha256:{fp}", {...}

def check_account_activation(account):
	# Check if account is activated
	settings = get_settings()
	msg = None
	if settings['account_activation']['value'] != _ACCOUNT_ACTIVATION_NOT_REQUIRED:
		if settings['account_activation']['value'] == _ACCOUNT_ACTIVATION_AUTOMATED and account['activation_code'] != _ACCOUNT_STATUS_ACTIVATED:
			msg = 'Please activate your account to login!'
		if settings['account_activation']['value'] == _ACCOUNT_ACTIVATION_MANUAL:
			if account['activation_code'] == _ACCOUNT_STATUS_CONFIRMED:
				msg = 'Your account is pending approval. You may email the system admin at {0} for a status update'.format(app.config["MAIL_REPLY_TO"])
			elif account['activation_code'] != _ACCOUNT_STATUS_ACTIVATED:
				msg = 'Please activate your account to login!'
	return msg

@authentication_blueprint.route("/cac", methods=["GET", "POST"])
def cac():
	# If already logged in or "remember me", follow your existing flows
	if loggedin():
		return redirect(url_for('toplevel.home'))
	elif rememberme():
		return redirect(url_for('authentication.login'))

	# --- 1) Verify CAC/Client certificate ---
	verify = request.headers.get("X-SSL-Client-Verify")
	if verify != "SUCCESS":
		msg = "Client certificate verification failed. Please ensure you have a valid CAC and try again."
		return redirect(url_for('authentication.login', msg=msg))

	client_cert = request.headers.get("X-SSL-Client-Cert")

	# Derive your CAC key (e.g., EDIPI) and metadata
	user_key, meta = derive_cac_user_key_from_nginx(client_cert)
	if not user_key:
		msg = "Could not derive CAC identity. Please reinsert your CAC and try again."
		return redirect(url_for('authentication.login', msg=msg))

	# DB handle
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

	# --- 2) If GET: attempt login if account exists; otherwise show registration form ---
	if request.method == "GET":
		account = None
		cursor.execute('SELECT * FROM user WHERE cacid = %s', (user_key,))
		account = cursor.fetchone()

		if account:
			activation_status = check_account_activation(account)
			if activation_status:
				# e.g., "Your account is not activated yet" or similar
				return redirect(url_for('authentication.login', msg=activation_status))
			# Create session and return your existing response object
			return create_session_data(account, respond_success=False)

		# Account not found: render registration form
		return render_template(
			'authentication-codeshack/cac.html',
			msg='',
			settings=get_settings(),
		)

	# --- 3) If POST: treat as registration submission ---
	if not _CAC_LOGIN_ENABLE:
		return 'CAC login is disabled. Please use Azure or username login.'

	if 'email' not in request.form:
		return 'Email is required.'

	# Basic email validation
	email = request.form['email'].strip()
	if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
		return 'Invalid email address'

	# Check if email is already associated with an account
	cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
	existing = cursor.fetchone()

	if existing:
		# Link CAC to existing account via your existing activation helper
		return activate_account(email=email, user_key=user_key)

	# Create a new account and activate (or send activation) using your helper
	return activate_account(
		email=email,
		username=email,
		password=hash_generate(secrets.token_urlsafe(20), app.secret_key),
		role="Member",
		user_key=user_key
	)

# http://localhost:5000/accounts/ - this will be the login page, we need to use both GET and POST requests
@authentication_blueprint.route('/', methods=['GET', 'POST'])
def login():
	# Redirect user to home page if logged-in
	if loggedin():
		return redirect(url_for('toplevel.home'))
	# Output message if something goes wrong...
	if request.method == 'POST' and _USERNAME_LOGIN_DISABLE:
		return 'Username/password login is disabled. Please use Azure or CAC login.'
	msg = request.args.get('msg') if request.args.get('msg') else ''
	# Retrieve the settings
	settings = get_settings()
	# Check if "username" and "password" POST requests exist (user submitted form)
	if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'token' in request.form:
		# Bruteforce protection
		login_attempts_res = login_attempts(False)
		if settings['brute_force_protection']['value'] == 'true' and login_attempts_res and login_attempts_res['attempts_left'] < 1:
			return 'You have exceeded the number of login attempts permitted. Please try again tomorrow or email {0} for assistance.'.format(
				app.config["MAIL_REPLY_TO"]
			)
		# Create variables for easy access
		username = request.form['username']
		if _AZURE_EMAIL_DOMAIN in username:
			return 'Use Azure ('+_AZURE_EMAIL_DOMAIN+') login instead'
		password = request.form['password']
		token = request.form['token']
		# Check if account exists using MySQL
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
		# Fetch one record and return result
		account = cursor.fetchone()
		password_correct = hash_verify(account['password'], password, app.secret_key) if account else False
		# If account exists in accounts table
		if account and password_correct:
			activation_status = check_account_activation(account)
			if activation_status:
				return activation_status
			# CSRF protection, form token should match the session token
			if settings['csrf_protection']['value'] == 'true' and str(token) != str(session['token']):
				return 'Invalid token!'
			# Two-factor
			if settings['twofactor_protection']['value'] == 'true' and account['ip'] != request.environ['REMOTE_ADDR']:
				session['tfa_id'] = account['id']
				session['tfa_email'] = account['email']
				return 'tfa: twofactor'
			# Reset the attempts left
			cursor.execute('DELETE FROM login_attempts WHERE ip_address = %s', (request.environ['REMOTE_ADDR'],))
			mysql.connection.commit()
			# Create session data, we can access this data in other routes
			rememberme = 'rememberme' in request.form
			resp = create_session_data(account, rememberme=rememberme)
			# Return response
			return resp
		else:
			# Account doesnt exist or username/password incorrect
			if settings['brute_force_protection']['value'] == 'true':
				# Bruteforce protection enabled - update attempts left
				login_attempts_res = login_attempts();
				return 'Incorrect username/password! You have ' + str(login_attempts_res['attempts_left']) + ' attempts remaining!'
			else:
				return 'Incorrect username/password!'
	# Generate random token that will prevent CSRF attacks
	token = uuid.uuid4()
	session['token'] = token
	# Show the login form with message (if any)
	return render_template('authentication-codeshack/login.html', msg=msg, token=token, settings=settings, 
			azure=use_azure(), azure_url=azure_url("/authorize"), azure_url_params=azure_url_params(),
			include_consent_banner=include_consent_banner())

# http://localhost:5000/pythinlogin/register - this will be the registration page, we need to use both GET and POST requests
@authentication_blueprint.route('/register', methods=['GET', 'POST'])
def register():
	# Redirect user to home page if logged-in
	if loggedin():
		return redirect(url_for('toplevel.home'))
	elif rememberme():
		return redirect(url_for('authentication.login'))
	# Output message variable
	msg = ''
	# Retrieve the settings
	settings = get_settings()
	# Check if "username", "password", "cpassword" and "email" POST requests exist (user submitted form)
	if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'cpassword' in request.form and 'email' in request.form:
		# reCAPTCHA validation
		if settings.get('recaptcha', {}).get('value') == 'true':
			if 'g-recaptcha-response' not in request.form:
				return 'Invalid captcha!'
			req = urllib.request.Request(
				'https://www.google.com/recaptcha/api/siteverify',
				urllib.parse.urlencode({
					'response': request.form['g-recaptcha-response'],
					'secret': settings['recaptcha_secret_key']['value']
				}).encode()
			)
			response_json = json.loads(urllib.request.urlopen(req).read().decode())
			if not response_json.get('success'):
				return 'Invalid captcha!'
		# Create variables for easy access
		username = request.form['username']
		password = request.form['password']
		cpassword = request.form['cpassword']
		email = request.form['email']
		flag, msg = validate_profile_info(username, password, cpassword, email)
		if not flag:
			return msg
		role = 'Member'
		hashed_password = hash_generate(password, app.secret_key)
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)	
		if settings['account_activation']['value'] != _ACCOUNT_ACTIVATION_NOT_REQUIRED and not _MAIL_DISABLE_FOR_RUN_LOCAL:
			return activate_account(email, username=username, password=hashed_password, role=role)
		else:
			# Account doesnt exists and the form data is valid, now insert new account into accounts table
			activation_status = _ACCOUNT_STATUS_ACTIVATED
			cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
			cursor.execute('INSERT INTO user (username, password, email, activation_code, role, ip) VALUES (%s, %s, %s,%s, %s, %s)', (username, hashed_password, email, activation_status, role, request.environ['REMOTE_ADDR'],))
			mysql.connection.commit()
			# Auto login if the setting is enabled
			if settings['auto_login_after_register']['value'] == 'true':
				cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
				cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
				account = cursor.fetchone()
				resp = create_session_data(account)
				# Redirect to home page
				return resp
			# Output message
			return 'You have registered! You can now login!'
	elif request.method == 'POST':
		# Form is empty... (no POST data)
		return 'Please fill out the form!'
	# Render registration form with message (if any)
	return render_template('authentication-codeshack/register.html', msg=msg, settings=settings)

# http://localhost:5000/pythinlogin/activate/<email>/<code> - this page will activate a users account if the correct activation code and email are provided
@authentication_blueprint.route('/activate/<string:email>/<string:code>', methods=['GET'])
def activate(email, code):
	# Output message variable
	msg = 'The activation code is incorrect, has been used or has expired!'
	# Check if the email and code provided exist in the accounts table
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	cursor.execute('SELECT * FROM user WHERE email = %s AND activation_code = %s', (email, code,))
	account = cursor.fetchone()
	# If account exists
	if account:
		settings = get_settings()
		status = _ACCOUNT_STATUS_ACTIVATED if settings['account_activation']['value'] == _ACCOUNT_ACTIVATION_AUTOMATED else _ACCOUNT_STATUS_CONFIRMED
		# account exists, update the activation code
		cursor.execute('UPDATE user SET activation_code = %s WHERE email = %s AND activation_code = %s', (status, email, code,))
		mysql.connection.commit()
		if settings['account_activation']['value'] == _ACCOUNT_ACTIVATION_MANUAL and not _MAIL_DISABLE_FOR_RUN_LOCAL:
			email_info = Message('Account pending admin approval', sender = app.config['MAIL_USERNAME'], recipients = [app.config['MAIL_REPLY_TO']])
			email_info.body = "Account pending approval with email = "+email
			email_info.html = "Account pending approval with email = "+email
			mail.send(email_info)
		# automatically log the user in and redirect to the home page
		response = make_response(redirect(url_for('authentication.login')))
		# Redirect to home page
		return response
	# Render activation template
	return render_template('authentication-codeshack/activate.html', msg=msg)

# http://localhost:5000/pythinlogin/profile - this will be the profile page, only accessible for loggedin users
@authentication_blueprint.route('/profile')
def profile():
	# Check if user is loggedin
	if loggedin():
		# Retrieve all account info from the database
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute('SELECT * FROM user WHERE id = %s', (session['id'],))
		account = cursor.fetchone()
		editable = _AZURE_EMAIL_DOMAIN not in account["email"]
		# Render the profile page along with the account info
		return render_template('authentication-codeshack/profile.html', account=account, role=session['role'], username=display_user(session['username']), editable=editable)
	# User is not loggedin, redirect to login page
	return redirect(url_for('authentication.login'))

# http://localhost:5000/pythinlogin/profile/edit - user can edit their existing details
@authentication_blueprint.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
	# Check if user is loggedin
	if loggedin():
		# Output message
		msg = ''
		# Retrieve the settings
		settings = get_settings()
		# We need to retieve additional account info from the database and populate it on the profile page
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute('SELECT * FROM user WHERE id = %s', (session['id'],))
		account = cursor.fetchone()
		# Check if "username", "password" and "email" POST requests exist (user submitted form)
		if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
			# Create variables for easy access
			username = request.form['username']
			password = request.form['password']
			cpassword = request.form['cpassword']
			email = request.form['email']
			flag, msg = validate_profile_info(username, password, cpassword, email, account["id"])
			if flag:
				current_password =  hash_generate(password, app.secret_key) if password else account['password']
				# update account with the new details
				cursor.execute('UPDATE user SET username = %s, password = %s, email = %s WHERE id = %s', (username, current_password, email, session['id'],))
				mysql.connection.commit()
				# Update session variables
				session['username'] = username
				session['email'] = email
				# retrieve updated acount
				cursor.execute('SELECT * FROM user WHERE id = %s', (session['id'],))
				account = cursor.fetchone()
				# Reactivate account if account acivation option enabled
				if settings['account_activation']['value'] == 'true' and not _MAIL_DISABLE_FOR_RUN_LOCAL:
					msg = 'Account updated successfully!'
					# Generate a random unique id for activation code
					activation_code = uuid.uuid4()
					# Update activation code in database
					cursor.execute('UPDATE user SET activation_code = %s WHERE id = %s', (activation_code, session['id'],))
					mysql.connection.commit()
					# Create new message
					email_info = Message('Account Activation Required', sender = app.config['MAIL_USERNAME'], recipients = [email])
					# Activate Link URL
					activate_link = _APP_URL + url_for('authentication.activate', email=email, code=str(activation_code))
					# Define and render the activation email template
					email_info.body = render_template('authentication-codeshack/activation-email-template.html', link=activate_link)
					email_info.html = render_template('authentication-codeshack/activation-email-template.html', link=activate_link)
					# send activation email to user
					mail.send(email_info)
					response = clear_session_data()
					return response
				else:
					# Output message
					msg = 'Account updated successfully\n'
		# Render the profile page along with the account info
		return render_template('authentication-codeshack/profile-edit.html', account=account, role=session['role'], username=display_user(session['username']), msg=msg.split("\n"))
	# Redirect to the login page
	return redirect(url_for('authentication.login'))

# http://localhost:5000/pythinlogin/forgotpassword - user can use this page if they have forgotten their password
@authentication_blueprint.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
	msg = ''
	# If forgot password form submitted
	if request.method == 'POST' and 'email' in request.form and not _MAIL_DISABLE_FOR_RUN_LOCAL:
		# Capture input email
		email = request.form['email']
		# Define the connection cursor
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		# Retrieve account info from database that's associated with the captured email
		cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
		account = cursor.fetchone()
		# If account exists
		if account:
			# Generate unique reset ID
			reset_code = uuid.uuid4()
			# Update the reset column in the accounts table to reflect the generated ID
			cursor.execute('UPDATE user SET reset = %s WHERE email = %s', (reset_code, email,))
			mysql.connection.commit()
			# Create new email message
			email_info = Message('Password Reset', sender = app.config['MAIL_USERNAME'], recipients = [email])
			# Generate reset password link
			reset_link = _APP_URL + url_for('authentication.resetpassword', email = email, code = str(reset_code))
			# Email content
			email_info.body = '<p>Please click the following link to reset your password: <a href="' + str(reset_link) + '">' + str(reset_link) + '</a></p>'
			email_info.html = '<p>Please click the following link to reset your password: <a href="' + str(reset_link) + '">' + str(reset_link) + '</a></p>'
			# Send mail
			mail.send(email_info)
			msg = 'Reset password link has been sent to your email!'
		else:
			msg = 'An account with that email does not exist!'
	# Render the forgot password template
	return render_template('authentication-codeshack/forgotpassword.html', msg=msg)

# http://localhost:5000/pythinlogin/resetpassword/EMAIL/CODE - proceed to reset the user's password
@authentication_blueprint.route('/resetpassword/<string:email>/<string:code>', methods=['GET', 'POST'])
def resetpassword(email, code):
	msg = ''
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	# Retrieve the account with the email and reset code provided from the GET request
	cursor.execute('SELECT * FROM user WHERE email = %s AND reset = %s', (email, code,))
	account = cursor.fetchone()
	# If account exists
	if account:
		# Check if the new password fields were submitted
		if request.method == 'POST' and 'npassword' in request.form and 'cpassword' in request.form:
			npassword = request.form['npassword']
			cpassword = request.form['cpassword']
			# Password fields must match
			if npassword and npassword == cpassword and npassword != "":
				# Hash new password
				npassword = hash_generate(npassword, app.secret_key)
				# Update the user's password
				cursor.execute('UPDATE user SET password = %s, reset = "" WHERE email = %s', (npassword, email,))
				mysql.connection.commit()
				if request.method == "POST": flash("Your password has been successfully reset.")
				return redirect(url_for('authentication.login'))
			else:
				msg = 'Passwords must match and must not be empty!'
		# Render the reset password template
		return render_template('authentication-codeshack/resetpassword.html', msg=msg, email=email, code=code)
	return 'Invalid email and/or code!'

# http://localhost:5000/pythinlogin/twofactor - two-factor authentication
@authentication_blueprint.route('/twofactor', methods=['GET', 'POST'])
def twofactor():
	# Output message
	msg = ''
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	# Verify the ID and email provided
	if 'tfa_email' in session and 'tfa_id' in session and not _MAIL_DISABLE_FOR_RUN_LOCAL:
		# Retrieve the account
		cursor.execute('SELECT * FROM user WHERE id = %s AND email = %s', (session['tfa_id'], session['tfa_email'],))
		account = cursor.fetchone()
		# If account exists
		if account:
			# If the code param exists in the POST request form
			if request.method == 'POST' and 'code' in request.form:
				# If the user entered the correct code
				if request.form['code'] == account['tfa_code']:
					# Get the user's IP address
					ip = request.environ['REMOTE_ADDR']
					# Update IP address in database
					cursor.execute('UPDATE user SET ip = %s WHERE id = %s', (ip, account['id'],))
					mysql.connection.commit()
					# Clear TFA session variables
					session.pop('tfa_email')
					session.pop('tfa_id')
					# Authenticate the user
					response = create_session_data(account, respond_success=False)
					# Redirect to home page
					return response
				else:
					msg = 'Incorrect code provided!'
			else:
				# Generate unique code
				code = str(uuid.uuid4()).upper()[:5]
				# Update code in database
				cursor.execute('UPDATE user SET tfa_code = %s WHERE id = %s', (code, account['id'],))
				mysql.connection.commit()
				# Create new message
				email_info = Message('Your Access Code', sender = app.config['MAIL_USERNAME'], recipients = [account['email']])
				# Define and render the twofactor email template
				email_info.body = render_template('authentication-codeshack/twofactor-email-template.html', code=code)
				email_info.html = render_template('authentication-codeshack/twofactor-email-template.html', code=code)
				# send twofactor email to user
				mail.send(email_info)
		else:
			msg = 'No email and/or ID provided!'
	else:
		msg = 'No email and/or ID provided!'
	# Render twofactor template
	return render_template('authentication-codeshack/twofactor.html', msg=msg)

def login_attempts(update = True):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Get the user's IP address
    ip = request.environ['REMOTE_ADDR']
    # Get the current date
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Update attempts left
    if update:
        cursor.execute('INSERT INTO login_attempts (ip_address, `date`) VALUES (%s,%s) ON DUPLICATE KEY UPDATE attempts_left = attempts_left - 1, `date` = VALUES(`date`)', (ip, str(now),))
        mysql.connection.commit()
	# Retrieve the login attemmpts
    cursor.execute('SELECT * FROM login_attempts WHERE ip_address = %s', (ip,))
    login_attempts = cursor.fetchone()
    if login_attempts:
        # The date the attempts left expires (removed from database)
        expire = datetime.datetime.strptime(now, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=1)
        # If current date is greater than expiration date
        if datetime.datetime.strptime(now, '%Y-%m-%d %H:%M:%S') > expire:
            # Delete the entry
            cursor.execute('DELETE FROM login_attempts WHERE id_address = %s', (ip, session['id'],))
            mysql.connection.commit()
            login_attempts = []
    return login_attempts

# http://localhost:5000/pythinlogin/logout - this will be the logout page
@authentication_blueprint.route('/logout')
def logout():
	resp = clear_session_data()
	return resp


def rememberme():
	if 'rememberme' not in request.cookies: return False
	# check if remembered, cookie has to match the "rememberme" field
	try:
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute('SELECT * FROM user WHERE rememberme = %s', (request.cookies['rememberme'],))
		account = cursor.fetchone()
		if not account: return False
	except MySQLdb.Error:
		print("ERROR IN CONNECTION", flush=True)
	return True

# Check if logged in function, update session if cookie for "remember me" exists
def loggedin():
	try:
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		# Check if user is logged-in
		if 'jwt' in request.cookies and 'id' in session:
			# Update last seen date
			cursor.execute('UPDATE user SET last_seen = NOW() WHERE id = %s', (session['id'],))
			mysql.connection.commit()
			return True
		# account not logged in return false
	except MySQLdb.Error:
		print("ERROR IN CONNECTION", flush=True)
	return False

# ADMIN PANEL
# http://localhost:5000/accounts/authentication-codeshack/admin/ - admin dashboard, view new accounts, active accounts, statistics
@authentication_blueprint.route('/authentication-codeshack/admin/', methods=['GET', 'POST'])
def admin():
	# Check if admin is logged-in
	if not admin_loggedin():
		return redirect(url_for('authentication.login'))
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	# Retrieve new accounts for the current date
	cursor.execute('SELECT * FROM user WHERE cast(registered as DATE) = cast(now() as DATE) ORDER BY registered DESC')
	accounts = cursor.fetchall()
	# Get the total number of accounts
	cursor.execute('SELECT COUNT(*) AS total FROM user')
	accounts_total = cursor.fetchone()
	# Get the total number of active accounts (<1 month)
	cursor.execute('SELECT COUNT(*) AS total FROM user WHERE last_seen < date_sub(now(), interval 1 month)')
	inactive_accounts = cursor.fetchone()
	# Retrieve accounts created within 1 day from the current date
	cursor.execute('SELECT * FROM user WHERE last_seen > date_sub(now(), interval 1 day) ORDER BY last_seen DESC')
	active_accounts = cursor.fetchall()
	# Get the total number of inactive accounts
	cursor.execute('SELECT COUNT(*) AS total FROM user WHERE last_seen > date_sub(now(), interval 1 month)')
	active_accounts2 = cursor.fetchone()
	# Render admin dashboard template
	return render_template('authentication-codeshack/admin/dashboard.html', accounts=accounts, selected='dashboard', selected_child='view', accounts_total=accounts_total['total'], inactive_accounts=inactive_accounts['total'], active_accounts=active_accounts, active_accounts2=active_accounts2['total'], time_elapsed_string=time_elapsed_string)

# http://localhost:5000/accounts/authentication-codeshack/admin/accounts - view all accounts
@authentication_blueprint.route('/authentication-codeshack/admin/accounts/<string:msg>/<string:search>/<string:status>/<string:activation>/<string:role>/<string:order>/<string:order_by>/<int:page>', methods=['GET', 'POST'])
@authentication_blueprint.route('/authentication-codeshack/admin/accounts', methods=['GET', 'POST'], defaults={'msg': '', 'search' : '', 'status': '', 'activation': '', 'role': '', 'order': 'DESC', 'order_by': '', 'page': 1})
def admin_accounts(msg, search, status, activation, role, order, order_by, page):
    # Check if admin is logged-in
	if not admin_loggedin():
		return redirect(url_for('authentication.login'))
	# Params validation
	msg = '' if msg == 'n0' else msg
	search = '' if search == 'n0' else search
	status = '' if status == 'n0' else status
	activation = '' if activation == 'n0' else activation
	role = '' if role == 'n0' else role
	order = 'DESC' if order == 'DESC' else 'ASC'
	order_by_whitelist = ['id','username','email','activation_code','role','registered','last_seen']
	order_by = order_by if order_by in order_by_whitelist else 'id'
	results_per_page = 20
	param1 = (page - 1) * results_per_page
	param2 = results_per_page
	param3 = '%' + search + '%'
	# SQL where clause
	where = '';
	where += 'WHERE (username LIKE %s OR email LIKE %s) ' if search else ''
	# Add filters
	if status == 'active':
		where += 'AND last_seen > date_sub(now(), interval 1 month) ' if where else 'WHERE last_seen > date_sub(now(), interval 1 month) '
	if status == 'inactive':
		where += 'AND last_seen < date_sub(now(), interval 1 month) ' if where else 'WHERE last_seen < date_sub(now(), interval 1 month) '
	if activation == 'pending':
		where += 'AND activation_code != '+_ACCOUNT_STATUS_ACTIVATED if where else 'WHERE activation_code != '+_ACCOUNT_STATUS_ACTIVATED
	if role:
		where += 'AND role = %s ' if where else 'WHERE role = %s '
	# Params array and append specified params
	params = []
	if search:
		params.append(param3)
		params.append(param3)
	if role:
		params.append(role)
	# Fetch the total number of accounts
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	cursor.execute('SELECT COUNT(*) AS total FROM user ' + where, params)
	accounts_total = cursor.fetchone()
	# Append params to array
	params.append(param1)
	params.append(param2)
    # Retrieve all accounts from the database
	cursor.execute('SELECT * FROM user ' + where + ' ORDER BY ' + order_by + ' ' + order + ' LIMIT %s,%s', params)
	accounts = cursor.fetchall()
	# Determine the URL
	url = url_for('authentication.admin_accounts') + '/n0/' + (search if search else 'n0') + '/' + (status if status else 'n0') + '/' + (activation if activation else 'n0') + '/' + (role if role else 'n0')
	# Handle output messages
	if msg:
		if msg == 'msg1':
			msg = 'Account created successfully!';
		if msg == 'msg2': 
			msg = 'Account updated successfully!';
		if msg == 'msg3':
			msg = 'Account deleted successfully!'
	# Render the accounts template
	return render_template('authentication-codeshack/admin/accounts.html', accounts=accounts, selected='accounts', selected_child='view', msg=msg, page=page, search=search, status=status, activation=activation, role=role, order=order, order_by=order_by, results_per_page=results_per_page, accounts_total=accounts_total['total'], math=math, url=url, time_elapsed_string=time_elapsed_string)

# http://localhost:5000/accounts/authentication-codeshack/admin/roles - view account roles
@authentication_blueprint.route('/authentication-codeshack/admin/roles', methods=['GET', 'POST'])
def admin_roles():
	# Check if admin is logged-in
	if not admin_loggedin():
		return redirect(url_for('authentication.login'))
	# Set the connection cursor
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	# Select and group roles from the accounts table
	cursor.execute('SELECT role, COUNT(*) as total FROM user GROUP BY role')
	roles = cursor.fetchall()
	new_roles = {}
	# Update the structure
	for role in roles:
		new_roles[role['role']] = role['total']
	for role in ['Admin', 'Member', 'Guest']:
		if not role in new_roles:
			new_roles[role] = 0
	# Get the total number of active roles
	cursor.execute('SELECT role, COUNT(*) as total FROM user WHERE last_seen > date_sub(now(), interval 1 month) GROUP BY role')
	roles_active = cursor.fetchall()
	new_roles_active = {}
	for role in roles_active:
		new_roles_active[role['role']] = role['total']
	# Get the total number of inactive roles
	cursor.execute('SELECT role, COUNT(*) as total FROM user WHERE last_seen < date_sub(now(), interval 1 month) GROUP BY role')
	roles_inactive = cursor.fetchall()
	new_roles_inactive = {}
	for role in roles_inactive:
		new_roles_inactive[role['role']] = role['total']
	# Render he roles template
	return render_template('authentication-codeshack/admin/roles.html', selected='roles', selected_child='', enumerate=enumerate, roles=new_roles, roles_active=new_roles_active, roles_inactive=new_roles_inactive)

# http://localhost:5000/accounts/authentication-codeshack/admin/settings - manage settings
@authentication_blueprint.route('/authentication-codeshack/admin/settings/<string:msg>', methods=['GET', 'POST'])
@authentication_blueprint.route('/authentication-codeshack/admin/settings', methods=['GET', 'POST'], defaults={'msg': ''})
def admin_settings(msg):
	# Check if admin is logged-in
	if not admin_loggedin():
		return redirect(url_for('authentication.login'))
	# Get settings
	settings = get_settings()
	# Set the connection cursor
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	# If user submitted the form
	if request.method == 'POST' and request.form:
		# Retrieve the form data
		data = request.form
		# Iterate the form data
		for key, value in data.items():
			# Check if checkbox is checked
			if 'true' in request.form.getlist(key):
				value = 'true'
			# Convert boolean values to lowercase
			value = value.lower() if value.lower() in ['true', 'false'] else value
			# Update setting
			cursor.execute('UPDATE settings SET setting_value = %s WHERE setting_key = %s', (value,key,))
			mysql.connection.commit()
		# Redirect and output message
		return redirect(url_for('authentication.admin_settings', msg='msg1'))
	# Handle output messages
	if msg and msg == 'msg1':
		msg = 'Settings updated successfully!';
	else:
		msg = ''
	# Render the settings template
	return render_template('authentication-codeshack/admin/settings.html', selected='settings', selected_child='', msg=msg, settings=settings, settings_format_tabs=settings_format_tabs, settings_format_form=settings_format_form)

# http://localhost:5000/accounts/authentication-codeshack/admin/about - view the about page
@authentication_blueprint.route('/authentication-codeshack/admin/about', methods=['GET', 'POST'])
def admin_about():
	# Check if admin is logged-in
	if not admin_loggedin():
		return redirect(url_for('authentication.login'))
	# Render the about template
	return render_template('authentication-codeshack/admin/about.html', selected='about', selected_child='')

# http://localhost:5000/accounts/authentication-codeshack/admin/accounts/delete/<id> - delete account
@authentication_blueprint.route('/authentication-codeshack/admin/accounts/delete/<int:id>', methods=['GET', 'POST'])
@authentication_blueprint.route('/authentication-codeshack/admin/accounts/delete', methods=['GET', 'POST'], defaults={'id': None})
def admin_delete_account(id):
	# Check if admin is logged-in
	if not admin_loggedin():
		return redirect(url_for('authentication.login'))
	# Set the database connection cursor
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	# Delete account from database by the id get request param
	cursor.execute('DELETE FROM user WHERE id = %s', (id,))
	mysql.connection.commit()
	# Redirect to accounts page and output message
	return redirect(url_for('authentication.admin_accounts', msg='msg3', activation='n0', order='id', order_by='DESC', page=1, role='n0', search='n0', status='n0'))

# http://localhost:5000/accounts/authentication-codeshack/admin/account/<optional:id> - create or edit account
@authentication_blueprint.route('/authentication-codeshack/admin/account/<int:id>', methods=['GET', 'POST'])
@authentication_blueprint.route('/authentication-codeshack/admin/account', methods=['GET', 'POST'], defaults={'id': None})
def admin_account(id):
	# Check if admin is logged-in
	if not admin_loggedin():
		return redirect(url_for('authentication.login'))
	# Default page (Create/Edit)
	page = 'Create'
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	# Default input account values
	account = {
		'username': '',
		'password': '',
		'email': '',
		'activation_code': '',
		'rememberme': '',
		'role': 'Member',
		'registered': str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
		'last_seen': str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
	}
	roles = ['Member', 'Admin','Guest']
    # GET request ID exists, edit account
	if id:
        # Edit an existing account
		page = 'Edit'
        # Retrieve account by ID with the GET request ID
		cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
		account = cursor.fetchone()
		# If user submitted the form
		if request.method == 'POST' and 'submit' in request.form:
            # update account
			password = account['password']
			# If password exists in POST request
			if request.form['password']:
				password = hash_generate(request.form['password'], app.secret_key)
			# Update account details
			cursor.execute('UPDATE user SET username = %s, password = %s, email = %s, activation_code = %s, rememberme = %s, role = %s, registered = %s, last_seen = %s WHERE id = %s', (request.form['username'],password,request.form['email'],request.form['activation_code'],request.form['rememberme'],request.form['role'],request.form['registered'],request.form['last_seen'],id,))
			mysql.connection.commit()
			# Redirect to admin accounts page
			return redirect(url_for('authentication.admin_accounts', msg='msg2', activation='n0', order='id', order_by='DESC', page=1, role='n0', search='n0', status='n0'))
		if request.method == 'POST' and 'delete' in request.form:
            # delete account
			return redirect(url_for('authentication.admin_delete_account', id=id))
	if request.method == 'POST' and request.form['submit']:
        # Create new account, hash password
		password = hash_generate(request.form['password'], app.secret_key)
		# Insert account into database
		cursor.execute('INSERT INTO user (username,password,email,activation_code,rememberme,role,registered,last_seen) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (request.form['username'],password,request.form['email'],request.form['activation_code'],request.form['rememberme'],request.form['role'],request.form['registered'],request.form['last_seen'],))
		mysql.connection.commit()
		# Redirect to the admin accounts page and output message
		return redirect(url_for('authentication.admin_accounts', msg='msg1', activation='n0', order='id', order_by='DESC', page=1, role='n0', search='n0', status='n0'))
	# Render the admin account template
	account_statuses = [_ACCOUNT_STATUS_NOT_CONFIRMED, _ACCOUNT_STATUS_CONFIRMED, _ACCOUNT_STATUS_ACTIVATED]
	return render_template('authentication-codeshack/admin/account.html', account=account, selected='accounts', selected_child='manage', page=page, roles=roles, account_statuses=account_statuses, datetime=datetime.datetime, str=str)

@authentication_blueprint.route('/authentication-codeshack/admin/account/impersonate/<int:id>', methods=['GET', 'POST'])
def admin_impersonate_user(id):
	"""Admin enter account with id"""
	if not admin_loggedin():
		return redirect(url_for('authentication.login'))
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
	account = cursor.fetchone()
	account["role"] = "Admin"
	response = create_session_data(account, respond_success=False)
	return response

# http://localhost:5000/accounts/authentication-codeshack/admin/emailtemplate - admin email templates page, manage email templates
@authentication_blueprint.route('/authentication-codeshack/admin/emailtemplate/<string:msg>', methods=['GET', 'POST'])
@authentication_blueprint.route('/authentication-codeshack/admin/emailtemplate', methods=['GET', 'POST'], defaults={'msg': ''})
def admin_emailtemplate(msg):
	# Check if admin is logged-in
	if not admin_loggedin():
		return redirect(url_for('authentication.login'))
	# Get the template directory path
	template_dir = os.path.join(os.path.dirname(__file__), '../templates')
	# Update the template file on save
	if request.method == 'POST':
		# Update activation template
		activation_email_template = request.form['activation_email_template'].replace('\r', '')
		open(template_dir + '/authentication-codeshack/activation-email-template.html', mode='w', encoding='utf-8').write(activation_email_template)
		# Update twofactor template
		twofactor_email_template = request.form['twofactor_email_template'].replace('\r', '')
		open(template_dir + '/authentication-codeshack/twofactor-email-template.html', mode='w', encoding='utf-8').write(twofactor_email_template)
		# Redirect and output success message
		return redirect(url_for('authentication.admin_emailtemplate', msg='msg1'))
	# Read the activation email template
	activation_email_template = open(template_dir + '/authentication-codeshack/activation-email-template.html', mode='r', encoding='utf-8').read()
	# Read the twofactor email template
	twofactor_email_template = open(template_dir + '/authentication-codeshack/twofactor-email-template.html', mode='r', encoding='utf-8').read()
	# Handle output messages
	if msg and msg == 'msg1':
		msg = 'Email templates updated successfully!';
	else:
		msg = ''
	# Render template
	return render_template('authentication-codeshack/admin/emailtemplates.html', selected='emailtemplate', selected_child='', msg=msg, activation_email_template=activation_email_template, twofactor_email_template=twofactor_email_template)

# Admin logged-in check function
def admin_loggedin():
    if loggedin() and session['role'] == 'Admin':
        # admin logged-in
        return True
    # admin not logged-in return false
    return False

# format settings key
def settings_format_key(key):
    key = key.lower().replace('_', ' ').replace('url', 'URL').replace('db ', 'Database ').replace(' pass', ' Password').replace(' user', ' Username')
    return key.title()

# Format settings variables in HTML format
def settings_format_var_html(key, value):
	html = ''
	type = 'text'
	type = 'password' if 'pass' in key else type
	type = 'checkbox' if value.lower() in ['true', 'false'] else type
	checked = ' checked' if value.lower() == 'true' else ''
	html += '<label for="' + key + '">' + settings_format_key(key) + '</label>'
	if (type == 'checkbox'):
		html += '<input type="hidden" name="' + key + '" value="false">'
	html += '<input type="' + type + '" name="' + key + '" id="' + key + '" value="' + value + '" placeholder="' + settings_format_key(key) + '"' + checked + '>'
	return html

# Format settings tabs
def settings_format_tabs(tabs):
	html = ''
	html += '<div class="tabs">'
	html += '<a href="#" class="active">General</a>'
	for tab in tabs:
		html += '<a href="#">' + tab + '</a>'
	html += '</div>'
	return html

# Format settings form
def settings_format_form(settings):
	html = ''
	html += '<div class="tab-content active">'
	category = ''
	for setting in settings:
		if category != '' and category != settings[setting]['category']:
			html += '</div><div class="tab-content">'
		category = settings[setting]['category']
		if (setting == "account_activation"):
			html += '<select name="account_activation" id="account-activation-select">'
			for option in [_ACCOUNT_ACTIVATION_NOT_REQUIRED, _ACCOUNT_ACTIVATION_AUTOMATED, _ACCOUNT_ACTIVATION_MANUAL]:
				selected_value = "selected" if option == settings[setting]['value'] else ""
				html += '<option {0} value="{1}">{1}</option>'.format(selected_value, option)
			html += '</select>'
		else:
			html += settings_format_var_html(settings[setting]['key'], settings[setting]['value'])
	html += '</div>'
	return html

# Get settings from database
def get_settings():
	cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
	cursor.execute('SELECT * FROM settings ORDER BY id')
	settings = cursor.fetchall()
	settings2 = {}
	for setting in settings:
		settings2[setting['setting_key']] = { 'key': setting['setting_key'], 'value': setting['setting_value'], 'category': setting['category'] }
	return settings2

# Format datetime
def time_elapsed_string(dt):
	try:
		d = datetime.datetime.strptime(str(dt), '%Y-%m-%d %H:%M:%S')
	except Exception:
		return ""
	dd = datetime.datetime.now()
	d = d.timestamp() - dd.timestamp()
	d = datetime.timedelta(seconds=d)
	timeDelta = abs(d)
	if timeDelta.days > 0:
		if timeDelta.days == 1:
			return '1 day ago'
		else:
			return '%s days ago' % timeDelta.days
	elif round(timeDelta.seconds / 3600) > 0:
		if round(timeDelta.seconds / 3600) == 1:
			return '1 hour ago'
		else:
			return '%s hours ago' % round(timeDelta.seconds / 3600)
	elif round(timeDelta.seconds / 60) < 2:
		return '1 minute ago'
	else:
		return '%s minutes ago' % round(timeDelta.seconds / 60) 