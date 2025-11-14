import openai
import os
import requests
#from elevenlabs import generate, set_api_key
from flask import jsonify,request,app, Flask, render_template
import base64
from CourseRecommendation import *

BELLA_VOICE_ID = "EXAVp45aNk4DPDnnGp4f"
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{DEFAULT_VOICE_ID}?output_format=mp3_44100_128"

openai_api_key = os.environ.get("OPENAI_API_KEY")
elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")


def generate_speech(message, id, flag=0):
    """
    Generates speech using the ElevenLabs REST API and returns the audio
    as a base64-encoded string within a JSON response.

    Args:
        message (str): The text to convert to speech.

    Returns:
        JSON: A Flask JSON response containing the audio, message, flag, and id.
    """
    if not elevenlabs_api_key:
        error_message = "ElevenLabs API Key is not set in environment variables."
        print(f"Error: {error_message}")
        return jsonify({'audio': '', 'message': error_message, 'flag': -1, 'id': id})

    headers = {
        "Content-Type": "application/json",
        # The API key is passed in the custom header 'xi-api-key'
        "xi-api-key": elevenlabs_api_key
    }

    payload = {
        "text": message,
        # Using a modern, recommended model
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.75
        }
    }

    try:
        # Make the POST request to the ElevenLabs API
        response = requests.post(
            ELEVENLABS_URL,
            headers=headers,
            json=payload,
            timeout=10 # Set a timeout for the request
        )
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        # The response content is the raw audio binary data (MP3 in this case)
        audio_binary = response.content

        print("\n", message, "\n")

        # Base64 encode the audio binary data
        audio_base64 = base64.b64encode(audio_binary).decode('utf-8')

        # Construct the final data structure, matching the original function's output
        data = {
            'audio': audio_base64,
            'message': message,
            'flag': flag,
            'id': id
        }

        return jsonify(data)

    except requests.exceptions.RequestException as e:
        # Handle exceptions like connection errors, timeouts, and bad HTTP status codes
        error_message = f"ElevenLabs API Request Failed: {e}"
        print(f"Error: {error_message}")
        # Return a failure response with the error details
        return jsonify({'audio': '', 'message': error_message, 'flag': -1, 'id': id})


def generate_questions(message):
    messages = [
        {"role": "system", "content": "Generate 5 short theoretical questions to evaluate the user's skills and knowledge in this field. Please keep the questions unique and distinct and target different areas of the said field"},
        {"role": "user", "content": f"User Input: {message}"}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        max_tokens=250
    )
    assistant_response = response.choices[0].message['content']
    generated_questions = assistant_response.split("\n")
    generated_questions = [q.strip() for q in generated_questions if q.strip()]

    print(generated_questions,"\n",len(generated_questions))
    return generated_questions

def eval_answer(evaluation_questions,ans_list):
    messages = [
        {"role": "system", "content": "Based on the set of questions and their corresponding answers, generate a phrase of 2-3 words consisting of the user's level (beginner or intermediate or expert) and specifically what field their interest is in. such as 'Beginner Python'"},
        {"role": "user", "content": f"Questions: {evaluation_questions}, Answers: {ans_list}"}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        max_tokens=50
    )
    assistant_response = response.choices[0].message['content']
    eval_phrase = assistant_response.split("\n")
    eval_phrase = [q.strip() for q in eval_phrase if q.strip()]

    print(eval_phrase,"\n",len(eval_phrase))
    return str(eval_phrase[0])


ans_list = []
evaluation_questions = []


app = Flask(__name__,template_folder="templates")

@app.route("/", methods=['GET'])
def default():
    return render_template("view.html")

@app.route("/getQues", methods=['POST','GET'])
def question_generator():
    global evaluation_questions
    data = request.get_json()
    message = "No answer provided"
    data = dict(data)
    message = data['message']
    flag = int(data['flag'])
    i = int(data['i'])
        

    if flag==1:
        i=0
        evaluation_questions = generate_questions(message)
    else: 
        ans_list.append(message)

    if i>4:
        msg = courseRecommender(eval_answer(evaluation_questions,ans_list))
        return generate_speech(msg,-300)
    else:
        msg = evaluation_questions[i]
        return generate_speech(msg,i)

if __name__ == '__main__':
    app.run()
