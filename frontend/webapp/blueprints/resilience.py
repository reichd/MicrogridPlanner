from flask import Blueprint, render_template, redirect, url_for
from extensions import user_info_wrapper

resilience_blueprint = Blueprint('resilience', __name__)

@resilience_blueprint.route('/')
@user_info_wrapper
def home(username, role):
	return redirect(url_for('resilience.compute', method="deterministic"))
	# Replace return redirect with the following to enable multiple methods
	# return render_template(
	# 	'tools/resilience/home.html',
	# 	username=username,
	# 	role=role,
	# 	active_page='resilience',
	# )

@resilience_blueprint.route('/<method>/')
def method_home(method):
	return redirect(url_for('resilience.compute', method=method))

@resilience_blueprint.route('/<method>/disturbances/')
@user_info_wrapper
def disturbances(username, role, method):
	return render_template(
		'tools/resilience/disturbance-repair.html',
		username=username,
		role=role,
		method=method,
		active_page='resilience',
		active_sub_page='disturbances',
		mode='disturbance'
	)

@resilience_blueprint.route('/<method>/disturbances/<id>/')
@user_info_wrapper
def disturbance_detail(username, role, method, id):
	return render_template(
		'tools/resilience/disturbance-repair-detail.html',
		username=username,
		role=role,
		method=method,
		active_page='resilience',
		active_sub_page='disturbances',
		id=id,
		mode='disturbance'
	)

@resilience_blueprint.route('/<method>/repairs/')
@user_info_wrapper
def repairs(username, role, method):
	return render_template(
		'tools/resilience/disturbance-repair.html',
		username=username,
		role=role,
		method=method,
		active_page='resilience',
		active_sub_page='repairs',
		mode='repair'
	)

@resilience_blueprint.route('/<method>/repairs/<id>/')
@user_info_wrapper
def repair_detail(username, role, method, id):
	return render_template(
		'tools/resilience/disturbance-repair-detail.html',
		username=username,
		role=role,
		method=method,
		active_page='resilience',
		active_sub_page='repairs',
		id=id,
		mode='repair'
	)

@resilience_blueprint.route('/<method>/compute/')
@user_info_wrapper
def compute(username, role, method):
	return render_template(
		'tools/resilience/compute.html',
		username=username,
		role=role,
		method=method,
		active_page='resilience',
		active_sub_page='compute'
	)

@resilience_blueprint.route('/<method>/results/', defaults={"id":None})
@resilience_blueprint.route('/<method>/results/<id>/')
@user_info_wrapper
def results(username, role, id, method):
	if id is not None:
		return render_template(
				'tools/resilience/result.html', 
				username=username, 
				role=role, 
				method=method,
				active_page='resilience', 
				active_sub_page='results',
				id=id,
			)
	return render_template(
			'tools/resilience/results.html', 
			username=username, 
			role=role, 
			method=method,
			active_page='resilience', 
			active_sub_page='results',
  		)
