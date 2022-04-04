from flask import Blueprint, jsonify

bp = Blueprint('api', __name__)

@bp.route('/')
def test():
    return jsonify({'status': 'ok'}), 200
