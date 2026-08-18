/**
 * @file presence_fusion.h
 * @brief Fuses esp-radar's jitter (movement) and wander (stillness) signals
 *        into one stable occupancy decision.
 *
 * Hardware-independent by design: no ESP-IDF, FreeRTOS, or esp_radar includes.
 * This lets the decision logic be built and unit tested on a host compiler,
 * the same discipline used for src/presence/tracker.py elsewhere in this
 * repository, even though nothing in this specific file has been compiled or
 * tested yet -- see the repository-root note in firmware-radar/README.md.
 *
 * Why this exists: Espressif's esp_radar.h documents `waveform_wander` as the
 * signal for detecting a present-but-stationary person. WaveSight
 * (github.com/ErfanDL/WaveSight), reviewed for inspiration, computes it but
 * never reads it -- its "someone" output is only a movement-hold timeout.
 * This module is the fix: `wander` gets its own K-of-N evidence vote with
 * hysteresis, exactly parallel to how src/presence/tracker.py treats the
 * breathing score, and the two signals are combined as an OR.
 */
#ifndef PRESENCE_FUSION_H
#define PRESENCE_FUSION_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Fixed upper bound on the wander evidence window; no dynamic allocation. */
#define PRESENCE_FUSION_MAX_WINDOW 16

typedef enum {
    PRESENCE_REASON_EMPTY = 0,
    PRESENCE_REASON_MOTION,
    PRESENCE_REASON_WANDER,
    PRESENCE_REASON_MOTION_AND_WANDER,
} presence_reason_t;

typedef struct {
    /** Milliseconds occupancy is held after the last confirmed movement. */
    uint32_t motion_hold_ms;

    /** Wander must be >= this to count as a "present" vote while off. */
    float wander_on_threshold;

    /** Wander must be >= this to keep counting as "present" once on.
     *  Must be <= wander_on_threshold; the gap is the hysteresis band. */
    float wander_off_threshold;

    /** Samples considered for the wander vote. 1..PRESENCE_FUSION_MAX_WINDOW. */
    uint8_t evidence_window;

    /** Votes required within the window to confirm wander presence.
     *  1..evidence_window. */
    uint8_t evidence_required;
} presence_fusion_config_t;

typedef struct {
    bool occupied;
    bool motion_held;
    bool wander_present;
    presence_reason_t reason;
} presence_state_t;

typedef struct {
    presence_fusion_config_t config;

    bool has_last_motion;
    uint32_t last_motion_ms;

    float wander_history[PRESENCE_FUSION_MAX_WINDOW];
    uint8_t wander_history_len;   /**< number of valid entries so far */
    uint8_t wander_history_next;  /**< next slot to overwrite */
    bool wander_present;
} presence_fusion_t;

/**
 * @brief A conservative default configuration.
 *
 * Wander thresholds are placeholders -- they MUST be replaced with values
 * derived from an empty-room calibration (see PLAN.md Gate 2/M2) before this
 * is trusted for anything. Shipping an invented threshold is exactly the
 * mistake this project's evidence discipline exists to avoid.
 */
presence_fusion_config_t presence_fusion_default_config(void);

/** Zero-initialise fusion state for the given config. config is copied. */
void presence_fusion_init(presence_fusion_t *pf, const presence_fusion_config_t *config);

/** Clear all temporal history and return to an empty state, same config. */
void presence_fusion_reset(presence_fusion_t *pf);

/**
 * @brief Consume one radar sample and return the fused occupancy decision.
 *
 * @param pf              Fusion state, previously initialised.
 * @param now_ms           Monotonic milliseconds (e.g. esp_log_timestamp()).
 * @param motion_detected  This sample's movement decision (e.g. the existing
 *                          jitter K-of-N filter -- unchanged from WaveSight's
 *                          own approach, which handles movement well).
 * @param wander_value      Raw waveform_wander from esp_radar's callback.
 */
presence_state_t presence_fusion_update(presence_fusion_t *pf, uint32_t now_ms,
                                         bool motion_detected, float wander_value);

#ifdef __cplusplus
}
#endif

#endif /* PRESENCE_FUSION_H */
