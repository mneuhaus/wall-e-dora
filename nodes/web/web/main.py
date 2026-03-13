"""Main module for the Web Node.

Sets up an aiohttp web server with WebSocket support to serve the React frontend
and handle real-time communication with clients and other Dora nodes.
Manages gamepad profiles and orchestrates data flow between the UI and backend nodes.
"""

import asyncio
import math
import os
import random
import threading
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import aiohttp
import aiohttp_debugtoolbar
import json
import jinja2
import logging
import pyarrow as pa
import time
from aiohttp import web
from dora import Node
from handlers.gamepad_profiles import (
    GamepadProfileManager,
    handle_save_gamepad_profile,
    handle_get_gamepad_profile,
    handle_check_gamepad_profile,
    handle_delete_gamepad_profile,
    handle_list_gamepad_profiles,
    emit_profiles_list
)

logging.basicConfig(level=logging.INFO)

try:
    import cv2
    import numpy as np
except Exception as error:  # pragma: no cover - runtime environment dependent
    cv2 = None
    np = None
    FACE_TRACKING_IMPORT_ERROR = str(error)
else:
    FACE_TRACKING_IMPORT_ERROR = ''

CAMERA_TTL_SECONDS = 0.25
CAMERA_FETCH_TIMEOUT_SECONDS = 2.5
GO2RTC_BASE_URL = os.environ.get('GO2RTC_BASE_URL', 'http://127.0.0.1:1984')
GO2RTC_STREAM_SRC = os.environ.get('GO2RTC_STREAM_SRC', 'walle_camera')
REPO_ROOT = Path(__file__).resolve().parents[3]
PHOTO_GALLERY_DIR = REPO_ROOT / 'out' / 'photos'
FACE_TRACKING_MODEL_DIR = REPO_ROOT / 'out' / 'models'
FACE_TRACKING_MODEL_PATH = Path(
    os.environ.get(
        'FACE_TRACKING_MODEL_PATH',
        str(FACE_TRACKING_MODEL_DIR / 'face_detection_yunet_2023mar.onnx'),
    )
)
FACE_TRACKING_MODEL_URL = os.environ.get(
    'FACE_TRACKING_MODEL_URL',
    'https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx',
)
FACE_TRACKING_SERVO_ID = int(os.environ.get('FACE_TRACKING_SERVO_ID', '14'))
FACE_TRACKING_CENTER_POSITION = int(os.environ.get('FACE_TRACKING_CENTER_POSITION', '500'))
FACE_TRACKING_MIN_POSITION = int(os.environ.get('FACE_TRACKING_MIN_POSITION', '220'))
FACE_TRACKING_MAX_POSITION = int(os.environ.get('FACE_TRACKING_MAX_POSITION', '780'))
FACE_TRACKING_DETECTION_INTERVAL_SECONDS = 0.18
FACE_TRACKING_COMMAND_INTERVAL_SECONDS = 0.12
FACE_TRACKING_RETURN_DELAY_SECONDS = 1.0
FACE_TRACKING_MAX_STEP = 30
FACE_TRACKING_SEARCH_STEP = 28
FACE_TRACKING_RETURN_STEP = 12
FACE_TRACKING_MOVE_TOLERANCE = 4
FACE_TRACKING_DEADZONE = 0.06
FACE_TRACKING_FACE_SWITCH_INTERVAL_SECONDS = 1.1
FACE_TRACKING_FACE_RANDOM_SWITCH_CHANCE = 0.24
FACE_TRACKING_LOCK_RETENTION_SECONDS = 0.45
FACE_TRACKING_PREDICTION_SECONDS = 0.22
FACE_TRACKING_SMOOTHING_ALPHA = 0.46
FACE_TRACKING_SEARCH_DELAY_SECONDS = 0.7
FACE_TRACKING_SEARCH_INTERVAL_SECONDS = 1.5
camera_snapshot_lock = threading.Lock()
camera_snapshot_bytes = None
camera_snapshot_taken_at = 0.0
face_tracking_state_lock = threading.Lock()
face_tracking_detector = None
face_tracking_enabled = False
face_tracking_supported = cv2 is not None and np is not None
face_tracking_face_detected = False
face_tracking_current_position = FACE_TRACKING_CENTER_POSITION
face_tracking_target_position = FACE_TRACKING_CENTER_POSITION
face_tracking_faces = []
face_tracking_last_detection_at = 0.0
face_tracking_last_face_at = 0.0
face_tracking_last_move_at = 0.0
face_tracking_last_face_switch_at = 0.0
face_tracking_last_search_at = 0.0
face_tracking_search_target_position = FACE_TRACKING_CENTER_POSITION
face_tracking_locked_center_x = 0.5
face_tracking_locked_velocity_x = 0.0
face_tracking_locked_area = 0.0
face_tracking_last_observation_at = 0.0
face_tracking_recenter_pending = False
face_tracking_sequence_active = False
face_tracking_state_signature = None

# Global variables (consider refactoring into a class or context)
global_web_inputs = []  # Queue for events received from WebSocket clients
ws_clients = set()      # Set of active WebSocket client connections
web_loop = None         # asyncio event loop for the web server thread


def clamp_face_tracking_position(position: int) -> int:
    """Clamp a servo target into the safe head-pivot range."""
    return max(FACE_TRACKING_MIN_POSITION, min(FACE_TRACKING_MAX_POSITION, int(position)))


FACE_TRACKING_SEARCH_POSITIONS = (
    clamp_face_tracking_position(FACE_TRACKING_MIN_POSITION + 18),
    clamp_face_tracking_position(FACE_TRACKING_MAX_POSITION - 18),
)


def compute_face_tracking_target(frame_width: int, face_center_x: float) -> int:
    """Map a detected face center to the head pivot position."""
    if frame_width <= 0:
        return FACE_TRACKING_CENTER_POSITION

    normalized_offset = (face_center_x - (frame_width / 2)) / (frame_width / 2)
    if abs(normalized_offset) <= FACE_TRACKING_DEADZONE:
        return FACE_TRACKING_CENTER_POSITION

    active_range = 1.0 - FACE_TRACKING_DEADZONE
    if normalized_offset < 0:
        strength = (abs(normalized_offset) - FACE_TRACKING_DEADZONE) / active_range
        return clamp_face_tracking_position(
            round(FACE_TRACKING_CENTER_POSITION - (FACE_TRACKING_CENTER_POSITION - FACE_TRACKING_MIN_POSITION) * strength)
        )

    strength = (normalized_offset - FACE_TRACKING_DEADZONE) / active_range
    return clamp_face_tracking_position(
        round(FACE_TRACKING_CENTER_POSITION + (FACE_TRACKING_MAX_POSITION - FACE_TRACKING_CENTER_POSITION) * strength)
    )


