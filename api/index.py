from flask import Flask, render_template, request, jsonify
import os
import openai
import requests

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
imageModel = "dall-e-3"
chatModel = "gpt-4"


# Assuming you have set OPENAI_API_KEY as an environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/write_story', methods=['POST'])
def write_story():
    user_input = request.json['topic']
    prompt = f"Write a creative, silly 75-word children's story about {user_input}. Include characters, a conflict, rising action, a surprising resolution, and a piece of short dialogue."
    try:
        response = openai.ChatCompletion.create(
            model=chatModel,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
    except openai.error.OpenAIError as e:
        # Handle general OpenAI API errors
        print(f"An OpenAI API error occurred: {e}")
    except Exception as e:
        # Handle other exceptions
        print(f"A general error occurred: {e}")
    story_response = {
        "responseVariableName": "story",
        "value": response.choices[0].message['content']
    }
    return jsonify(story_response)


@app.route('/get_title', methods=['POST'])
def get_title():
    story = request.json['data']
    
    prompt = f"Create a catchy and creative title for this children's story: {story}"
    
    response = openai.ChatCompletion.create(
        model=chatModel,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    title_response = {
        "responseVariableName": "title",
        "value": response.choices[0].message['content']
    }
    return jsonify(title_response)


@app.route('/get_image', methods=['POST'])
def get_image():

    story = request.json['data']
    PROMPT = (f"Please create an photorealistic image based on this narrative:\n\n{story}\n")
    response = openai.Image.create(
        model=imageModel,
        prompt=PROMPT,
        n=1,
        size="1024x1024",
    )

    imageURL_response = {
        "responseVariableName": "imageURL",
        "value": response["data"][0]["url"]
    }
    return jsonify(imageURL_response)


@app.route('/write_newStory', methods=['POST'])
def write_newStory():
    data = request.json
    original_story = data.get('story')
    adjective1=data.get('adjective1')
    adjective2=data.get('adjective2')
    adjective3=data.get('adjective3')
    noun1 = data.get('noun1')
    noun2=data.get('noun2')
    verb = data.get('verb')


    prompt = (f"Integrate the replacement values included below into this original story. \n\nOriginal Story:\n{original_story}\n"
             f"Replacement values to add into the story:\n{adjective1}\n{adjective2}\n{adjective3}\n{noun1}\n{noun2}\n{verb}\n\n"
             f"Updated story that includes all the replacement values:")
    response = openai.ChatCompletion.create(
        model=chatModel,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    story_response = {
        "responseVariableName": "newStory",
        "value": response.choices[0].message['content']  
    }
    return jsonify(story_response)

@app.route('/story')
def story():
    image_url = request.args.get('image_url', '')
    title = request.args.get('title', 'Default Title')
    description = request.args.get('description', 'Default Description')
    return render_template('story.html', image_url=image_url, title=title, description=description)


if __name__ == '__main__':
    app.run(debug=True)
