from flask import Blueprint, render_template

bp = Blueprint('admin', __name__, template_folder='templates')

@bp.route('/<page>')
def show(page):
    return render_template(f'admin/{page}.html')