def compute_next_face_tracking_step(current_position: int, target_position: int, *, max_step: int = FACE_TRACKING_MAX_STEP) -> int:
    """Move smoothly toward a face target without twitching."""
    delta = target_position - current_position
    if abs(delta) <= FACE_TRACKING_MOVE_TOLERANCE:
        return clamp_face_tracking_position(target_position)

    step = round(delta * 0.4)
    if step == 0:
        step = 1 if delta > 0 else -1
    step = max(-max_step, min(max_step, step))
    return clamp_face_tracking_position(current_position + step)


def compute_face_tracking_face_area(face: dict[str, float | bool]) -> float:
    """Return a normalized face box area for candidate scoring."""
    return max(0.0, float(face.get('width', 0.0)) * float(face.get('height', 0.0)))


def select_face_tracking_face(
    detected_faces: list[dict[str, float | bool]],
    reference_center_x: float,
    reference_area: float,
    *,
    now: float,
    last_face_switch_at: float,
) -> tuple[int, float]:
    """Prefer a stable face lock, but occasionally swap between equally good faces."""
    if len(detected_faces) == 1:
        return 0, last_face_switch_at

    ranked_candidates = []
    for index, face in enumerate(detected_faces):
        area = compute_face_tracking_face_area(face)
        center_x = float(face.get('center_x', 0.5))
        score = (
            (float(face.get('score', 0.0)) * 1.8)
            + min(0.28, area * 3.2)
            - (abs(center_x - reference_center_x) * 1.65)
        )
        if reference_area > 0:
            score -= abs(area - reference_area) * 0.55
        ranked_candidates.append((score, index))

    ranked_candidates.sort(reverse=True)
    selected_index = ranked_candidates[0][1]

    if now - last_face_switch_at < FACE_TRACKING_FACE_SWITCH_INTERVAL_SECONDS:
        return selected_index, last_face_switch_at

    top_score = ranked_candidates[0][0]
    switchable_indices = [
        index for score, index in ranked_candidates
        if score >= top_score - 0.16
    ]
    if len(switchable_indices) > 1 and random.random() < FACE_TRACKING_FACE_RANDOM_SWITCH_CHANCE:
        return random.choice(switchable_indices), now

    return selected_index, last_face_switch_at


def blend_face_tracking_observation(
    observed_center_x: float,
    observed_area: float,
    previous_center_x: float,
    previous_velocity_x: float,
    previous_area: float,
    *,
    delta_time: float,
) -> tuple[float, float, float]:
    """Blend the new face observation into a smoother tracked target."""
    clamped_observed_center = max(0.0, min(1.0, observed_center_x))
    if delta_time <= 0:
        return clamped_observed_center, 0.0, observed_area

    observed_velocity_x = (clamped_observed_center - previous_center_x) / max(delta_time, 1e-3)
    blended_velocity_x = (previous_velocity_x * 0.4) + (observed_velocity_x * 0.6)
    predicted_center_x = max(
        0.0,
        min(
            1.0,
            clamped_observed_center + (blended_velocity_x * min(delta_time, FACE_TRACKING_PREDICTION_SECONDS)),
        ),
    )
    smoothed_center_x = (
        (previous_center_x * (1.0 - FACE_TRACKING_SMOOTHING_ALPHA))
        + (predicted_center_x * FACE_TRACKING_SMOOTHING_ALPHA)
    )
    smoothed_area = (previous_area * 0.55) + (observed_area * 0.45)
    return max(0.0, min(1.0, smoothed_center_x)), blended_velocity_x, max(0.0, smoothed_area)


def project_face_tracking_center(center_x: float, velocity_x: float, *, elapsed: float) -> float:
    """Project the current face lock forward briefly between detections."""
    return max(
        0.0,
        min(
            1.0,
            center_x + (velocity_x * min(elapsed, FACE_TRACKING_PREDICTION_SECONDS)),
        ),
    )


def select_next_face_tracking_search_target(current_target_position: int) -> int:
    """Sweep wider left/right while searching instead of hovering near center."""
    left_edge = FACE_TRACKING_SEARCH_POSITIONS[0]
    right_edge = FACE_TRACKING_SEARCH_POSITIONS[1]

    if current_target_position <= FACE_TRACKING_CENTER_POSITION:
        return right_edge

    return left_edge


def ensure_face_tracking_model() -> Path | None:
    """Ensure the YuNet model exists locally."""
    global face_tracking_supported

    if FACE_TRACKING_MODEL_PATH.exists():
        return FACE_TRACKING_MODEL_PATH

    try:
        FACE_TRACKING_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FACE_TRACKING_MODEL_URL, FACE_TRACKING_MODEL_PATH)
        logging.info('Downloaded YuNet face model to %s', FACE_TRACKING_MODEL_PATH)
        return FACE_TRACKING_MODEL_PATH
    except Exception as error:
        logging.error('Failed to download YuNet face model: %s', error)
        face_tracking_supported = False
        return None


def get_face_tracking_detector():
    """Load the OpenCV YuNet detector lazily."""
    global face_tracking_detector, face_tracking_supported

    if not face_tracking_supported:
        return None

    if face_tracking_detector is not None:
        return face_tracking_detector

    model_path = ensure_face_tracking_model()
    if model_path is None:
        return None

    try:
        detector = cv2.FaceDetectorYN_create(
            str(model_path),
            '',
            (320, 320),
            0.7,
            0.3,
            5000,
        )
    except Exception as error:
        logging.error('Failed to create YuNet face detector: %s', error)
        face_tracking_supported = False
        return None

    face_tracking_detector = detector
    return face_tracking_detector


def serialize_face_tracking_state() -> dict:
    """Return the face tracking state for API/UI consumers."""
    with face_tracking_state_lock:
        return {
            'enabled': face_tracking_enabled,
            'supported': face_tracking_supported,
            'face_detected': face_tracking_face_detected,
            'current_position': face_tracking_current_position,
            'target_position': face_tracking_target_position,
            'faces': list(face_tracking_faces),
            'sequence_active': face_tracking_sequence_active,
            'error': None if face_tracking_supported else (FACE_TRACKING_IMPORT_ERROR or 'OpenCV unavailable'),
        }


def broadcast_face_tracking_state() -> None:
    """Broadcast face tracking state updates to all connected WebSocket clients."""
    global face_tracking_state_signature

    state = serialize_face_tracking_state()
    signature = json.dumps(state, sort_keys=True)
    if signature == face_tracking_state_signature:
        return

    face_tracking_state_signature = signature
    if web_loop is None:
        return

    payload = json.dumps({
        'id': 'face_tracking_state',
        'value': state,
        'type': 'EVENT',
    }).encode('utf-8')
    asyncio.run_coroutine_threadsafe(broadcast_bytes(payload), web_loop)


