from .util import clean_headword


def example_sentence(english: str, chinese: str) -> str:
    head = clean_headword(english)
    low = head.lower()

    if " " in head:
        return f"Let's practice: {head}."

    verbs = {
        "go", "run", "eat", "play", "read", "swim", "jump", "sit", "stand",
        "look", "see", "say", "tell", "want", "like", "help", "make", "put",
        "open", "stop", "wait", "move", "touch", "know", "live", "wear",
        "sing", "dance", "draw", "kick",
    }
    if low in verbs or low.endswith(("ing", "ed")):
        return f"I can {low}."
    if low in ("I", "you", "we", "they", "he", "she", "it", "my", "your", "our", "his", "her"):
        return f"{head.capitalize()} is here."
    if low in ("red", "green", "blue", "big", "small", "happy", "sad", "tired", "hungry", "good"):
        return f"It is {low}."
    if low in ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"):
        return f"I have {low} apples."
    return f"I like the {low}."
