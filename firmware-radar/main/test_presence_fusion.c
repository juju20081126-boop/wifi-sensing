/**
 * @file test_presence_fusion.c
 * @brief Host-side tests for presence_fusion.c.
 *
 * NOT part of the firmware build. Compile and run standalone once a C
 * compiler is available, e.g.:
 *
 *     gcc -Wall -Wextra -std=c11 test_presence_fusion.c presence_fusion.c \
 *         -o test_presence_fusion && ./test_presence_fusion
 *
 * These tests were written before any C compiler was available on the
 * machine that authored them (see firmware-radar/README.md, "Verification
 * status"). They exist so verification can happen the moment a toolchain is
 * available, mirroring the test-first discipline used for the Python
 * detector in src/breathing and src/presence -- but until one of these
 * actually runs and passes, treat this file as an unexecuted test plan, not
 * evidence.
 */
#include <assert.h>
#include <stdio.h>
#include "presence_fusion.h"

static void test_empty_starts_empty(void) {
    presence_fusion_t pf;
    presence_fusion_config_t cfg = presence_fusion_default_config();
    presence_fusion_init(&pf, &cfg);

    presence_state_t s = presence_fusion_update(&pf, 0, false, 0.0f);

    assert(s.occupied == false);
    assert(s.reason == PRESENCE_REASON_EMPTY);
    printf("test_empty_starts_empty: PASS\n");
}

static void test_motion_is_held_before_room_becomes_empty(void) {
    presence_fusion_t pf;
    presence_fusion_config_t cfg = presence_fusion_default_config();
    cfg.motion_hold_ms = 10000;
    presence_fusion_init(&pf, &cfg);

    presence_state_t entered = presence_fusion_update(&pf, 0, true, 0.0f);
    presence_state_t held = presence_fusion_update(&pf, 9000, false, 0.0f);
    presence_state_t empty = presence_fusion_update(&pf, 10100, false, 0.0f);

    assert(entered.occupied == true);
    assert(entered.reason == PRESENCE_REASON_MOTION);
    assert(held.occupied == true);
    assert(held.motion_held == true);
    assert(empty.occupied == false);
    assert(empty.reason == PRESENCE_REASON_EMPTY);
    printf("test_motion_is_held_before_room_becomes_empty: PASS\n");
}

static void test_k_of_n_wander_evidence_can_hold_occupancy_without_motion(void) {
    presence_fusion_t pf;
    presence_fusion_config_t cfg = presence_fusion_default_config();
    cfg.wander_on_threshold = 0.6f;
    cfg.wander_off_threshold = 0.3f;
    cfg.evidence_window = 5;
    cfg.evidence_required = 2;
    presence_fusion_init(&pf, &cfg);

    presence_state_t first = presence_fusion_update(&pf, 0, false, 0.75f);
    presence_state_t second = presence_fusion_update(&pf, 1000, false, 0.10f);
    presence_state_t confirmed = presence_fusion_update(&pf, 2000, false, 0.80f);

    assert(first.occupied == false);   /* only 1 vote so far, need 2 */
    assert(second.occupied == false);
    assert(confirmed.occupied == true);
    assert(confirmed.reason == PRESENCE_REASON_WANDER);
    printf("test_k_of_n_wander_evidence_can_hold_occupancy_without_motion: PASS\n");
}

static void test_single_high_sample_does_not_trigger_presence(void) {
    /* Guards against exactly WaveSight's failure mode inverted: a single
     * noisy spike must not be mistaken for a real, sustained presence. */
    presence_fusion_t pf;
    presence_fusion_config_t cfg = presence_fusion_default_config();
    cfg.wander_on_threshold = 0.6f;
    cfg.wander_off_threshold = 0.3f;
    cfg.evidence_window = 5;
    cfg.evidence_required = 3;
    presence_fusion_init(&pf, &cfg);

    presence_state_t spike = presence_fusion_update(&pf, 0, false, 0.99f);
    presence_state_t back_to_quiet = presence_fusion_update(&pf, 1000, false, 0.0f);

    assert(spike.occupied == false);
    assert(back_to_quiet.occupied == false);
    printf("test_single_high_sample_does_not_trigger_presence: PASS\n");
}

static void test_hysteresis_keeps_presence_through_a_brief_dip(void) {
    presence_fusion_t pf;
    presence_fusion_config_t cfg = presence_fusion_default_config();
    cfg.wander_on_threshold = 0.6f;
    cfg.wander_off_threshold = 0.2f;
    cfg.evidence_window = 3;
    cfg.evidence_required = 2;
    presence_fusion_init(&pf, &cfg);

    presence_fusion_update(&pf, 0, false, 0.7f);
    presence_fusion_update(&pf, 1000, false, 0.7f);
    presence_state_t confirmed = presence_fusion_update(&pf, 2000, false, 0.7f);
    assert(confirmed.wander_present == true);

    /* A dip below the ON threshold but above OFF should not immediately
     * clear presence, because the off-threshold vote still counts it. */
    presence_state_t dip = presence_fusion_update(&pf, 3000, false, 0.4f);
    assert(dip.wander_present == true);

    printf("test_hysteresis_keeps_presence_through_a_brief_dip: PASS\n");
}

static void test_motion_and_wander_reason_reported_when_both_present(void) {
    presence_fusion_t pf;
    presence_fusion_config_t cfg = presence_fusion_default_config();
    cfg.wander_on_threshold = 0.5f;
    cfg.wander_off_threshold = 0.2f;
    cfg.evidence_window = 2;
    cfg.evidence_required = 1;
    cfg.motion_hold_ms = 5000;
    presence_fusion_init(&pf, &cfg);

    presence_state_t s = presence_fusion_update(&pf, 0, true, 0.9f);

    assert(s.occupied == true);
    assert(s.reason == PRESENCE_REASON_MOTION_AND_WANDER);
    printf("test_motion_and_wander_reason_reported_when_both_present: PASS\n");
}

static void test_reset_clears_all_state(void) {
    presence_fusion_t pf;
    presence_fusion_config_t cfg = presence_fusion_default_config();
    cfg.wander_on_threshold = 0.5f;
    cfg.wander_off_threshold = 0.2f;
    cfg.evidence_window = 2;
    cfg.evidence_required = 1;
    presence_fusion_init(&pf, &cfg);

    presence_fusion_update(&pf, 0, true, 0.9f);
    presence_fusion_reset(&pf);
    presence_state_t s = presence_fusion_update(&pf, 100000, false, 0.0f);

    assert(s.occupied == false);
    assert(s.reason == PRESENCE_REASON_EMPTY);
    printf("test_reset_clears_all_state: PASS\n");
}

int main(void) {
    test_empty_starts_empty();
    test_motion_is_held_before_room_becomes_empty();
    test_k_of_n_wander_evidence_can_hold_occupancy_without_motion();
    test_single_high_sample_does_not_trigger_presence();
    test_hysteresis_keeps_presence_through_a_brief_dip();
    test_motion_and_wander_reason_reported_when_both_present();
    test_reset_clears_all_state();
    printf("\nall tests passed\n");
    return 0;
}