def detect_primary_face(frame_bytes: bytes) -> tuple[float | None, int | None, list[dict[str, float | bool]]]:
    """Return the primary face center and normalized face boxes."""
    detector = get_face_tracking_detector()
    if detector is None or np is None:
        return None, None, []

    frame_buffer = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(frame_buffer, cv2.IMREAD_COLOR)
    if frame is None:
        return None, None, []

    frame_height = int(frame.shape[0])
    frame_width = int(frame.shape[1])
    detector.setInputSize((frame_width, frame_height))

    try:
        _, faces = detector.detect(frame)
    except Exception as error:
        logging.debug('YuNet detection failed: %s', error)
        return None, frame_width, []

    if faces is None or len(faces) == 0:
        return None, frame_width, []

    primary_face = max(faces, key=lambda face: float(face[14]) * float(face[2]) * float(face[3]))
    px, py, pwidth, pheight = [float(value) for value in primary_face[:4]]

    normalized_faces = []
    for face in faces:
        x, y, width, height = [float(value) for value in face[:4]]
        normalized_faces.append({
            'x': x / frame_width,
            'y': y / frame_height,
            'width': width / frame_width,
            'height': height / frame_height,
            'center_x': (x + (width / 2)) / frame_width,
            'center_y': (y + (height / 2)) / frame_height,
            'score': float(face[14]),
            'primary': x == px and y == py and width == pwidth and height == pheight,
        })

    return float(px + (pwidth / 2)), frame_width, normalized_faces


def annotate_face_tracking_frame(frame_bytes: bytes) -> bytes:
    """Draw detected face boxes directly onto a JPEG frame."""
    if not frame_bytes or cv2 is None or np is None:
        return frame_bytes

    with face_tracking_state_lock:
        faces = list(face_tracking_faces)

    if not faces:
        return frame_bytes

    frame_buffer = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(frame_buffer, cv2.IMREAD_COLOR)
    if frame is None:
        return frame_bytes

    frame_height, frame_width = frame.shape[:2]
    for face in faces:
        x = max(0, min(frame_width - 1, int(float(face.get('x', 0)) * frame_width)))
        y = max(0, min(frame_height - 1, int(float(face.get('y', 0)) * frame_height)))
        width = max(1, int(float(face.get('width', 0)) * frame_width))
        height = max(1, int(float(face.get('height', 0)) * frame_height))
        color = (0, 210, 255) if face.get('primary') else (255, 255, 255)
        cv2.rectangle(frame, (x, y), (min(frame_width - 1, x + width), min(frame_height - 1, y + height)), color, 2)

    success, encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 84])
    if not success:
        return frame_bytes
    return encoded.tobytes()


def update_face_tracking_head_position(payload: list | dict | None) -> None:
    """Keep the tracker in sync with the actual head pivot position."""
    global face_tracking_current_position

    if payload is None:
        return

    if isinstance(payload, dict):
        items = [payload]
    elif isinstance(payload, list):
        items = payload
    else:
        return

    for item in items:
        if not isinstance(item, dict) or item.get('id') != FACE_TRACKING_SERVO_ID:
            continue
        position = item.get('position')
        if position is None:
            continue
        with face_tracking_state_lock:
            try:
                face_tracking_current_position = clamp_face_tracking_position(int(position))
            except (TypeError, ValueError):
                return
        return


def update_face_tracking_sequence_state(payload: list | dict | None) -> None:
    """Pause face tracking while a scene/action sequence is running."""
    global face_tracking_sequence_active, face_tracking_face_detected, face_tracking_faces
    global face_tracking_last_search_at, face_tracking_search_target_position
    global face_tracking_locked_center_x, face_tracking_locked_velocity_x
    global face_tracking_locked_area, face_tracking_last_observation_at

    if payload is None:
        return

    if isinstance(payload, dict):
        items = [payload]
    elif isinstance(payload, list):
        items = payload
    else:
        return

    changed = False
    with face_tracking_state_lock:
        current_value = face_tracking_sequence_active
        next_value = current_value
        for item in items:
            if isinstance(item, dict) and 'active' in item:
                next_value = bool(item.get('active'))
        if next_value != current_value:
            face_tracking_sequence_active = next_value
            face_tracking_face_detected = False
            face_tracking_faces = []
            face_tracking_last_search_at = 0.0
            face_tracking_search_target_position = FACE_TRACKING_CENTER_POSITION
            face_tracking_locked_center_x = 0.5
            face_tracking_locked_velocity_x = 0.0
            face_tracking_locked_area = 0.0
            face_tracking_last_observation_at = 0.0
            changed = True

    if changed:
        broadcast_face_tracking_state()


