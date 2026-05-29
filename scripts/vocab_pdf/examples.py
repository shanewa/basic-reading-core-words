"""Varied example sentences for vocabulary PDF rows."""

from __future__ import annotations

from .util import clean_headword

# Multi-word phrases
PHRASE_EXAMPLES: dict[str, str] = {
    "here you are": "Here you are — this book is for you.",
    "good job": "Good job! You finished the puzzle.",
    "good job!": "Good job! You finished the puzzle.",
    "good night": "Good night, Mum. See you tomorrow.",
    "ice cream": "We eat ice cream on hot summer days.",
    "chinese new year": "We visit family at Chinese New Year.",
    "pencil case": "My pencil case is in the schoolbag.",
    "sit down": "Please sit down and open your book.",
    "come on": "Come on, let's go to the park!",
    "look at": "Look at the cow in the field.",
    "look like": "You look like your sister.",
    "lots of": "There are lots of flowers in the garden.",
    "put on": "Put on your coat; it is cold outside.",
    "put up": "We put up lanterns for the festival.",
    "play football": "They play football after school.",
    "every day": "I brush my teeth every day.",
    "in class": "We listen quietly in class.",
    "set the table": "Can you help me set the table for dinner?",
    "jelly bean": "She picked a red jelly bean from the bag.",
    "inline skates": "He wears a helmet on his inline skates.",
    "paper-cut": "Grandma taught me to make a paper-cut.",
    "let's": "Let's play a game together.",
    "let us": "Let us sing the song again.",
    "o'clock": "School starts at eight o'clock.",
}


# Single words — curated sentences (lowercase keys)
WORD_EXAMPLES: dict[str, str] = {
    "hello": "Hello! I am glad to see you.",
    "nice": "It is a nice day for a walk.",
    "meet": "I am happy to meet you.",
    "you": "Can you help me, please?",
    "play": "The children play in the yard.",
    "photo": "This is a photo of my family.",
    "how": "How are you today?",
    "say": "Please say your name loudly.",
    "balloon": "The red balloon floated to the sky.",
    "thank": "I thank you for the lovely gift.",
    "please": "May I have some water, please?",
    "family": "My family eats dinner together.",
    "mum": "Mum reads a story at bedtime.",
    "dad": "Dad drives me to school.",
    "sister": "My sister draws pictures every afternoon.",
    "brother": "My brother plays with the puppy.",
    "classroom": "Our classroom has a big window.",
    "teacher": "The teacher writes on the board.",
    "schoolbag": "I pack my schoolbag every morning.",
    "panda": "The panda eats bamboo at the zoo.",
    "tiger": "We saw a tiger at the wildlife park.",
    "birthday": "We sang Happy Birthday at the party.",
    "weather": "The weather is sunny and warm today.",
    "banana": "She peeled a banana for breakfast.",
    "doctor": "The doctor checks my ears and throat.",
    "monday": "On Monday we have an English lesson.",
    "exciting": "The magic show was very exciting.",
    "funny": "That clown is really funny!",
    "elephant": "An elephant has a long trunk.",
    "butterfly": "A butterfly landed on the flower.",
    "neighbor": "Our neighbor waters the plants when we travel.",
    "surprise": "What a surprise to see you here!",
    "breakfast": "I had eggs and milk for breakfast.",
    "library": "We borrow books from the library.",
}


# Template pools — picked deterministically per word
TEMPLATES: dict[str, list[str]] = {
    "animal": [
        "We saw a {w} at the zoo yesterday.",
        "The little {w} ran across the grass.",
        "Do you know what sound a {w} makes?",
    ],
    "food": [
        "Would you like some {w} for lunch?",
        "Mum bought fresh {w} at the market.",
        "This {w} tastes sweet and yummy.",
    ],
    "color": [
        "She painted the sky {w}.",
        "My favourite colour is {w}.",
        "The {w} kite flew high above us.",
    ],
    "body": [
        "Touch your {w} with one finger.",
        "The doctor looked at my {w}.",
        "We draw a face with eyes and a {w}.",
    ],
    "place": [
        "We walked to the {w} after school.",
        "The {w} is quiet and clean.",
        "Meet me near the {w} at noon.",
    ],
    "vehicle": [
        "The {w} stopped at the station.",
        "We travelled by {w} on holiday.",
        "Look — a big {w} is coming!",
    ],
    "verb": [
        "I {w} with my friends after class.",
        "Can you {w} slowly, please?",
        "Every morning we {w} before breakfast.",
    ],
    "adj": [
        "The room feels {w} and cosy.",
        "Today the weather is {w}.",
        "That was a {w} story, wasn't it?",
    ],
    "number": [
        "I can count up to {w}.",
        "She has {w} pencils in her case.",
        "There are {w} birds on the tree.",
    ],
    "object": [
        "Please put the {w} on the table.",
        "I found my {w} under the bed.",
        "This {w} belongs to the classroom.",
    ],
    "person": [
        "The {w} smiled and waved at us.",
        "Ask the {w} if you need help.",
        "A {w} works at our school.",
    ],
    "time": [
        "We start the lesson at {w}.",
        "See you on {w} morning.",
        "{w} is my favourite day of the week.",
    ],
    "default": [
        "We use the word “{w}” in our story.",
        "Listen and repeat: {w}.",
        "Can you spell “{w}” out loud?",
        "The sentence has the word {w} in it.",
    ],
}

