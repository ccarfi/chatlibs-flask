document.addEventListener('DOMContentLoaded', function() {
    const chatBox = document.getElementById('chat_box');
    const inputField = document.getElementById('input_field');
    const enterButton = document.getElementById('enter_button');
    const returnImage = document.getElementById('return_image');

    let currentStep = 1;
    let storyData = {};

    // Prompts for each step
    const prompts = [
        "<strong>ChatLibs: </strong>Enter a topic for the story",
        "", 
        "<strong>ChatLibs: </strong>Please give me an adjective",
        "<strong>ChatLibs: </strong>And a noun",
        "<strong>ChatLibs: </strong>How about another adjective",
        "<strong>ChatLibs: </strong>And a verb",
        "<strong>ChatLibs: </strong>Thanks — tell me one more adjective",
        "<strong>ChatLibs: </strong>One last noun",
        ""
    ];

    function updateChatBox(message) {
        chatBox.innerHTML += `<div>${message}<br><br></div>`;
        chatBox.scrollTop = chatBox.scrollHeight; // Scroll to the bottom

    }

    function getNextPrompt() {
        const predefinedInput = "none";
        if (currentStep <= prompts.length) {
            switch (currentStep) {
                case 2:
                    sendInputToServer(predefinedInput);
                    break;
                case 9:
                    sendInputToServer(predefinedInput);
                    break;
                default:
                    updateChatBox(prompts[currentStep - 1]);
                    // Change button background back to original and enable it
                    enterButton.classList.remove('button-waiting');
                    enterButton.disabled = false;
                    inputField.disabled = false;
                    inputField.focus();
            }
        }
    }


    function handleResponse(response) {
        console.log("Handle response");
        console.log(response);

        if (response.responseVariableName && response.value) {
            storyData[response.responseVariableName] = response.value;
        }

        if (response.addToChat) {
            updateChatBox(response.addToChat);
        }

        if (currentStep == 2) {
             updateChatBox("<strong>ChatLibs: </strong>Your story is: <br>"+storyData.title);
        }

        if (currentStep == 8) {
             updateChatBox(storyData.newStory);
             emphasizeStoryWords()
             updateChatBox(storyData.newStoryWithEmphasis);
        }
     
        if (currentStep == 9) {
             returnImage.src = storyData.imageURL; // Update the return image with the new image URL
             // Remove the 'image-waiting' class to unhide the image
             returnImage.classList.remove('image-waiting');
        }

        currentStep++;
        getNextPrompt();
    }

function sendInputToServer(input) {
    let url = 'api/route'; // Default URL
    let body = {};
    let doFetch = false;
    console.log("Current step: " + currentStep);
    console.log("Send input to server");

    switch (currentStep) {
        case 1:            
            updateChatBox("<strong>ChatLibs: </strong>Thinking about your story...");
            url = '/write_story';
            body = { topic: input };
            console.log(body);
            doFetch = true;              
            break;
        case 2:
            url = '/get_title';
            body = { data: storyData.story };
            console.log(body);
            doFetch = true;              
            break;
        case 3:
            storyData.adjective1 = input;
            break;
        case 4:
            storyData.adjective2 = input;
            break;
        case 5:
             storyData.adjective3 = input;
            break;
        case 6:
            storyData.noun = input;
            break;
        case 7:
            storyData.verb = input;;
            break;
        case 8:
            updateChatBox("<strong>ChatLibs: </strong>Here we go!...");
            inputField.classList.add('hidden-element');
            enterButton.classList.add('hidden-element');
            url = '/write_newStory';
            body = {
                story: storyData.story,
                adjective1: storyData.adjective1,
                adjective2: storyData.adjective2,
                adjective3: storyData.adjective3,
                noun: storyData.noun,
                verb: storyData.verb,
                lastAdjective: input
            };
            console.log(body);
            doFetch = true;              
            break;
        case 9:
            updateChatBox("<strong>ChatLibs: </strong>Drawing a picture for you!");
            url = '/get_image';
            body = { data: storyData.newStory };
            console.log(body);
            doFetch = true;             
            break;
        default:
            break;
            body = { step: currentStep, input: input, storyData: storyData };
            break;
    }

    if (doFetch) {
      fetch(url, {
          method: 'POST',
          body: JSON.stringify(body),
          headers: {
              'Content-Type': 'application/json'
          }
      })
      .then(response => response.json())
      .then(data => handleResponse(data))
      .catch(error => console.error('Error:', error));
    } else {
        handleResponse("No server step");
    }
}

    function emphasizeStoryWords() {
        // Check if the required data exists
        if (!storyData.newStory || !storyData.adjective1 || !storyData.adjective2 || !storyData.adjective3 || !storyData.noun || !storyData.verb) {
            console.error('Missing story data for emphasis');
            return;
        }

        // List of words to emphasize
        const wordsToEmphasize = [storyData.adjective1, storyData.adjective2, storyData.adjective3, storyData.noun, storyData.verb];

        // Create a new story with emphasis
        let emphasizedStory = storyData.newStory;

        // Replace each word with its emphasized version
        wordsToEmphasize.forEach(word => {
            const regex = new RegExp(`\\b${word}\\b`, 'gi'); // Match the word as a whole word, case-insensitive
            emphasizedStory = emphasizedStory.replace(regex, `<em>${word}</em>`);
        });

        // Assign the new story with emphasis to storyData
        storyData.newStoryWithEmphasis = emphasizedStory;
    }
    
    // Function to handle input submission
    function handleSubmit() {
        const userInput = inputField.value;
        inputField.value = '';
        // Change button background to grey and disable it
        enterButton.classList.add('button-waiting');
        enterButton.disabled=true;
        inputField.disabled=true;
        updateChatBox(`<strong>You:</strong> ${userInput}`);
        sendInputToServer(userInput);
    }

    // Listen for "Enter" key press in the input field
    inputField.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            console.log("type");
            event.preventDefault(); // Prevent the default form submission behavior
            if (inputField.value.trim() !== '') {
                handleSubmit(); // Call the submit function if input is not empty
            }
        }
    });

    // Listen for button click
    enterButton.addEventListener('click', function() {
        console.log("click");
        if (inputField.value.trim() !== '') {
            handleSubmit(); // Call the submit function if input is not empty
        }
    });

    const inputFields = document.querySelectorAll('input');

    inputFields.forEach(input => {
        input.addEventListener('focus', () => {
            document.querySelector('meta[name=viewport]').setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
        });
        input.addEventListener('blur', () => {
            document.querySelector('meta[name=viewport]').setAttribute('content', 'width=device-width, initial-scale=1');
        });
    });


    // Start the conversation with the first prompt

    getNextPrompt();
});