def process_face_tracking(node: Node) -> None:
    """Run one face tracking update and emit head-pivot commands if needed."""
    global face_tracking_last_detection_at, face_tracking_last_face_at
    global face_tracking_face_detected, face_tracking_target_position
    global face_tracking_current_position, face_tracking_last_move_at
    global face_tracking_recenter_pending, face_tracking_faces
    global face_tracking_last_face_switch_at, face_tracking_last_search_at
    global face_tracking_search_target_position
    global face_tracking_locked_center_x, face_tracking_locked_velocity_x
    global face_tracking_locked_area, face_tracking_last_observation_at

    if web_loop is None or not face_tracking_supported:
        return

    now = time.monotonic()
    state_changed = False

    with face_tracking_state_lock:
        enabled = face_tracking_enabled
        paused_for_sequence = face_tracking_sequence_active
        last_detection_at = face_tracking_last_detection_at
        last_face_at = face_tracking_last_face_at
        last_move_at = face_tracking_last_move_at
        current_position = face_tracking_current_position
        target_position = face_tracking_target_position
        last_face_switch_at = face_tracking_last_face_switch_at
        last_search_at = face_tracking_last_search_at
        search_target_position = face_tracking_search_target_position
        recenter_pending = face_tracking_recenter_pending
        face_detected = face_tracking_face_detected
        locked_center_x = face_tracking_locked_center_x
        locked_velocity_x = face_tracking_locked_velocity_x
        locked_area = face_tracking_locked_area
        last_observation_at = face_tracking_last_observation_at

    if enabled and not paused_for_sequence and face_detected and last_observation_at > 0:
        time_since_observation = now - last_observation_at
        if 0 < time_since_observation <= FACE_TRACKING_LOCK_RETENTION_SECONDS:
            projected_center_x = project_face_tracking_center(
                locked_center_x,
                locked_velocity_x,
                elapsed=time_since_observation,
            )
            projected_target = compute_face_tracking_target(1000, projected_center_x * 1000.0)
            if projected_target != target_position:
                with face_tracking_state_lock:
                    face_tracking_target_position = projected_target
                    target_position = projected_target
                state_changed = True

    if enabled and not paused_for_sequence and now - last_detection_at >= FACE_TRACKING_DETECTION_INTERVAL_SECONDS:
        frame = None
        try:
            frame = asyncio.run_coroutine_threadsafe(
                fetch_go2rtc_frame(force_refresh=True),
                web_loop,
            ).result(timeout=0.75)
        except Exception as error:
            logging.debug('Face tracking frame fetch skipped: %s', error)

        detected = False
        next_target = target_position
        detected_faces = []
        if frame:
            _, frame_width, detected_faces = detect_primary_face(frame)
            if detected_faces and frame_width is not None:
                selected_index, last_face_switch_at = select_face_tracking_face(
                    detected_faces,
                    locked_center_x,
                    locked_area,
                    now=now,
                    last_face_switch_at=last_face_switch_at,
                )
                selected_face = detected_faces[selected_index]
                selected_center_x = float(selected_face['center_x'])
                selected_area = compute_face_tracking_face_area(selected_face)
                observation_delta = now - last_observation_at if last_observation_at > 0 else 0.0
                locked_center_x, locked_velocity_x, locked_area = blend_face_tracking_observation(
                    selected_center_x,
                    selected_area,
                    locked_center_x,
                    locked_velocity_x,
                    locked_area,
                    delta_time=observation_delta,
                )
                next_target = compute_face_tracking_target(frame_width, locked_center_x * frame_width)

                for index, face in enumerate(detected_faces):
                    face['primary'] = index == selected_index
                detected = True

        with face_tracking_state_lock:
            face_tracking_last_detection_at = now
            face_tracking_faces = detected_faces
            if detected:
                face_tracking_last_face_at = now
                face_tracking_face_detected = True
                face_tracking_target_position = next_target
                face_tracking_last_face_switch_at = last_face_switch_at
                face_tracking_search_target_position = next_target
                face_tracking_locked_center_x = locked_center_x
                face_tracking_locked_velocity_x = locked_velocity_x
                face_tracking_locked_area = locked_area
                face_tracking_last_observation_at = now
            elif face_tracking_face_detected:
                face_tracking_face_detected = False
                face_tracking_locked_velocity_x = 0.0
            state_changed = True
            last_face_at = face_tracking_last_face_at
            current_position = face_tracking_current_position
            target_position = face_tracking_target_position
            last_move_at = face_tracking_last_move_at
            search_target_position = face_tracking_search_target_position
            last_search_at = face_tracking_last_search_at
            recenter_pending = face_tracking_recenter_pending
            face_detected = face_tracking_face_detected
            locked_center_x = face_tracking_locked_center_x
            locked_velocity_x = face_tracking_locked_velocity_x
            locked_area = face_tracking_locked_area
            last_observation_at = face_tracking_last_observation_at

    if now - last_move_at < FACE_TRACKING_COMMAND_INTERVAL_SECONDS:
        if state_changed:
            broadcast_face_tracking_state()
        return

    next_position = None
    if enabled and not paused_for_sequence:
        if face_detected:
            next_position = compute_next_face_tracking_step(current_position, target_position)
        else:
            if now - last_face_at >= FACE_TRACKING_SEARCH_DELAY_SECONDS and now - last_search_at >= FACE_TRACKING_SEARCH_INTERVAL_SECONDS:
                face_tracking_search_target_position = select_next_face_tracking_search_target(search_target_position)
                face_tracking_last_search_at = now
                search_target_position = face_tracking_search_target_position
                last_search_at = face_tracking_last_search_at
                state_changed = True

            if now - last_face_at >= FACE_TRACKING_SEARCH_DELAY_SECONDS:
                next_position = compute_next_face_tracking_step(
                    current_position,
                    search_target_position,
                    max_step=FACE_TRACKING_SEARCH_STEP,
                )
            elif now - last_face_at >= FACE_TRACKING_RETURN_DELAY_SECONDS and abs(current_position - FACE_TRACKING_CENTER_POSITION) > FACE_TRACKING_MOVE_TOLERANCE:
                next_position = compute_next_face_tracking_step(
                    current_position,
                    FACE_TRACKING_CENTER_POSITION,
                    max_step=FACE_TRACKING_RETURN_STEP,
                )
    elif recenter_pending and abs(current_position - FACE_TRACKING_CENTER_POSITION) > FACE_TRACKING_MOVE_TOLERANCE:
        next_position = compute_next_face_tracking_step(
            current_position,
            FACE_TRACKING_CENTER_POSITION,
            max_step=FACE_TRACKING_RETURN_STEP,
        )
    elif recenter_pending:
        with face_tracking_state_lock:
            face_tracking_recenter_pending = False
        state_changed = True

    if next_position is not None and next_position != current_position:
        node.send_output(
            'move_servo',
            pa.array([{'id': FACE_TRACKING_SERVO_ID, 'position': next_position}]),
            metadata={},
        )
        with face_tracking_state_lock:
            face_tracking_current_position = next_position
            face_tracking_last_move_at = now
            if not face_tracking_enabled and abs(next_position - FACE_TRACKING_CENTER_POSITION) <= FACE_TRACKING_MOVE_TOLERANCE:
                face_tracking_recenter_pending = False
        state_changed = True

    if state_changed:
        broadcast_face_tracking_state()


async def fetch_go2rtc_frame(*, force_refresh: bool = False) -> bytes | None:
    """Fetch a recent JPEG frame through go2rtc and cache it briefly."""
    global camera_snapshot_bytes, camera_snapshot_taken_at

    now = time.monotonic()
    with camera_snapshot_lock:
        if not force_refresh and camera_snapshot_bytes and now - camera_snapshot_taken_at <= CAMERA_TTL_SECONDS:
            return camera_snapshot_bytes

    frame_url = f'{GO2RTC_BASE_URL}/api/frame.jpeg?src={GO2RTC_STREAM_SRC}'
    timeout = aiohttp.ClientTimeout(total=CAMERA_FETCH_TIMEOUT_SECONDS)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(frame_url) as response:
                if response.status != 200:
                    raise RuntimeError(f'go2rtc frame request failed: {response.status}')
                frame = await response.read()

        if not frame.startswith(b'\xff\xd8'):
            raise RuntimeError('go2rtc returned invalid JPEG data')

        with camera_snapshot_lock:
            camera_snapshot_bytes = frame
            camera_snapshot_taken_at = now

        return frame
    except Exception as error:
        logging.warning('Camera snapshot failed via go2rtc: %s', error)
        with camera_snapshot_lock:
            return camera_snapshot_bytes


async def camera_snapshot(request: web.Request):
    """Serve a recent camera JPEG frame for the UI background."""
    frame = await fetch_go2rtc_frame()
    if not frame:
        return web.Response(text='Camera unavailable', status=503)

    if request.query.get('annotated') == '1':
        frame = annotate_face_tracking_frame(frame)

    return web.Response(
        body=frame,
        content_type='image/jpeg',
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Access-Control-Allow-Origin': '*',
        },
    )


