import random

# Dialogues when the bot deals damage to the player
DAMAGE_DIALOGUES = [
    "Ratio",
    "Skill issue",
    "Got some test cases",
    "Yessir",
    "I'm solving this problem faster than you!",
    "Making progress here!",
    "Getting closer to the solution!",
    "Watch out, I'm on fire!",
]

# Dialogues when the bot uses an ability
ABILITY_USE_DIALOGUES = [
    "Here's a gift!",
    "Eat this",
    "I think you might enjoy this",
    "Surprise!",
    "Special delivery!",
    "Watch this",
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
    "Hello {}! Ready to code? I won't go easy on you!",
    "Hey {}! Let's see what you've got!",
    "Greetings {}! Hope you're ready for a challenge!",
    "Welcome {}! Let's have a great practice match!",
]

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

# Response to player chat (LLM replacement joke)
CHAT_RESPONSE = "Sorry, my creator Bao is so broke he can't put an LLM in me to answer you."

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
    return CHAT_RESPONSE