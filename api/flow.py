"""The ChatLibs game flow, as data.

The front end fetches this from ``/api/config`` and drives the whole interaction
off it. Change the game design here — reorder words, add a slot, reword a
prompt — without touching JavaScript or the route handlers.

`words` order and the 6 slots (3 adjectives / 2 nouns / 1 verb) are the same as
the original game; the order the user is asked in is A-N-A-V-A-N.
"""

FLOW = {
    # Shown when the page loads, before the user types the topic.
    "intro": "Enter a topic for the story",

    # Collected one at a time, in this order, after the title is revealed.
    "words": [
        {"slot": "adjective1", "label": "adjective", "prompt": "Please give me an adjective"},
        {"slot": "noun1",      "label": "noun",      "prompt": "And a noun"},
        {"slot": "adjective2", "label": "adjective", "prompt": "How about another adjective"},
        {"slot": "verb",       "label": "verb",      "prompt": "And a verb"},
        {"slot": "adjective3", "label": "adjective", "prompt": "Thanks — tell me one more adjective"},
        {"slot": "noun2",      "label": "noun",      "prompt": "One last noun"},
    ],
}