async def camera_stream(request: web.Request):
    """Proxy the go2rtc MJPEG stream through the existing HTTPS web node."""
    if request.query.get('annotated') == '1':
        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
                'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
                'Pragma': 'no-cache',
                'Access-Control-Allow-Origin': '*',
            },
        )
        await response.prepare(request)

        try:
            while True:
                frame = await fetch_go2rtc_frame()
                if frame:
                    annotated_frame = annotate_face_tracking_frame(frame)
                    part = (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n'
                        + f'Content-Length: {len(annotated_frame)}\r\n\r\n'.encode('ascii')
                        + annotated_frame
                        + b'\r\n'
                    )
                    await response.write(part)

                await asyncio.sleep(0.12)
        except (asyncio.CancelledError, ConnectionResetError):
            logging.debug('Annotated camera stream client disconnected')
        except Exception as error:
            logging.warning('Annotated camera stream failed: %s', error)
        finally:
            try:
                await response.write_eof()
            except Exception:
                pass

        return response

    stream_url = f'{GO2RTC_BASE_URL}/api/stream.mjpeg?src={GO2RTC_STREAM_SRC}'
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=CAMERA_FETCH_TIMEOUT_SECONDS, sock_read=None)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(stream_url) as upstream:
                if upstream.status != 200:
                    body = await upstream.text()
                    logging.warning('go2rtc stream request failed: %s %s', upstream.status, body[:200])
                    return web.Response(text='Camera stream unavailable', status=503)

                response = web.StreamResponse(
                    status=200,
                    headers={
                        'Content-Type': upstream.headers.get(
                            'Content-Type',
                            'multipart/x-mixed-replace; boundary=frame',
                        ),
                        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
                        'Pragma': 'no-cache',
                        'Access-Control-Allow-Origin': '*',
                    },
                )
                await response.prepare(request)

                async for chunk in upstream.content.iter_chunked(16384):
                    await response.write(chunk)

                await response.write_eof()
                return response
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        logging.warning('Camera stream proxy failed: %s', error)
        return web.Response(text='Camera stream unavailable', status=503)
    except ConnectionResetError:
        logging.debug('Camera stream client disconnected')
        return web.Response(status=499)


def ensure_photo_gallery_dir():
    """Ensure the on-device photo gallery directory exists."""
    PHOTO_GALLERY_DIR.mkdir(parents=True, exist_ok=True)


def serialize_photo_path(photo_path: Path) -> dict:
    """Convert a saved photo path into API-friendly metadata."""
    stat = photo_path.stat()
    captured_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return {
        'filename': photo_path.name,
        'url': f'/photos/{photo_path.name}',
        'captured_at': captured_at,
        'size_bytes': stat.st_size,
    }


