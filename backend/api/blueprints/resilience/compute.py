from flask import Blueprint
from extensions import get_wrapper, run_analysis

resilience_compute_blueprint = Blueprint("resilience", __name__)

@resilience_compute_blueprint.route("/", methods=["POST"])
@get_wrapper(pass_user_id=True)
def resilience(user_id):
    return run_analysis(user_id, "resilience", time_limit="2-00:00:00", send_email=False)
