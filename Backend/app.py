from flask import Flask, session, jsonify, redirect, request
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import pathlib
import datetime
import pytz
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.secret_key = os.getenv('SECRET_KEY')

# Session configuration
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'  
)

# Scopes required by the API
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Path to the credentials.json file
CLIENT_SECRETS_FILE = os.getenv('GOOGLE_CLIENT_SECRET')
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Path to token.json file
TOKEN_FILE = "A:\\Calendar App\\Backend\\token.json"

@app.route('/')
def home():
    return 'Google Calendar Widget Backend'

# Google OAuth authorization
@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = app.url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session.get('state')
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = app.url_for('oauth2callback', _external=True)

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    with open(TOKEN_FILE, 'w') as token:
        token.write(credentials.to_json())

    return redirect(app.url_for('get_events'))

# Convert datetime to local timezone
def convert_to_local(datetime_str, tz_name='Asia/Kolkata'):
    utc_time = datetime.datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    local_tz = pytz.timezone(tz_name)
    return utc_time.astimezone(local_tz).strftime('%Y-%m-%d %H:%M:%S')

# Add event
@app.route('/add_event', methods=['POST'])
def add_event():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    event_data = request.json
    event = {
        'summary': event_data['summary'],
        'start': {
            'dateTime': event_data['start'],
            'timeZone': event_data['timeZone'],
        },
        'end': {
            'dateTime': event_data['end'],
            'timeZone': event_data['timeZone'],
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()

    return jsonify({'message': 'Event created', 'eventId': event['id']}), 201

# Get Events from all calendars
@app.route('/events', methods=['GET'])
def get_events():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return redirect('/authorize')

    try:
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # Current time in UTC

        # Get all calendars
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])

        all_events = []  # List to hold events from all calendars

        for calendar in calendars:
            calendar_id = calendar['id']
            events_result = service.events().list(calendarId=calendar_id, timeMin=now,
                                                  maxResults=1000000, singleEvents=True,
                                                  orderBy='startTime').execute()
            events = events_result.get('items', [])

            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                all_events.append({
                    'calendarId': calendar_id,
                    'calendarSummary': calendar['summary'],
                    'eventId': event['id'],
                    'start': convert_to_local(start),
                    'summary': event.get('summary', 'No Title'),
                    'end': event['end'].get('dateTime', event['end'].get('date'))
                })

        return jsonify(all_events)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return redirect('/authorize')

    try:
        service = build('calendar', 'v3', credentials=creds)
        event_data = request.json
        updated_event = {
            'summary': event_data['summary'],
            'start': {'dateTime': event_data['start'], 'timeZone': event_data['timeZone']},
            'end': {'dateTime': event_data['end'], 'timeZone': event_data['timeZone']}
        }
        updated_event = service.events().update(calendarId='primary', eventId=event_id, body=updated_event).execute()
        return jsonify(updated_event)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return redirect('/authorize')

    try:
        service = build('calendar', 'v3', credentials=creds)
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return jsonify({'status': 'Event deleted'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get all calendars
@app.route('/calendars', methods=['GET'])
def get_calendars():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return redirect('/authorize')

    try:
        service = build('calendar', 'v3', credentials=creds)
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])

        calendars_list = []
        for calendar in calendars:
            calendars_list.append({
                'id': calendar['id'],
                'summary': calendar['summary'],
                'timeZone': calendar['timeZone']
            })

        return jsonify(calendars_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