async def list_photos(request: web.Request):
    """Return the current saved photo gallery."""
    ensure_photo_gallery_dir()
    photo_paths = sorted(
        [path for path in PHOTO_GALLERY_DIR.iterdir() if path.suffix.lower() in {'.jpg', '.jpeg'}],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return web.json_response({'photos': [serialize_photo_path(path) for path in photo_paths]})


async def capture_photo(request: web.Request):
    """Capture a JPEG frame from go2rtc and persist it to the robot."""
    ensure_photo_gallery_dir()
    frame = await fetch_go2rtc_frame()
    if not frame:
        return web.json_response({'error': 'camera unavailable'}, status=503)

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    source = str(payload.get('source') or 'ui').strip().lower()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    photo_path = PHOTO_GALLERY_DIR / f'{timestamp}-{source}-{uuid4().hex[:6]}.jpg'
    photo_path.write_bytes(frame)
    logging.info('Saved photo to %s', photo_path)

    return web.json_response({
        'ok': True,
        'photo': serialize_photo_path(photo_path),
    })


async def get_face_tracking_state(request: web.Request):
    """Return the current face tracking state."""
    return web.json_response(serialize_face_tracking_state())


async def set_face_tracking_state(request: web.Request):
    """Enable or disable server-side face-follow mode."""
    global face_tracking_enabled, face_tracking_face_detected, face_tracking_target_position
    global face_tracking_recenter_pending, face_tracking_last_detection_at, face_tracking_faces
    global face_tracking_last_face_switch_at, face_tracking_last_search_at
    global face_tracking_search_target_position
    global face_tracking_locked_center_x, face_tracking_locked_velocity_x
    global face_tracking_locked_area, face_tracking_last_observation_at

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    requested_enabled = bool(payload.get('enabled'))
    if requested_enabled and not face_tracking_supported:
        return web.json_response(
            {
                'ok': False,
                'error': FACE_TRACKING_IMPORT_ERROR or 'OpenCV face tracking unavailable',
                'state': serialize_face_tracking_state(),
            },
            status=503,
        )

    with face_tracking_state_lock:
        face_tracking_enabled = requested_enabled
        face_tracking_face_detected = False
        face_tracking_last_detection_at = 0.0
        face_tracking_target_position = face_tracking_current_position
        face_tracking_recenter_pending = not requested_enabled
        face_tracking_faces = []
        face_tracking_last_face_switch_at = 0.0
        face_tracking_last_search_at = 0.0
        face_tracking_search_target_position = FACE_TRACKING_CENTER_POSITION
        face_tracking_locked_center_x = 0.5
        face_tracking_locked_velocity_x = 0.0
        face_tracking_locked_area = 0.0
        face_tracking_last_observation_at = 0.0

    broadcast_face_tracking_state()
    return web.json_response({'ok': True, 'state': serialize_face_tracking_state()})



def flush_web_inputs(node: Node, profile_manager: GamepadProfileManager):
    """Process queued events received from WebSocket clients.

    Iterates through `global_web_inputs`, handles special events like saving
    grid state or joystick settings locally, and forwards other events
    to the appropriate Dora outputs.

    Args:
        node: The Dora node instance.
        profile_manager: The GamepadProfileManager instance (unused here but
                         passed for consistency).
    """
    global global_web_inputs
    if not global_web_inputs:
        return
    import os, json
    logging.info(f"Processing {len(global_web_inputs)} web events")
    for web_event in global_web_inputs:
        if web_event.get("output_id") == "save_grid_state":
            grid_state_path = os.path.join(os.path.dirname(__file__), "..", "grid_state.json")
            with open(grid_state_path, "w", encoding="utf-8") as f:
                json.dump(web_event["data"], f)

            # Broadcast the updated grid state to all connected clients
            for ws in ws_clients.copy():
                if not ws.closed:
                    try:
                        response = {
                            "id": "grid_state",
                            "value": web_event["data"],
                            "type": "EVENT"
                        }
                        asyncio.run_coroutine_threadsafe(
                            ws.send_str(json.dumps(response)),
                            web_loop
                        )
                    except Exception as e:
                        print(f"Error broadcasting grid state: {e}")
                else:
                    ws_clients.discard(ws)

        elif web_event.get("output_id") == "save_joystick_servo":
            # Handle joystick servo selection persistence
            widget_id = web_event.get("data", {}).get("id")
            axis = web_event.get("data", {}).get("axis")
            servo_id = web_event.get("data", {}).get("servoId")

            if widget_id and axis in ['x', 'y']:
                # Load current grid state
                grid_state_path = os.path.join(os.path.dirname(__file__), "..", "grid_state.json")
                grid_state = {}
                if os.path.exists(grid_state_path):
                    try:
                        with open(grid_state_path, "r", encoding="utf-8") as f:
                            grid_state = json.load(f)
                    except Exception as e:
                        print(f"Error loading grid state: {e}")

                # Update the widget with the new servo ID
                if widget_id in grid_state:
                    # Update the appropriate servo ID property
                    servo_prop = f"{axis}ServoId"
                    grid_state[widget_id][servo_prop] = servo_id

                    # Save the updated grid state
                    with open(grid_state_path, "w", encoding="utf-8") as f:
                        json.dump(grid_state, f)

                    # Broadcast the updated grid state
                    for ws in ws_clients.copy():
                        if not ws.closed:
                            try:
                                response = {
                                    "id": "grid_state",
                                    "value": grid_state,
                                    "type": "EVENT"
                                }
                                asyncio.run_coroutine_threadsafe(
                                    ws.send_str(json.dumps(response)),
                                    web_loop
                                )
                            except Exception as e:
                                print(f"Error broadcasting updated joystick state: {e}")
                        else:
                            ws_clients.discard(ws)

                    print(f"Updated joystick {widget_id} {axis}-axis to servo {servo_id}")
                else:
                    print(f"Cannot update joystick {widget_id}: widget not found in grid state")

        elif web_event.get("output_id") == "get_grid_state":
            # Load and send grid state to the requesting client
            grid_state_path = os.path.join(os.path.dirname(__file__), "..", "grid_state.json")
            grid_state = {}

            if os.path.exists(grid_state_path):
                try:
                    with open(grid_state_path, "r", encoding="utf-8") as f:
                        grid_state = json.load(f)
                except Exception as e:
                    print(f"Error loading grid state: {e}")

            # Send to the client that requested it
            for ws in ws_clients.copy():
                if not ws.closed:
                    try:
                        response = {
                            "id": "grid_state",
                            "value": grid_state,
                            "type": "EVENT"
                        }
                        asyncio.run_coroutine_threadsafe(
                            ws.send_str(json.dumps(response)),
                            web_loop
                        )
                    except Exception as e:
                        print(f"Error sending grid state: {e}")
                else:
                    ws_clients.discard(ws)
        else:
            node.send_output(
                output_id=web_event["output_id"], data=pa.array(web_event["data"]), metadata=web_event["metadata"]
            )
    global_web_inputs = []


async def websocket_handler(request: web.Request):
    """Handle incoming WebSocket connections and messages.

    Manages the lifecycle of a WebSocket connection, receives messages
    from the client, queues them for processing by `flush_web_inputs`,
    and removes the client upon disconnection.

    Args:
        request: The aiohttp request object.

    Returns:
        The WebSocketResponse object.
    """
    logging.info("New WebSocket connection request received")
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Add to clients
    ws_clients.add(ws)
    logging.info(f"WebSocket connection established - {len(ws_clients)} active connections")

    # Send connection confirmation
    try:
        welcome_msg = {
            "id": "connection_status",
            "value": {"status": "connected", "timestamp": time.time()},
            "type": "EVENT"
        }
        await ws.send_str(json.dumps(welcome_msg))
        await ws.send_str(json.dumps({
            'id': 'face_tracking_state',
            'value': serialize_face_tracking_state(),
            'type': 'EVENT',
        }))

        # Process incoming messages
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    event = json.loads(msg.data)
                    output_id = event.get('output_id')
                    logging.debug(f"Processed event with output_id: {output_id}")

                    # More detailed logging only for important configuration changes
                    if output_id in ['save_joystick_servo']:
                        logging.info(f"Joystick servo assignment: {event.get('data')}")

                    global_web_inputs.append(event)
                except Exception as e:
                    logging.error(f"Error processing WebSocket text message: {e}")
                    global_web_inputs.append({"raw": msg.data})
            elif msg.type == web.WSMsgType.BINARY:
                try:
                    import pyarrow as pa
                    buf = pa.BufferReader(msg.data)
                    batch = pa.ipc.read_record_batch(buf)
                    row = {k: v[0] for k, v in batch.to_pydict().items()}
                    global_web_inputs.append(row)
                except Exception as e:
                    logging.error(f"Error processing binary websocket message: {e}")
            elif msg.type == web.WSMsgType.ERROR:
                logging.error(f"WebSocket connection closed with exception {ws.exception()}")
    except Exception as e:
        logging.error(f"WebSocket handler error: {e}")
    finally:
        ws_clients.discard(ws)
        logging.info(f"WebSocket connection closed - {len(ws_clients)} active connections remain")

    return ws


async def index(request: web.Request):
    """Serve the main HTML template for the React frontend.

    Renders `template.html` using Jinja2. Currently injects an empty
    grid state, as the state is primarily managed via WebSocket.

    Args:
        request: The aiohttp request object.

    Returns:
        An aiohttp web Response object containing the rendered HTML.
    """
    import os, json
    template = request.app['jinja_env'].get_template('template.html')
    # For fixed layout, we don't need to load grid state
    rendered = template.render(gridState=json.dumps({}))
    return web.Response(text=rendered, content_type='text/html')


async def broadcast_bytes(data_bytes: bytes):
    """Broadcast binary data (decoded as UTF-8 string) to all connected WebSocket clients.

    Args:
        data_bytes: The bytes object containing the message to broadcast.
    """
    try:
        data_str = data_bytes.decode("utf-8")

        # Reduce logging for common events
        if '"id":"servo_status"' in data_str or '"id":"servos_list"' in data_str:
            logging.debug(f"Broadcasting servo data to {len(ws_clients)} clients")
        else:
            logging.debug(f"Broadcasting to {len(ws_clients)} clients: {data_str[:50]}...")

        active_clients = 0

        for ws in ws_clients.copy():
            try:
                if not ws.closed:
                    await ws.send_str(data_str)
                    active_clients += 1
                else:
                    ws_clients.discard(ws)
            except Exception as e:
                logging.error(f"Error sending to client: {e}")
                ws_clients.discard(ws)

        # Minimal logging for broadcasts
        logging.debug(f"Broadcast complete to {active_clients} active clients")
    except Exception as e:
        logging.error(f"Error in broadcast_bytes: {e}")

def asset_url(asset):
    return asset


def start_background_webserver():
    """Initialize and start the aiohttp web server in a background thread."""
    async def init_app():
        """Async function to set up the aiohttp application."""
        import os
        import jinja2
        import json
        import aiohttp

        ensure_photo_gallery_dir()
        app = web.Application()
        aiohttp_debugtoolbar.setup(app, intercept_redirects=True, hosts=['127.0.0.1', '::1'])
        template_path = os.path.join(os.path.dirname(__file__), "..", "resources")
        app['jinja_env'] = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
        app.router.add_get('/', index)
        app.router.add_get('/ws', websocket_handler)
        app.router.add_get('/camera/snapshot.jpg', camera_snapshot)
        app.router.add_get('/camera/stream.mjpeg', camera_stream)
        app.router.add_get('/api/photos', list_photos)
        app.router.add_post('/api/photos/capture', capture_photo)
        app.router.add_get('/api/face-tracking', get_face_tracking_state)
        app.router.add_post('/api/face-tracking', set_face_tracking_state)
        app.router.add_static('/resources/', path=template_path, name='resources')
        app.router.add_static('/photos/', path=str(PHOTO_GALLERY_DIR), name='photos', show_index=False, append_version=False)
        
        # Add specific route for icons with correct MIME types
        app.router.add_static('/icons/', 
            path=os.path.join(template_path, "icons"),
            name='icons', 
            show_index=True,
            append_version=False
        )
        
        # Add specific route for screenshots
        app.router.add_static('/screenshots/', 
            path=os.path.join(template_path, "screenshots"),
            name='screenshots', 
            show_index=True,
            append_version=False
        )
        
        # Add special route for manifest.webmanifest with correct MIME type
        async def serve_manifest(request):
            manifest_path = os.path.join(template_path, "manifest.webmanifest")
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    content = f.read()
                return web.Response(text=content, content_type="application/manifest+json")
            return web.Response(status=404)
        
        app.router.add_get('/manifest.webmanifest', serve_manifest)
        
        # Add special route for service-worker.js with correct MIME type
        async def serve_service_worker(request):
            sw_path = os.path.join(template_path, "service-worker.js")
            if os.path.exists(sw_path):
                with open(sw_path, 'r') as f:
                    content = f.read()
                return web.Response(text=content, content_type="application/javascript")
            return web.Response(status=404)
            
        app.router.add_get('/service-worker.js', serve_service_worker)
        
        # Add handler for serving icon files with correct MIME type
        async def serve_icon(request):
            icon_name = request.match_info.get('icon')
            icon_path = os.path.join(template_path, "icons", icon_name)
            if os.path.exists(icon_path):
                # Log that we're trying to serve this icon
                logging.info(f"Serving icon: {icon_name} from {icon_path}")
                return web.FileResponse(
                    path=icon_path,
                    headers={
                        'Content-Type': 'image/png',
                        'Cache-Control': 'max-age=86400'
                    }
                )
            logging.error(f"Icon not found: {icon_name}")
            return web.Response(status=404)
            
        app.router.add_get('/icons/{icon}', serve_icon)
        
        # Add handler for serving screenshot files with correct MIME type
        async def serve_screenshot(request):
            screenshot_name = request.match_info.get('screenshot')
            screenshot_path = os.path.join(template_path, "screenshots", screenshot_name)
            if os.path.exists(screenshot_path):
                # Log that we're trying to serve this screenshot
                logging.info(f"Serving screenshot: {screenshot_name} from {screenshot_path}")
                return web.FileResponse(
                    path=screenshot_path,
                    headers={
                        'Content-Type': 'image/png',
                        'Cache-Control': 'max-age=86400'
                    }
                )
            logging.error(f"Screenshot not found: {screenshot_name}")
            return web.Response(status=404)
            
        app.router.add_get('/screenshots/{screenshot}', serve_screenshot)

        app.router.add_static('/build/',
            path=os.path.join(os.path.dirname(__file__), "..", "resources/build"),
            name='build',
            show_index=True,
            append_version=True
        )

        # Handler for serving images from arbitrary paths
        async def get_image(request):
            """Serve images from arbitrary file paths."""
            path = request.query.get('path')

            if not path:
                return web.Response(text="Missing 'path' parameter", status=400)

            # Basic security check to only allow image files
            if not path.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                return web.Response(text="Only image files are allowed", status=403)

            # Check if file exists
            if not os.path.exists(path):
                return web.Response(text=f"Image not found: {path}", status=404)

            try:
                # Determine content type based on file extension
                extension = os.path.splitext(path)[1].lower()
                content_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.png': 'image/png'
                }.get(extension, 'application/octet-stream')

                # Create a file response
                return web.FileResponse(
                    path=path,
                    headers={
                        'Content-Type': content_type,
                        'Cache-Control': 'max-age=3600',  # Cache for 1 hour
                        'Access-Control-Allow-Origin': '*'  # Allow cross-origin access
                    }
                )
            except Exception as e:
                logging.error(f"Error serving image {path}: {str(e)}")
                return web.Response(text=f"Error serving image: {str(e)}", status=500)

        # Add route for image serving
        app.router.add_get('/get-image', get_image)

        # Proxy endpoint for communicating with eye displays
        async def eye_proxy(request):
            """Proxy requests to eye displays."""
            ip = request.query.get('ip')
            filename = request.query.get('filename')

            if not ip or not filename:
                return web.Response(text="Missing 'ip' or 'filename' parameter", status=400)

            try:
                # Construct the request URL to the eye display
                url = f"http://{ip}/playgif?name={filename}"

                # Use aiohttp.ClientSession to make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        status = response.status
                        response_text = await response.text()

                        return web.Response(
                            text=response_text,
                            status=status,
                            headers={
                                'Content-Type': 'text/plain',
                                'Access-Control-Allow-Origin': '*'
                            }
                        )
            except Exception as e:
                logging.error(f"Error proxying request to eye display {ip}: {str(e)}")
                return web.Response(
                    text=f"Error communicating with eye display: {str(e)}",
                    status=500,
                    headers={'Access-Control-Allow-Origin': '*'}
                )

        # Add route for eye display proxy
        app.router.add_get('/eye-proxy', eye_proxy)

        import ssl
        import os
        import subprocess
        # Set the paths for the self-signed certificate and key
        cert_file = os.path.join(os.path.dirname(__file__), "..", "cert.pem")
        key_file = os.path.join(os.path.dirname(__file__), "..", "key.pem")
        # Generate self-signed certs if they do not exist
        if not (os.path.exists(cert_file) and os.path.exists(key_file)):
            print("Generating self-signed certificates")
            subprocess.run([
                "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
                "-keyout", key_file, "-out", cert_file, "-days", "365", "-subj", "/CN=localhost"
            ], check=True)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8443, ssl_context=ssl_context)
        await site.start()

    def run_loop():
        global web_loop
        loop = asyncio.new_event_loop()
        web_loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_app())
        print("DEBUG: Web server started on port 8443")
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()


