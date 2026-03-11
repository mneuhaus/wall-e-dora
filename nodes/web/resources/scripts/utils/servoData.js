/**
 * Normalize servo payloads from the websocket bridge into a clean array of servo objects.
 *
 * The backend emits:
 * - `servo_status` as a single object
 * - `servos_list` as an array of objects
 *
 * Older/bad payloads can still arrive as strings, nulls, or mixed arrays. This helper
 * keeps frontend state stable and prevents rendering `Servo #undefined`.
 *
 * @param {*} payload Raw websocket event value
 * @returns {Array<Object>} Filtered list of servo objects with a usable id
 */
export function normalizeServoList(payload) {
  const items = Array.isArray(payload) ? payload : [payload];

  return items.filter((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      return false;
    }

    const numericId = typeof item.id === 'string' ? Number.parseInt(item.id, 10) : item.id;
    return Number.isInteger(numericId);
  }).map((item) => ({
    ...item,
    id: typeof item.id === 'string' ? Number.parseInt(item.id, 10) : item.id,
  }));
}

/**
 * Normalize diagnostics payloads from the websocket bridge into a clean array.
 *
 * The backend emits `servo_diagnostics` as either a single object or an array of
 * objects when a bulk overview is requested.
 *
 * @param {*} payload Raw websocket event value
 * @returns {Array<Object>} Filtered diagnostics payloads with numeric ids
 */
export function normalizeDiagnosticsPayload(payload) {
  const items = Array.isArray(payload) ? payload : [payload];

  return items.filter((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      return false;
    }

    const numericId = typeof item.id === 'string' ? Number.parseInt(item.id, 10) : item.id;
    return Number.isInteger(numericId);
  }).map((item) => ({
    ...item,
    id: typeof item.id === 'string' ? Number.parseInt(item.id, 10) : item.id,
  }));
}

/**
 * Find a servo by id inside a raw websocket payload.
 *
 * @param {*} payload Raw websocket event value
 * @param {number|string|null|undefined} servoId Servo id to match
 * @returns {Object|null} Matching servo object, if found
 */
export function findServoInPayload(payload, servoId) {
  const normalizedId = Number.parseInt(servoId, 10);
  if (!Number.isInteger(normalizedId)) {
    return null;
  }

  return normalizeServoList(payload).find((servo) => servo.id === normalizedId) || null;
}
