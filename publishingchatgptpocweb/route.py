from datetime import timedelta
import json
import logging
import threading
from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
# from werkzeug.middleware.proxy_fix import ProxyFix
from core.auth import Auth
from core.config import PathConfig, settings
from scripts import ai, file

app = Flask(__name__, template_folder=PathConfig.TEMPLATE_DIRECTORY, static_folder=PathConfig.STATIC_DIRECTORY)
# app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
app.config['SESSION_TYPE'] = settings.FLASK_SESSION_TYPE
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SECRET_KEY'] = settings.FLASK_SECRET_KEY
app.secret_key = settings.FLASK_SECRET_KEY
app.config['PREFERRED_URL_SCHEME'] = 'https'

app.config['BASE_PATH'] = settings.DEPLOYED_BASE_PATH
app.config['BASE_PATH'] ='' if settings.DEPLOYED_BASE_PATH =='/' else settings.DEPLOYED_BASE_PATH

Session(app)
PathConfig.init_app(app)
auth_instance = Auth()
file_instance = file.FILES(PathConfig)
ai_instance = ai.AI(settings, PathConfig, file_instance)

@app.before_request
def before_request_func():
    open_endpoints = ['authorize', 'signin-oidc', 'get_user_oid', 'static', 'health', 'healthkubernetes']
    if request.endpoint in open_endpoints:
        return  
    if 'user' not in session and request.endpoint not in open_endpoints:
        return redirect(auth_instance.build_auth_url())

@app.route("/signin-oidc")
def authorize():
    session.permanent = True
    session["state"] = request.args.get("state")
    session["nonce"] = request.args.get("nonce")
    code = request.args.get('code')
    
    if not code:
        return "No code returned from Azure AD.", 400
    
    cache = auth_instance.load_cache()
    
    result = auth_instance.build_msal_app(cache=cache).acquire_token_by_authorization_code(
        code,
        scopes=[],  
        redirect_uri=auth_instance.get_auth_redirect_uri())
    auth_instance.save_cache(cache)

    if "error" in result:
        return f"Authentication error: {result['error']}.", 500

    user = result.get("id_token_claims")
    session["user"] = user['oid']
    session["user_name"] = user['name']
    session["user_email"] = user['preferred_username']

    return redirect(url_for('index'))

@app.route('/get_user_oid')
def get_user_oid():
    if 'user' in session:
        return jsonify(oid=session['user']), 200
    else:
        return jsonify(error='User not authenticated', auth_url=auth_instance.build_auth_url()), 401

@app.route('/')
def index():
    try:
        ai_instance.init_retieval_qa()
        return render_template('index.html')
    except Exception as e:
        logging.error(f"Exception occurred while rendering index template: {e}")
        return "An error occurred while loading the page."
    
@app.route('/about')
def about():
    try:
        return render_template('about.html')
    except Exception as e:
        logging.error(f"Exception occurred while rendering about template: {e}")
        return "An error occurred while loading the page."

@app.route('/health')
def health():
    return 'healthy'

@app.route('/health/kubernetes')
def healthkubernetes():
    return 'healthy'

@app.route('/fetchconcepts', methods=['POST'])
def fetchconceptsfromtext():
    response = {}
    text = request.form['text']   
    try:
        concepts = ai_instance.fetch_concepts(text)
        response['text'] = text
        response['concepts'] = concepts
    except Exception as ex:
        response['concepts'] = {}
        response['report_data'] = None

    return response

@app.route('/fetchsources', methods=['POST'])
def fetchsourcesfrompans():
    response = {}
    pans_string = request.form['pans']
    pans = pans_string.split(',')

    try:
        sources = ai_instance.fetch_sources(pans)
        response['sources'] = sources
    except Exception as ex:
        response['sources'] = []
    return response

@app.route('/get_answer_sse', methods=['GET'])
def handle_get_answer_sse():
    sessionId = request.args.get('sessionId')  

    try:
        text = request.args.get('text')  
        temperature = request.args.get('temperature')  
        frequency_penalty = request.args.get('frequency_penalty')  
        presence_penalty = request.args.get('presence_penalty')  

        # Get the event stream generator for this sesssionid
        callback_instance = ai_instance.get_callback_instance(sessionId)
        event_stream_generator = callback_instance.event_stream()
        
        # Process the query to start generating responses
        threading.Thread(target=ai_instance.process_query_answer, args=(callback_instance, text, temperature, frequency_penalty, presence_penalty)).start()

        return Response(event_stream_generator, content_type='text/event-stream')

    except Exception as e:
        error_message = str(e)
        error_data = {
            'sessionId': sessionId, 
            'status': 'error', 
            'message': error_message
        }
        return Response(f"event: error\ndata: {json.dumps(error_data)}\n\n", content_type='text/event-stream')

if __name__ == '__main__':
    app.run(host='localhost', port=5000)