def start_asset_compilation():
    """Start the Webpack Encore asset compilation process in watch mode."""
    cmd = ['nodes/web/resources/node_modules/.bin/encore', 'dev', '--watch']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    def print_output():
        for line in iter(proc.stdout.readline, ""):
            print("[ASSET COMPILER]", line, end="")
    threading.Thread(target=print_output, daemon=True).start()


def main():
    """Main function for the Web Node.

    Starts the background web server, initializes the Dora node and the
    GamepadProfileManager, and enters the main Dora event loop to process
    incoming events from other nodes and the web UI.
    """
    # start_asset_compilation() # Usually run manually or via Makefile
    start_background_webserver()
    node = Node()

    # Initialize gamepad profile manager
    profile_manager = GamepadProfileManager()

    # Periodic profile list broadcasting
    last_profiles_broadcast = 0

    for event in node:
        try:
            if event["type"] == "INPUT" and "id" in event and (event["id"] == "tick"):
                # Process all pending web inputs
                flush_web_inputs(node, profile_manager)
                process_face_tracking(node)

                # Periodically broadcast gamepad profiles list
                current_time = time.time()
                if current_time - last_profiles_broadcast > 5:  # Every 5 seconds
                    try:
                        # Emit the updated list of profiles to Dora
                        emit_profiles_list(node, profile_manager)

                        # Send full profiles directly to WebSocket clients (not simplified)
                        full_profiles = profile_manager.list_profiles()

                        response = {
                            "id": "gamepad_profiles_list",
                            "value": full_profiles,
                            "type": "EVENT"
                        }

                        serialized = json.dumps(response, default=str).encode('utf-8')
                        asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)
                        logging.info(f"Broadcasted profiles list to {len(ws_clients)} WebSocket clients")

                        last_profiles_broadcast = current_time
                    except Exception as e:
                        logging.error(f"Error broadcasting profiles list: {e}")
            elif event["type"] == "INPUT":
                logging.info(f"Received input event: {event['id']}")
                event_value = event['value'].to_pylist()

                if event["id"] in ("waveshare_servo/servo_status", "servo_status", "waveshare_servo/servos_list", "servos_list"):
                    update_face_tracking_head_position(event_value)
                elif event["id"] in ("sequence/sequence_state", "sequence_state"):
                    update_face_tracking_sequence_state(event_value)

                # Handle gamepad profile events
                if event["id"] == "save_gamepad_profile":
                    print(f"DEBUG - main.py: Received save_gamepad_profile event")
                    print(f"DEBUG - main.py: Event data: {event}")
                    print(f"DEBUG - main.py: Value type: {type(event['value'])}")

                    if hasattr(event['value'], 'to_pylist'):
                        value_list = event['value'].to_pylist()
                        print(f"DEBUG - main.py: Value as pylist: {value_list}")
                    else:
                        print(f"DEBUG - main.py: Value doesn't have to_pylist method")

                    handle_save_gamepad_profile(event, node, profile_manager)
                    print(f"Saved gamepad profile: {event['value'][0] if hasattr(event['value'], '__getitem__') else event['value']}")
                    print(f"Profiles storage directory: {profile_manager.profiles_dir}")
                    print(f"DEBUG - main.py: Directory exists: {os.path.exists(profile_manager.profiles_dir)}")
                    # After saving, emit updated profiles list
                    emit_profiles_list(node, profile_manager)
                    continue
                elif event["id"] == "get_gamepad_profile":
                    handle_get_gamepad_profile(event, node, profile_manager)
                    continue
                elif event["id"] == "check_gamepad_profile":
                    handle_check_gamepad_profile(event, node, profile_manager)
                    continue
                elif event["id"] == "delete_gamepad_profile":
                    handle_delete_gamepad_profile(event, node, profile_manager)
                    continue
                elif event["id"] == "list_gamepad_profiles":
                    handle_list_gamepad_profiles(event, node, profile_manager)
                    continue

                # Add special handling for runtime values
                if event["id"] == "power/runtime":
                    logging.info(f"Runtime value received: {event_value} (type: {type(event_value)})")
                    # Ensure runtime value is a valid number
                    if event_value and isinstance(event_value, list):
                        try:
                            runtime_val = float(event_value[0])
                            if runtime_val <= 0 or math.isinf(runtime_val) or math.isnan(runtime_val):
                                event_value[0] = 0
                            logging.info(f"Processed runtime: {event_value[0]}")
                        except Exception as e:
                            logging.error(f"Error processing runtime value: {e}")
                            event_value[0] = 0

                # Create the event data with potentially modified ID
                event_id = event["id"]

                # Transform event IDs to match what the frontend expects
                if event_id.startswith("waveshare_servo/"):
                    event_id = event_id.replace("waveshare_servo/", "")
                    logging.info(f"Transformed event ID from {event['id']} to {event_id}")

                event_data = {
                    "id": event_id,
                    "value": event_value,
                    "type": "EVENT"
                }

                # Handle servo-related events
                if event["id"] == "waveshare_servo/servo_status" or event["id"] == "servo_status":
                    # Fix for json-in-string format for servo status updates
                    if event_value and len(event_value) == 1 and isinstance(event_value[0], str):
                        try:
                            parsed_value = json.loads(event_value[0])
                            event_value = parsed_value
                            event_data["value"] = parsed_value
                        except json.JSONDecodeError as e:
                            logging.error(f"Failed to parse servo_status JSON string: {e}")

                    # Log info about single servo update
                    if event_value:
                        if isinstance(event_value, list):
                            try:
                                servo_ids = [s.get('id') for s in event_value]
                                logging.info(f"Servo status update: {len(event_value)} servos {servo_ids}")
                            except (TypeError, AttributeError) as e:
                                logging.error(f"Error processing servo IDs in list: {e}, value: {event_value[:100]}")
                        else:
                            try:
                                # Single servo update
                                servo_id = event_value.get('id')
                                logging.info(f"Servo status update: servo {servo_id}")
                            except (TypeError, AttributeError) as e:
                                logging.error(f"Error processing single servo: {e}, value type: {type(event_value)}")
                    else:
                        logging.warning("Received empty servo status update")

                elif event["id"] == "waveshare_servo/servos_list" or event["id"] == "servos_list":
                    # Log info about servos list
                    if event_value:
                        # Detailed logging of raw event value for troubleshooting
                        logging.info(f"Raw servos_list event value type: {type(event_value)}, length: {len(event_value)}")
                        if len(event_value) > 0:
                            logging.info(f"First element type: {type(event_value[0])}")
                            if isinstance(event_value[0], str):
                                logging.info(f"First element content sample: {event_value[0][:100]}...")

                        # Fix for json-in-string format: if the first item is a string containing JSON
                        if len(event_value) == 1 and isinstance(event_value[0], str):
                            try:
                                parsed_value = json.loads(event_value[0])
                                if isinstance(parsed_value, list):
                                    event_value = parsed_value
                                    event_data["value"] = parsed_value
                                elif isinstance(parsed_value, dict):
                                    event_value = [parsed_value]
                                    event_data["value"] = [parsed_value]
                            except json.JSONDecodeError as e:
                                logging.error(f"Failed to parse servos_list JSON string: {e}")

                        # Log the servo IDs
                        try:
                            # Check if event_value is a list of dicts or list of something else
                            if all(isinstance(item, dict) for item in event_value):
                                servo_ids = [s.get('id') for s in event_value]
                                logging.info(f"Servos list update: {len(event_value)} servos {servo_ids}")
                            else:
                                logging.error(f"event_value contains non-dict items: {event_value[:5]}")
                        except (TypeError, AttributeError) as e:
                            logging.error(f"Error processing servo IDs: {e}, value type: {type(event_value)}, value: {event_value}")
                    else:
                        logging.warning("Received empty servos list")


                # Handle config-related events
                elif event["id"] in ["config/setting_updated", "config/settings"]:
                    event_name = event["id"].replace("config/", "")
                    if event_name == "settings":
                        logging.info(f"Received complete settings")
                    else:
                        logging.info(f"Received config event: {event_name} with value: {event_value[:100] if len(str(event_value)) > 100 else event_value}")

                serialized = json.dumps(event_data, default=str).encode('utf-8')
                if web_loop is not None:
                    asyncio.run_coroutine_threadsafe(broadcast_bytes(serialized), web_loop)
        except Exception as e:
            logging.error(f"Error handling event: {e}")


if __name__ == "__main__":
    main()
