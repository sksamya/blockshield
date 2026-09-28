from flask import Blueprint, jsonify
from backend.simulator.scenarios import scenario_runner

simulator_bp = Blueprint("simulator", __name__, url_prefix="/api/simulator")

@simulator_bp.route("/run/1", methods=["POST", "GET"])
def run_scenario_1():
    res = scenario_runner.run_scenario_1_fraud_swap()
    return jsonify(res), 200

@simulator_bp.route("/run/2", methods=["POST", "GET"])
def run_scenario_2():
    res = scenario_runner.run_scenario_2_prenotified_swap()
    return jsonify(res), 200

@simulator_bp.route("/run/3", methods=["POST", "GET"])
def run_scenario_3():
    res = scenario_runner.run_scenario_3_unnotified_legitimate_swap()
    return jsonify(res), 200

@simulator_bp.route("/run/4", methods=["POST", "GET"])
def run_scenario_4():
    res = scenario_runner.run_scenario_4_old_swap()
    return jsonify(res), 200

@simulator_bp.route("/run/5", methods=["POST", "GET"])
def run_scenario_5():
    res = scenario_runner.run_scenario_5_mule_flag_sharing()
    return jsonify(res), 200

@simulator_bp.route("/run/6", methods=["POST", "GET"])
def run_scenario_6():
    res = scenario_runner.run_scenario_6_audit_tampering()
    return jsonify(res), 200

@simulator_bp.route("/run-all", methods=["POST", "GET"])
def run_all():
    results = [
        scenario_runner.run_scenario_1_fraud_swap(),
        scenario_runner.run_scenario_2_prenotified_swap(),
        scenario_runner.run_scenario_3_unnotified_legitimate_swap(),
        scenario_runner.run_scenario_4_old_swap(),
        scenario_runner.run_scenario_5_mule_flag_sharing(),
        scenario_runner.run_scenario_6_audit_tampering()
    ]
    all_passed = all(r.get("success", False) for r in results)
    return jsonify({
        "status": "completed",
        "all_scenarios_passed": all_passed,
        "scenarios": results
    }), 200
