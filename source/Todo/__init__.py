from flask import Blueprint

todo = Blueprint('todo',__name__,static_folder='..\static',template_folder='..\templates')

from source.Todo import Tori,Tori_detail
