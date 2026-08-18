/**
 * @file radar_app.h
 * @brief Wires Espressif's esp-radar component to presence_fusion and GPIO.
 */
#ifndef RADAR_APP_H
#define RADAR_APP_H

#include "esp_err.h"
#include "presence_fusion.h"

#ifdef __cplusplus
extern "C" {
#endif

/** GPIO driven high while presence_fusion reports occupied. */
#define RADAR_APP_PRESENCE_GPIO CONFIG_RADAR_PRESENCE_GPIO

/** GPIO driven high while the jitter-based movement filter is active. */
#define RADAR_APP_MOVEMENT_GPIO CONFIG_RADAR_MOVEMENT_GPIO

/** Starts esp-radar and the presence fusion pipeline. Call after WiFi is
 *  connected to a station, since esp-radar reads CSI off that link. */
esp_err_t radar_app_start(void);

/** Stops esp-radar cleanly, e.g. before reconfiguring WiFi. */
esp_err_t radar_app_stop(void);

/** Begins empty-room calibration for duration_s seconds. The room must be
 *  empty for the whole window; see PLAN.md Gate 2 before trusting the
 *  learned thresholds this produces. */
esp_err_t radar_app_calibrate_start(uint32_t duration_s);

/** True while a calibration run is in progress. */
bool radar_app_is_calibrating(void);

/** Thread-safe snapshot of the latest fused state and raw signal values,
 *  for the web server to read without touching radar internals directly. */
typedef struct {
    presence_state_t presence;
    float jitter;
    float wander;
    bool calibrating;
    uint32_t updated_at_ms;
} radar_app_snapshot_t;

void radar_app_get_snapshot(radar_app_snapshot_t *out);

#ifdef __cplusplus
}
#endif

#endif /* RADAR_APP_H */
