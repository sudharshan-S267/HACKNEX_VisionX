"""
Central Object Ontology for VisionTrace AI
Single Source of Truth for:
- Supported Model Classes
- Canonical Object Names
- Natural Language Synonyms (e.g., lady -> person, bike -> motorcycle)
- Category Expansions (e.g., bag -> backpack, handbag, suitcase)
- Unsupported Entity Rejection
"""

from typing import Dict, List, Set, Optional, Tuple, Any

# 1. Central Supported Object Classes & Synonyms
OBJECT_ONTOLOGY: Dict[str, Dict[str, Any]] = {
    "person": {
        "canonical": "person",
        "synonyms": [
            "person",
            "people",
            "persons",
            "human",
            "humans",
            "man",
            "men",
            "woman",
            "women",
            "lady",
            "ladies",
            "girl",
            "girls",
            "boy",
            "boys",
            "guy",
            "guys",
            "gentleman",
            "gentlemen",
            "pedestrian",
            "pedestrians",
            "individual",
            "individuals",
            "child",
            "children",
            "someone",
            "anybody",
            "anyone",
            "somebody",
        ],
    },
    "car": {
        "canonical": "car",
        "synonyms": [
            "car",
            "cars",
            "automobile",
            "automobiles",
            "sedan",
            "sedans",
            "suv",
            "suvs",
            "auto",
            "autos",
            "van",
            "vans",
        ],
    },
    "truck": {
        "canonical": "truck",
        "synonyms": [
            "truck",
            "trucks",
            "lorry",
            "lorries",
            "pickup",
            "pickups",
        ],
    },
    "bus": {
        "canonical": "bus",
        "synonyms": [
            "bus",
            "buses",
            "coach",
            "coaches",
        ],
    },
    "motorcycle": {
        "canonical": "motorcycle",
        "synonyms": [
            "motorcycle",
            "motorcycles",
            "motorbike",
            "motorbikes",
            "scooter",
            "scooters",
            "moped",
            "mopeds",
        ],
    },
    "bicycle": {
        "canonical": "bicycle",
        "synonyms": [
            "bicycle",
            "bicycles",
            "cycle",
            "cycles",
            "bike",
            "bikes",
        ],
    },
    "backpack": {
        "canonical": "backpack",
        "synonyms": [
            "backpack",
            "backpacks",
            "rucksack",
            "rucksacks",
            "knapsack",
            "knapsacks",
            "schoolbag",
            "schoolbags",
        ],
    },
    "handbag": {
        "canonical": "handbag",
        "synonyms": [
            "handbag",
            "handbags",
            "purse",
            "purses",
            "tote",
            "totes",
        ],
    },
    "suitcase": {
        "canonical": "suitcase",
        "synonyms": [
            "suitcase",
            "suitcases",
            "luggage",
            "baggage",
            "briefcase",
            "briefcases",
        ],
    },
    "bottle": {
        "canonical": "bottle",
        "synonyms": [
            "bottle",
            "bottles",
            "flask",
            "flasks",
        ],
    },
    "dog": {
        "canonical": "dog",
        "synonyms": [
            "dog",
            "dogs",
            "puppy",
            "puppies",
            "canine",
            "canines",
        ],
    },
    "cat": {
        "canonical": "cat",
        "synonyms": [
            "cat",
            "cats",
            "kitten",
            "kittens",
            "feline",
            "felines",
        ],
    },
}

# 2. Multi-Class Category Groupings
CATEGORY_ONTOLOGY: Dict[str, List[str]] = {
    "bag": ["backpack", "handbag", "suitcase"],
    "bags": ["backpack", "handbag", "suitcase"],
    "luggage": ["suitcase", "backpack", "handbag"],
    "vehicle": ["car", "truck", "bus", "motorcycle", "bicycle"],
    "vehicles": ["car", "truck", "bus", "motorcycle", "bicycle"],
    "animal": ["dog", "cat"],
    "animals": ["dog", "cat"],
    "pet": ["dog", "cat"],
    "pets": ["dog", "cat"],
}

