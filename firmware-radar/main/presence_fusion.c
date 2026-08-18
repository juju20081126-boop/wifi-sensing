/**
 * @file presence_fusion.c
 * @brief See presence_fusion.h for the design rationale.
 */
#include "presence_fusion.h"

presence_fusion_config_t presence_fusion_default_config(void) {
    presence_fusion_config_t config = {
        .motion_hold_ms = 180000,       /* 3 minutes, matches the Python tracker's default */
        .wander_on_threshold = 0.02f,   /* PLACEHOLDER -- calibrate before trusting */
        .wander_off_threshold = 0.01f,  /* PLACEHOLDER -- calibrate before trusting */
        .evidence_window = 5,
        .evidence_required = 2,
    };
    return config;
}

void presence_fusion_init(presence_fusion_t *pf, const presence_fusion_config_t *config) {
    pf->config = *config;
    presence_fusion_reset(pf);
}

void presence_fusion_reset(presence_fusion_t *pf) {
    pf->has_last_motion = false;
    pf->last_motion_ms = 0;
    pf->wander_history_len = 0;
    pf->wander_history_next = 0;
    pf->wander_present = false;
    for (int i = 0; i < PRESENCE_FUSION_MAX_WINDOW; i++) {
        pf->wander_history[i] = 0.0f;
    }
}

static uint8_t clamp_window(uint8_t window) {
    if (window < 1) {
        return 1;
    }
    if (window > PRESENCE_FUSION_MAX_WINDOW) {
        return PRESENCE_FUSION_MAX_WINDOW;
    }
    return window;
}

presence_state_t presence_fusion_update(presence_fusion_t *pf, uint32_t now_ms,
                                         bool motion_detected, float wander_value) {
    if (motion_detected) {
        pf->has_last_motion = true;
        pf->last_motion_ms = now_ms;
    }

    const uint8_t window = clamp_window(pf->config.evidence_window);
    uint8_t required = pf->config.evidence_required;
    if (required < 1) {
        required = 1;
    }
    if (required > window) {
        required = window;
    }

    /* Push the new sample into the fixed-size ring buffer. */
    pf->wander_history[pf->wander_history_next] = wander_value;
    pf->wander_history_next = (uint8_t)((pf->wander_history_next + 1) % window);
    if (pf->wander_history_len < window) {
        pf->wander_history_len++;
    }

    /* Hysteresis: use the "on" threshold while off, the lower "off"
     * threshold while already on, so a single noisy sample near the
     * boundary cannot flicker the state. */
    const float threshold = pf->wander_present
        ? pf->config.wander_off_threshold
        : pf->config.wander_on_threshold;

    uint8_t votes = 0;
    for (uint8_t i = 0; i < pf->wander_history_len; i++) {
        if (pf->wander_history[i] >= threshold) {
            votes++;
        }
    }
    pf->wander_present = (votes >= required);

    bool motion_held = false;
    if (pf->has_last_motion) {
        const uint32_t elapsed = now_ms - pf->last_motion_ms; /* wraps safely (unsigned) */
        motion_held = (elapsed <= pf->config.motion_hold_ms);
    }

    presence_state_t state;
    state.motion_held = motion_held;
    state.wander_present = pf->wander_present;
    state.occupied = motion_held || pf->wander_present;

    if (motion_held && pf->wander_present) {
        state.reason = PRESENCE_REASON_MOTION_AND_WANDER;
    } else if (motion_held) {
        state.reason = PRESENCE_REASON_MOTION;
    } else if (pf->wander_present) {
        state.reason = PRESENCE_REASON_WANDER;
    } else {
        state.reason = PRESENCE_REASON_EMPTY;
    }

    return state;
}
