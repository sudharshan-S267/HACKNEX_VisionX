import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_query(q):
    data = json.dumps({"query": q}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/query",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    queries = [
        ("Find cars", "car", None),
        ("Find people", "person", None),
        ("Find trucks", "truck", None),
        ("Find buses", "bus", None),
        ("Find motorcycles", "motorcycle", None),
        ("Find bicycles", "bicycle", None),
        ("Find red cars", "car", "red"),
        ("Find red people", "person", "red"),
        ("Find helicopters", "helicopter", None),
        ("blue bus", "bus", "blue"),
        ("blue person", "person", "blue"),
        ("blue car", "car", "blue"),
        ("LADY", "person", None),
        ("WHERE IS THE LADY", "person", None),
        ("BAG", "bag", None),
        ("helicopter", "helicopter", None),
        ("XYZABC", "unknown", None),
    ]

    all_passed = True

    for query_text, expected_class, expected_color in queries:
        res = run_query(query_text)
        matches = res.get("matches", [])
        answer = res.get("answer", "")
        
        types = set(m.get("object_type") for m in matches)
        colors = set(m.get("color") for m in matches)
        print(f"Query: '{query_text:18}' | Count: {len(matches):2} | Object types: {types} | Colors: {colors}")
        
        # Verify strict exclusivity
        if expected_class in ["helicopter", "unknown"]:
            if len(matches) != 0:
                print(f"  [ERROR] Expected 0 matches for '{query_text}', got {len(matches)}!")
                all_passed = False
        elif expected_class == "bag":
            for m in matches:
                if m.get("object_type") not in ["backpack", "handbag", "suitcase"]:
                    print(f"  [ERROR] Unwanted object_type '{m.get('object_type')}' in results for '{query_text}'!")
                    all_passed = False
        else:
            for m in matches:
                if m.get("object_type") != expected_class:
                    print(f"  [ERROR] Unwanted object_type '{m.get('object_type')}' in results for '{query_text}'!")
                    all_passed = False
                if expected_color and (m.get("color") or "").lower() != expected_color:
                    print(f"  [ERROR] Unwanted color '{m.get('color')}' in results for '{query_text}'!")
                    all_passed = False

    if all_passed:
        print(f"\nALL {len(queries)} STRICT OBJECT & COLOR FILTERING CHECKS PASSED PERFECTLY!")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