# 3. Known Unsupported Entities (to provide helpful rejection instead of false searches)
UNSUPPORTED_ENTITIES: Dict[str, str] = {
    "helicopter": "Helicopter",
    "helicopters": "Helicopter",
    "chopper": "Helicopter",
    "choppers": "Helicopter",
    "airplane": "Airplane",
    "airplanes": "Airplane",
    "plane": "Airplane",
    "planes": "Airplane",
    "aircraft": "Aircraft",
    "drone": "Drone",
    "drones": "Drone",
    "elephant": "Elephant",
    "elephants": "Elephant",
    "bear": "Bear",
    "bears": "Bear",
    "tiger": "Tiger",
    "tigers": "Tiger",
    "lion": "Lion",
    "lions": "Lion",
    "horse": "Horse",
    "horses": "Horse",
    "helmet": "Helmet",
    "helmets": "Helmet",
    "gun": "Firearm",
    "guns": "Firearm",
    "weapon": "Weapon",
    "weapons": "Weapon",
    "knife": "Weapon",
    "knives": "Weapon",
    "boat": "Boat",
    "boats": "Boat",
    "ship": "Ship",
    "ships": "Ship",
}

# 4. Explicit Broad Query Phrases
ALL_OBJECT_PHRASES: Set[str] = {
    "show all detected objects",
    "show all objects",
    "show all events",
    "find all objects",
    "find all events",
    "show everything",
    "all events",
    "all objects",
    "everything",
    "list all detections",
    "list all events",
}

# Precompute Fast Reverse Lookup
SYNONYM_TO_CANONICAL: Dict[str, str] = {}
for canonical, data in OBJECT_ONTOLOGY.items():
    for syn in data["synonyms"]:
        SYNONYM_TO_CANONICAL[syn.lower()] = canonical

ALL_SUPPORTED_CLASSES: Set[str] = set(OBJECT_ONTOLOGY.keys())


def normalize_entity_token(token: str) -> Optional[str]:
    """Resolve single token to canonical object name if known."""
    tok = token.lower().strip()
    return SYNONYM_TO_CANONICAL.get(tok)


def get_supported_classes() -> Set[str]:
    """Returns the set of all canonical classes recognized by the system."""
    return ALL_SUPPORTED_CLASSES


def is_all_objects_query(query: str) -> bool:
    """Check if query is asking for all detected objects/events."""
    import re
    q = query.lower().strip()
    if q in ALL_OBJECT_PHRASES:
        return True
    # Match phrases strictly referring to all/everything without a specific object class:
    # e.g.: "show all objects", "list everything", "show all detected events"
    if re.search(r"^(?:show|find|list|get|display)\s+(?:all|everything)(?:\s+(?:detected\s+)?(?:objects|events|detections|results))?$", q):
        return True
    if re.search(r"^(?:all|everything)(?:\s+(?:detected\s+)?(?:objects|events|detections))?$", q):
        return True
    return False



def find_unsupported_entity(query: str) -> Optional[Tuple[str, str]]:
    """
    Check if query mentions an unsupported entity.
    Returns (raw_word, display_name) or None.
    """
    import re
    q = query.lower()
    for raw_word, display_name in UNSUPPORTED_ENTITIES.items():
        pattern = rf"\b{re.escape(raw_word)}\b"
        if re.search(pattern, q):
            return (raw_word, display_name)
    return None


def resolve_query_entities(query: str) -> Tuple[List[str], List[str]]:
    """
    Extract canonical object classes and matched entity tokens from query.
    Handles:
    - Multi-class category groupings (e.g. 'bag' -> ['backpack', 'handbag', 'suitcase'], 'vehicle' -> ['car', 'truck', 'bus', 'motorcycle', 'bicycle'])
    - Multi-object queries (e.g. 'people and cars' -> ['person', 'car'])
    - Individual synonyms (e.g. 'lady' -> 'person', 'men' -> 'person', 'bike' -> 'bicycle')
    Returns:
    (canonical_classes_list, matched_entities_list)
    """
    import re
    q = query.lower().strip()
    matched_classes: Set[str] = set()
    matched_entities: List[str] = []

    # 1. Check category groupings first (e.g. bag, vehicle, animal)
    for cat_name, mapped_classes in CATEGORY_ONTOLOGY.items():
        pattern = rf"\b{re.escape(cat_name)}\b"
        if re.search(pattern, q):
            matched_classes.update(mapped_classes)
            matched_entities.append(cat_name)

    # 2. Check individual synonyms and canonical names
    # Sort synonyms by length descending to match phrases like 'pickup truck' before 'truck'
    all_syns = sorted(SYNONYM_TO_CANONICAL.keys(), key=lambda s: len(s), reverse=True)
    for syn in all_syns:
        pattern = rf"\b{re.escape(syn)}\b"
        if re.search(pattern, q):
            canonical = SYNONYM_TO_CANONICAL[syn]
            matched_classes.add(canonical)
            if syn not in matched_entities:
                matched_entities.append(syn)

    return sorted(list(matched_classes)), matched_entities

