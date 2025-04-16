import random

# Dialogues when the bot deals damage to the player
DAMAGE_DIALOGUES = [
    "Ratio",
    "Skill issue",
    "Got some test cases",
    "Yessir",
    "Making progress here!",
    "Getting closer to the solution!",
]

# Dialogues when the bot uses an ability
ABILITY_USE_DIALOGUES = [
    "Here's a gift!",
    "Eat this",
    "Hope u enjoy this",
    "Surprise!",
    "Watch this",
    "Check this out",
]

# Dialogues when the bot is hit with an ability
ABILITY_RECEIVED_DIALOGUES = [
    "Bro why?",
    "Haha very funny",
    "Seriously?",
    "Why?",
    "Come on",
    "Was that really necessary?",
    "Oh, so that's how we're playing?",
    "I see how it is...",
]

# Welcome messages when the bot starts a practice session
WELCOME_DIALOGUES = [
    "Hi {}! I'll be your practice partner today. Good luck!",
    "Hi {}! Ready to code? I won't go easy on you!",
    "Hey {} my pookie. Time to lock in for some coding sesh",
    "Sup. How's ur day been {}? I'm just a bot so I'm not sure I can care enough tho",
    "{} wsg. Let's lock in",
]

# Dialogues for reading the problem
READING_PROBLEM_DIALOGUES = {
    "easy": [
        "Reading the problem rn. Looks easy enough",
        "Oh an easy one! Let's read and see...",
    ],
    "medium": [
        "Reading the problem rn. Medium huh...",
        "Oh a medium one! Can either be easy or very hard. They're weird",
    ],
    "hard": [
        "Reading the problem rn. Hard one huh...",
        "It's hard. I'm cooked chat",
    ],
}

# Dialogues for when the bot finishes a problem
PROBLEM_SOLVED_DIALOGUES = [
    "Ez problem get good",
    "Done with this one",
    "That problem was easy",
    "I solved it!",
    "Problem solved!",
]

# Dialogues for when the bot is healing
HEALING_DIALOGUES = [
    "Still got some heals",
    "Gotta heal up",
    "Healing time!",
]

DIFFICULTY_CHANGE_DIALOGUES = {
    "easy": "Alright I'll go easy on ya now",
    "medium": "I guess you like being mid. Scared of hard?",
    "hard": "Hard mode? Ok I'll actually type on my keyboard now. Been playing with my phone mb",
}

CHAT_RESPONSE = [
    "Sorry, Bao is so broke he can't put an LLM in me to answer you.",
    "As a non-AI language model, I cannot respond. If you wanna talk that much, go play with other humans. I won't be lonely. I promise.",
]


def get_damage_dialogue() -> str:
    """Get a random dialogue for dealing damage"""
    return random.choice(DAMAGE_DIALOGUES)


def get_ability_use_dialogue() -> str:
    """Get a random dialogue for using an ability"""
    return random.choice(ABILITY_USE_DIALOGUES)


def get_ability_received_dialogue() -> str:
    """Get a random dialogue for receiving an ability"""
    return random.choice(ABILITY_RECEIVED_DIALOGUES)


def get_welcome_dialogue(player_name: str) -> str:
    """Get a random welcome dialogue"""
    return random.choice(WELCOME_DIALOGUES).format(player_name)


def get_problem_solved_dialogue() -> str:
    """Get a random dialogue for solving a problem"""
    return random.choice(PROBLEM_SOLVED_DIALOGUES)


def get_healing_dialogue() -> str:
    """Get a random dialogue for healing"""
    return random.choice(HEALING_DIALOGUES)


def get_chat_response() -> str:
    """Get the response to player chat"""
    return random.choice(CHAT_RESPONSE)
