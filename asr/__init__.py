import uuid

import gevent.monkey
gevent.monkey.patch_all()
import base64
from email.mime.multipart import MIMEMultipart
from email.message import Message
import json
import struct
import os

import requests
from flask import Flask, request, Response, abort

# new
from requests_toolbelt.multipart import decoder
import datetime

from .speex_utils import spx2pcm, pcm2wav
from .vosk_client import transcript
from pydub import AudioSegment as am

app = Flask(__name__)

AUTH_URL = "https://auth.rebble.io"
API_KEY = '' #os.environ['SPEECH_API_KEY']


# We know gunicorn does this, but it doesn't *say* it does this, so we must signal it manually.
@app.before_request
def handle_chunking():
    request.environ['wsgi.input_terminated'] = 1


def parse_chunks(stream):
    boundary = b'--' + request.headers['content-type'].split(';')[1].split('=')[1].encode('utf-8').strip()  # super lazy/brittle parsing.
    this_frame = b''
    while True:
        content = stream.read(4096)
        this_frame += content
        end = this_frame.find(boundary)
        if end > -1:
            frame = this_frame[:end]
            this_frame = this_frame[end + len(boundary):]
            if frame != b'':
                try:
                    header, content = frame.split(b'\r\n\r\n', 1)
                except ValueError:
                    continue
                yield content[:-2]
        if content == b'':
            print("End of input.")
            break


@app.route('/heartbeat')
def heartbeat():
    return 'ok'

@app.route('/NmspServlet/', methods=["POST"])
def recognise():
    stream = request.stream

    #access_token, part1, part2 = request.host.split('.', 1)[0].split('-', 3)
    access_token = request.host.split('.')[0].split('-')[0]
    part1 = 'en'
    part2 = 'US'
    lang = f"{part1}-{part2.upper()}"

    auth_req = requests.get(f"{AUTH_URL}/api/v1/me/token", headers={'Authorization': f"Bearer {access_token}"})
    if not auth_req.ok:
        abort(401)

    chunks = iter(list(parse_chunks(stream)))
    
    content = next(chunks).decode('utf-8')
    extra = next(chunks).decode('utf-8')

    voice_data = b''.join((struct.pack('B', len(x)) + x for x in chunks)) 

    file_name = '/tmp/out-' + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S:%s")
    
    output_file = open(file_name + '.spx', 'wb')
    output_file.write(voice_data)
    output_file.close()

    # spx -> pcm -> wav
    pcm2wav(spx2pcm(voice_data), file_name)
    
    # downsample wav: 16000 -> 8000
    sound = am.from_file(file_name+'.wav', format='wav', frame_rate=16000)
    sound = sound.set_frame_rate(8000)
    sound.export(file_name+'-8k.wav', format='wav')

    # speech to text
    json_data = json.loads(transcript(file_name+'-8k.wav'))

    words = []
    text = json_data["text"]

    if len(text) > 0:
        words.append({'word': text})
        
    # Now for some reason we also need to give back a mime/multipart message...
    parts = MIMEMultipart()
    response_part = Message()
    response_part.add_header('Content-Type', 'application/JSON; charset=utf-8')

    if len(words) > 0:
        response_part.add_header('Content-Disposition', 'form-data; name="QueryResult"')
        words[0]['word'] += '\\*no-space-before'
        words[0]['word'] = words[0]['word'][0].upper() + words[0]['word'][1:]
        json_data = json.dumps({'words': [words]})
        response_part.set_payload(json_data)
    else:
        response_part.add_header('Content-Disposition', 'form-data; name="QueryRetry"')
        # Other errors probably exist, but I don't know what they are.
        # This is a Nuance error verbatim.
        response_part.set_payload(json.dumps({
            "Cause": 1,
            "Name": "AUDIO_INFO",
            "Prompt": "Sorry, speech not recognized. Please try again."
        }))
    parts.attach(response_part)

    parts.set_boundary('--Nuance_NMSP_vutc5w1XobDdefsYG3wq')

    parts_string = '\r\n' + parts.as_string().split("\n", 3)[3].replace('\n', '\r\n')
    # print(parts_string)
    response = Response(parts_string)
    #response = Response('\r\n' + parts.as_string().split("\n", 3)[3].replace('\n', '\r\n'))
    response.headers['Content-Type'] = f'multipart/form-data; boundary={parts.get_boundary()}'
    print(response.headers)
    print(response.get_data())
    print('===')
    return response