CATEGORY_WORDS: dict[str, set[str]] = {
    "animal": {
        "pet", "bird", "dog", "cat", "fish", "rabbit", "tiger", "lion", "bear",
        "monkey", "panda", "cow", "chicken", "sheep", "horse", "wolf", "bee",
        "frog", "spider", "cricket", "bug", "hippo", "alligator", "puppy",
        "animal", "zoo",
    },
    "food": {
        "apple", "banana", "rice", "noodle", "milk", "bread", "cake", "sweet",
        "eat", "food", "dinner", "lunch", "cheese", "grapes", "carrot", "potato",
        "tomato", "meat", "fruit", "candy", "chocolate", "cookie", "pear",
        "lettuce", "butter", "jam", "ketchup", "bean", "chips", "yummy",
        "delicious", "breakfast",
    },
    "color": {
        "red", "green", "blue", "black", "white", "yellow", "colour",
    },
    "body": {
        "face", "eye", "ear", "nose", "mouth", "hair", "hand", "arm", "leg",
        "foot", "head", "body", "teeth", "touch",
    },
    "place": {
        "home", "school", "classroom", "room", "park", "beach", "farm", "zoo",
        "kitchen", "garden", "house", "forest", "desert", "mountain", "London",
        "store", "yard",
    },
    "vehicle": {
        "bus", "car", "train", "plane", "van", "boat",
    },
    "verb": {
        "go", "run", "eat", "play", "read", "swim", "jump", "sit", "stand",
        "look", "see", "say", "tell", "want", "like", "help", "make", "put",
        "open", "stop", "wait", "move", "know", "live", "wear", "sing", "dance",
        "draw", "kick", "listen", "learn", "walk", "talk", "teach", "wash",
        "smell", "grow", "buy", "catch", "chase", "climb", "fly", "swim",
        "share", "give", "find", "try", "understand", "feel", "hear", "call",
        "dig", "bite", "bark", "splash", "sleep", "wake", "bring", "take",
        "use", "feed", "clean", "tidy", "rock", "move", "shout", "sing",
    },
    "adj": {
        "big", "small", "happy", "sad", "tired", "hungry", "good", "nice",
        "cute", "long", "short", "hot", "cold", "warm", "scary", "funny",
        "exciting", "amazing", "strong", "fast", "slow", "loud", "quiet",
        "clean", "tidy", "safe", "bad", "different", "same", "heavy", "sick",
        "busy", "lucky", "cozy", "delicious", "true", "old", "new", "tall",
    },
    "number": {
        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve",
    },
    "person": {
        "boy", "girl", "man", "friend", "student", "driver", "farmer", "worker",
        "doctor", "nurse", "queen", "child", "people", "aunt", "Mr",
    },
    "time": {
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
        "sunday", "week", "day", "night", "time", "month", "year", "birthday",
        "o'clock",
    },
}


def _pick(key: str, options: list[str]) -> str:
    return options[hash(key) % len(options)]


def _category(low: str) -> str:
    for cat, words in CATEGORY_WORDS.items():
        if low in words:
            return cat
    if low.endswith("ing"):
        return "verb"
    if low.endswith(("ed", "es")):
        return "verb"
    return "default"


def example_sentence(english: str, chinese: str) -> str:
    head = clean_headword(english)
    low = head.lower()

    for phrase, sent in PHRASE_EXAMPLES.items():
        if low == phrase.lower():
            return sent

    if low in WORD_EXAMPLES:
        return WORD_EXAMPLES[low]

    if low == "i":
        return "I am a student."
    if low in ("we", "they", "he", "she", "it"):
        return _pick(low, [f"{head.capitalize()} is my friend.", f"{head.capitalize()} likes music."])
    if low in ("my", "your", "our", "his", "her"):
        return _pick(low, [f"This is {low} book.", f"{head.capitalize()} bag is blue."])

    if " " in head:
        return _pick(
            low,
            [
                f"Say it with me: “{head}”.",
                f"We often use “{head}” in class.",
                f"Can you make a sentence with “{head}”?",
            ],
        )

    cat = _category(low)
    templates = TEMPLATES.get(cat, TEMPLATES["default"])
    line = _pick(low, templates).format(w=head)
    return line
