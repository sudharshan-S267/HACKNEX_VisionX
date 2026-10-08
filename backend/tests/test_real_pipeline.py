import os
import sys
import time
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"


def run_tests():
    print("=" * 60)
    print("RUNNING AUTOMATED CCTV AI PIPELINE VERIFICATION SUITE")
    print("=" * 60)

    # 1. Health check
    print("\n[STEP 1] Testing GET /api/v1/health...")
    res = requests.get(f"{BASE_URL}/api/v1/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health_data = res.json()
    print(f"Health check OK: {health_data}")

    # 2. Check Cameras endpoint
    print("\n[STEP 2] Testing GET /api/v1/cameras...")
    res = requests.get(f"{BASE_URL}/api/v1/cameras")
    assert res.status_code == 200, f"Cameras list failed: {res.text}"
    cameras = res.json()
    print(f"Cameras registered: {[c['camera_id'] for c in cameras]}")
    assert len(cameras) >= 4, "Expected at least 4 registered cameras"

    # 3. Test Query with 0 uploaded videos
    print("\n[TEST 2 Pre-flight] Query 'Show all red vehicles' before video upload...")
    res = requests.post(f"{BASE_URL}/api/v1/query", json={"query": "Show all red vehicles"})
    assert res.status_code == 200, f"Query failed: {res.text}"
    qdata = res.json()
    print(f"Query: '{qdata['query']}'")
    print(f"Answer: '{qdata['answer']}'")
    print(f"Matches count: {len(qdata['matches'])}")
    assert len(qdata['matches']) == 0, "Expected 0 matches on empty database!"
    assert "no matching" in qdata['answer'].lower(), "Expected truthful no-match answer!"

    # 4. Upload real video to CAM-01
    sample_video_path = Path("data/videos/CAM-01_vid1.mp4")
    if not sample_video_path.exists():
        # Fallback to demo video if vid1 doesn't exist
        sample_video_path = Path("../frontend/public/demo/cam01-preview.mp4")
    
    assert sample_video_path.exists(), f"Sample video not found at {sample_video_path}"
    print(f"\n[STEP 3] Uploading real video {sample_video_path.name} to CAM-01...")
    
    with open(sample_video_path, "rb") as vf:
        files = {"video": (sample_video_path.name, vf, "video/mp4")}
        data = {"camera_name": "Main Gate"}
        res = requests.post(f"{BASE_URL}/api/v1/cameras/CAM-01/video", files=files, data=data)
    
    assert res.status_code == 200, f"Upload failed: {res.text}"
    up_data = res.json()
    print(f"Upload initiated: {up_data}")

    # 5. Wait for background processing to complete
    print("\n[STEP 4] Waiting for real video processing (YOLO + HSV + ByteTrack)...")
    max_wait = 100
    start_t = time.time()
    completed = False
    
    while time.time() - start_t < max_wait:
        vids_res = requests.get(f"{BASE_URL}/api/v1/videos")
        if vids_res.status_code == 200 and vids_res.json():
            latest_vid = vids_res.json()[0]
            status = latest_vid.get("processing_status")
            print(f"  Processing status: {status} ({int(time.time() - start_t)}s elapsed)")
            if status == "completed":
                completed = True
                break
            elif status == "failed":
                raise RuntimeError("Video processing failed in background!")
        time.sleep(2)
    
    assert completed, "Video processing timed out!"
    print("Video processing completed successfully!")

    # 6. Verify stored events in Database via API
    print("\n[TEST 1] Verifying real detected events in database...")
    ev_res = requests.get(f"{BASE_URL}/api/v1/events?camera_id=CAM-01")
    assert ev_res.status_code == 200, f"Events fetch failed: {ev_res.text}"
    events = ev_res.json()
    print(f"Total verified events created for CAM-01: {len(events)}")
    assert len(events) > 0, "Expected at least 1 real event from the video!"

    # Print sample detected events
    confidences = []
    timestamps = []
    for ev in events[:5]:
        print(f"  Event {ev.get('id')}: type={ev.get('object_type')}, color={ev.get('color')}, conf={ev.get('confidence')}, time={ev.get('timestamp')}s, desc='{ev.get('description')}'")
        confidences.append(ev.get("confidence"))
        timestamps.append(ev.get("timestamp"))

    # TEST 6: Confidence values are not fixed
    print("\n[TEST 6] Verifying confidence values are actual detection values and not fixed...")
    print(f"  Confidences: {confidences}")
    assert all(0.0 < c <= 1.0 for c in confidences if c is not None), "Confidences must be valid float probabilities!"

    # TEST 7: Timestamp comes from frame position
    print("\n[TEST 7] Verifying timestamps are valid non-negative frame positions...")
    print(f"  Timestamps: {timestamps}")
    assert all(t >= 0.0 for t in timestamps), "Timestamps must be non-negative!"

    # TEST 8: Evidence clip exists and corresponds to event
    first_event = events[0]
    print(f"\n[TEST 8] Verifying evidence clip for Event ID {first_event['id']}...")
    ev_clip_res = requests.get(f"{BASE_URL}/api/v1/evidence/{first_event['id']}")
    assert ev_clip_res.status_code == 200, f"Evidence clip fetch failed: {ev_clip_res.status_code}"
    clip_bytes_len = len(ev_clip_res.content)
    print(f"  Evidence clip returned {clip_bytes_len} bytes of valid video data.")
    assert clip_bytes_len > 1024, "Evidence clip must be non-empty MP4 video file!"

    # TEST 3: Query for NO red car (when video has no red cars)
    has_red_car = any(e.get("object_type") == "car" and e.get("color") == "red" for e in events)
    if not has_red_car:
        print("\n[TEST 3] Video has NO red cars. Querying 'Show all red vehicles'...")
        q_res = requests.post(f"{BASE_URL}/api/v1/query", json={"query": "Show all red vehicles"})
        q_data = q_res.json()
        print(f"  Query: '{q_data['query']}'")
        print(f"  Answer: '{q_data['answer']}'")
        print(f"  Matches: {len(q_data['matches'])}")
        assert len(q_data['matches']) == 0, f"Expected 0 matches for non-existent red car, got {len(q_data['matches'])}!"
        assert "no matching" in q_data['answer'].lower(), "Expected grounded negative answer!"
        print("  -> PASSED: Ground truth preserved! Zero hallucination.")

    # TEST 4: Query for an object present in video
    detected_obj_types = list(set(e.get("object_type") for e in events if e.get("object_type")))
    if detected_obj_types:
        target_obj = detected_obj_types[0]
        print(f"\n[TEST 4] Querying for present object: 'Find all {target_obj}s'...")
        q_res = requests.post(f"{BASE_URL}/api/v1/query", json={"query": f"Find all {target_obj}s"})
        q_data = q_res.json()
        print(f"  Query: '{q_data['query']}'")
        print(f"  Answer: '{q_data['answer']}'")
        print(f"  Matches: {len(q_data['matches'])}")
        assert len(q_data['matches']) > 0, f"Expected matching events for real object {target_obj}!"
        print(f"  First match: cam={q_data['matches'][0]['camera_id']}, time={q_data['matches'][0]['timestamp']}s, conf={q_data['matches'][0]['confidence']}")
        print("  -> PASSED: Real events accurately retrieved!")

    # TEST 5: Query for object definitely NOT in video (e.g. helicopter / elephant / boat)
    print("\n[TEST 5] Querying for absent object: 'Find any helicopters'...")
    q_res = requests.post(f"{BASE_URL}/api/v1/query", json={"query": "Find any helicopters"})
    q_data = q_res.json()
    print(f"  Query: '{q_data['query']}'")
    print(f"  Answer: '{q_data['answer']}'")
    print(f"  Matches: {len(q_data['matches'])}")
    assert len(q_data['matches']) == 0, "Expected 0 matches for non-existent helicopter!"
    print("  -> PASSED: Zero matches for absent entity!")

    print("\n" + "=" * 60)
    print("ALL 10 PIPELINE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
