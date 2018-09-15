from flask import Flask
from flask_session import Session
from flask_pymongo import PyMongo
from source.Todo import todo
from flask import g
import pymongo
import config
import configparser

#app init
app = Flask(__name__)
#get session config
app.config.from_pyfile('config.py')

Session(app)
#blueprint register
app.register_blueprint(todo,url_prefix='/todo')
#get db parameter
config = configparser.ConfigParser()
config.read('parameter.ini')
server = config.get('DB','host')
port = config.getint('DB','port')

@app.before_request
def before_request():
    #open db connection & set into g
    if 'db' not in g:
        client = pymongo.MongoClient(host=server, port=port)
        g.db = client


@app.teardown_request
def teardown_request(exception):
    #close db connection & remove from g
    if hasattr(g,"db"):
        g.db.close()
        g.pop('db', None)

#action in the middle of application and server(werkzeug)
class AppMiddleware(object):
    def __init__(self, app, script_name=''):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        '''
        script_name = self.script_name
        if self.script_name:
            environ['SCRIPT_NAME'] = script_name

            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
        '''
        return self.app(environ, start_response)

app.wsgi_app = AppMiddleware(app.wsgi_app)

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)