document.addEventListener('DOMContentLoaded', function () {
    const chatBox = document.getElementById('chat_box');
    const inputField = document.getElementById('input_field');
    const enterButton = document.getElementById('enter_button');
    const returnImage = document.getElementById('return_image');

    let flow = null;          // loaded from /api/config
    let phase = 'loading';    // loading -> topic -> words -> generating -> done
    let wordIndex = 0;
    let storyData = {};

    // --- Chat box helpers ---------------------------------------------------

    function updateChatBox(message) {
        chatBox.innerHTML += `<div>${message}<br><br></div>`;
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function chatlibsSays(message) {
        updateChatBox(`<strong>ChatLibs: </strong>${message}`);
    }

    function lockInput() {
        enterButton.classList.add('button-waiting');
        enterButton.disabled = true;
        inputField.disabled = true;
    }

    function unlockInput() {
        enterButton.classList.remove('button-waiting');
        enterButton.disabled = false;
        inputField.disabled = false;
        inputField.focus();
    }

    function hideInput() {
        inputField.classList.add('hidden-element');
        enterButton.classList.add('hidden-element');
    }

    // --- Server calls -------------------------------------------------------

    async function callApi(url, body) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        let data = {};
        try { data = await response.json(); } catch (e) { /* non-JSON error */ }
        if (!response.ok || data.error) {
            throw new Error(data.error || `Request failed (${response.status})`);
        }
        return data;
    }

    // --- Word emphasis (highlights the user's words in the swapped story) ---

    function emphasizeStory(story) {
        let emphasized = story;
        flow.words.forEach(function (w) {
            const word = storyData[w.slot];
            if (!word) return;
            const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`\\b${escaped}\\b`, 'gi');
            emphasized = emphasized.replace(
                regex,
                `<em><strong><u>&nbsp;${word}&nbsp;</u></strong></em>`
            );
        });
        return emphasized;
    }

    // --- Restart ------------------------------------------------------------

    function offerRestart() {
        const link = document.createElement('a');
        link.href = '#';
        link.textContent = 'Write another story';
        link.addEventListener('click', function (e) {
            e.preventDefault();
            restart();
        });
        const wrapper = document.createElement('div');
        wrapper.innerHTML = '<strong>ChatLibs: </strong>';
        wrapper.appendChild(link);
        wrapper.innerHTML += '<br><br>';
        chatBox.appendChild(wrapper);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function restart() {
        storyData = {};
        wordIndex = 0;
        chatBox.innerHTML = '&nbsp;';
        returnImage.src = '';
        returnImage.classList.add('image-waiting');
        inputField.classList.remove('hidden-element');
        enterButton.classList.remove('hidden-element');
        startTopicPhase();
    }

    // --- Flow phases --------------------------------------------------------

    function startTopicPhase() {
        phase = 'topic';
        chatlibsSays(flow.intro);
        unlockInput();
    }

    function promptNextWord() {
        chatlibsSays(flow.words[wordIndex].prompt);
        unlockInput();
    }

    async function handleTopic(topic) {
        chatlibsSays('Thinking about your story...');
        const storyResp = await callApi('/api/story', { topic: topic });
        storyData.story = storyResp.story;

        const titleResp = await callApi('/api/title', { story: storyData.story });
        storyData.title = titleResp.title;
        chatlibsSays(`Your story is: <br><strong>${storyData.title}</strong>`);

        phase = 'words';
        wordIndex = 0;
        promptNextWord();
    }

    async function finishStory() {
        phase = 'generating';
        hideInput();
        chatlibsSays('Here we go!...');

        const words = {};
        flow.words.forEach(function (w) { words[w.slot] = storyData[w.slot]; });

        const remixResp = await callApi('/api/remix', {
            story: storyData.story,
            words: words
        });
        storyData.newStory = remixResp.story;

        updateChatBox(`<br><strong>${storyData.title}</strong><br>`);
        updateChatBox(emphasizeStory(storyData.newStory));

        chatlibsSays('Drawing a picture for you!');
        const imageResp = await callApi('/api/image', { story: storyData.newStory });
        storyData.image = imageResp.image;

        returnImage.src = storyData.image;
        returnImage.classList.remove('image-waiting');

        const shareUrl = '/story?title=' + encodeURIComponent(storyData.title) +
            '&description=' + encodeURIComponent(storyData.newStory);
        chatlibsSays('Here is a link to your story you can share:');
        updateChatBox(`<a target="_blank" href="${shareUrl}">${storyData.title}</a>`);

        phase = 'done';
        offerRestart();
    }

    // --- Input handling -----------------------------------------------------

    async function handleSubmit() {
        const userInput = inputField.value.trim();
        if (userInput === '') return;
        inputField.value = '';
        updateChatBox(`<strong>You:</strong> ${userInput}`);
        lockInput();

        try {
            if (phase === 'topic') {
                await handleTopic(userInput);
            } else if (phase === 'words') {
                storyData[flow.words[wordIndex].slot] = userInput;
                wordIndex += 1;
                if (wordIndex < flow.words.length) {
                    promptNextWord();
                } else {
                    await finishStory();
                }
            }
        } catch (err) {
            handleError(err);
        }
    }

    function handleError(err) {
        console.error(err);
        chatlibsSays(
            'Oops — something went wrong (' + err.message + '). ' +
            'Let\'s try that again.'
        );
        if (phase === 'generating') {
            // The story exists but image/remix failed — let them start over.
            offerRestart();
        } else {
            // Recoverable mid-question: re-show the same prompt and re-enable.
            inputField.classList.remove('hidden-element');
            enterButton.classList.remove('hidden-element');
            unlockInput();
        }
    }

    inputField.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            handleSubmit();
        }
    });

    enterButton.addEventListener('click', function () {
        handleSubmit();
    });

    // Mobile: lock zoom while typing, restore on blur (preserved from original).
    document.querySelectorAll('input').forEach(function (input) {
        input.addEventListener('focus', function () {
            document.querySelector('meta[name=viewport]').setAttribute(
                'content',
                'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'
            );
        });
        input.addEventListener('blur', function () {
            document.querySelector('meta[name=viewport]').setAttribute(
                'content', 'width=device-width, initial-scale=1'
            );
        });
    });

    // --- Boot ---------------------------------------------------------------

    lockInput();
    fetch('/api/config')
        .then(function (r) { return r.json(); })
        .then(function (config) {
            flow = config;
            startTopicPhase();
        })
        .catch(function (err) {
            console.error(err);
            chatlibsSays('Could not start the game. Please refresh the page.');
        });
});
