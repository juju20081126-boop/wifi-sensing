/**
 * @file radar_app.c
 * @brief See radar_app.h. Verification status: source-backed only, never
 *        compiled or flashed as of writing -- see firmware-radar/README.md.
 */
#include "radar_app.h"

#include <string.h>

#include "esp_log.h"
#include "esp_radar.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/timers.h"

static const char *TAG = "radar_app";

/* Movement K-of-N filter over jitter. WaveSight's own approach to movement
 * detection (as opposed to its stationary-presence gap) is sound, so the
 * shape is kept: a small ring buffer, a fixed count of outliers required.
 * Fixed here rather than exposed via Kconfig to keep the initial config
 * surface small; promote to runtime-configurable once real recordings (see
 * PLAN.md Gate 2) show these need tuning per room. */
#define MOVE_FILTER_WINDOW 8
#define MOVE_FILTER_OUTLIERS_REQUIRED 3
#define MOVE_JITTER_THRESHOLD_DEFAULT 0.02f /* PLACEHOLDER -- calibrate */

static presence_fusion_t s_fusion;
static presence_fusion_config_t s_fusion_config;
static float s_move_threshold = MOVE_JITTER_THRESHOLD_DEFAULT;

static float s_move_buf[MOVE_FILTER_WINDOW];
static uint32_t s_move_buf_count = 0;

static bool s_calibrating = false;
static TimerHandle_t s_calib_timer = NULL;

static portMUX_TYPE s_snapshot_lock = portMUX_INITIALIZER_UNLOCKED;
static radar_app_snapshot_t s_snapshot = {0};

static bool move_filter_update(float jitter_value) {
    s_move_buf[s_move_buf_count % MOVE_FILTER_WINDOW] = jitter_value;
    s_move_buf_count++;
    if (s_move_buf_count < MOVE_FILTER_WINDOW) {
        return false; /* not enough history yet */
    }
    uint32_t over = 0;
    for (int i = 0; i < MOVE_FILTER_WINDOW; i++) {
        if (s_move_buf[i] > s_move_threshold) {
            over++;
        }
    }
    return over >= MOVE_FILTER_OUTLIERS_REQUIRED;
}

static void radar_cb(const wifi_radar_info_t *info, void *ctx) {
    (void)ctx;

    if (s_calibrating) {
        /* esp_radar_train_start/stop handles its own sampling internally;
         * skip our own decision logic while it runs, matching the pattern
         * in WaveSight's radar_cb for its own calibration flag. */
        return;
    }

    const bool motion = move_filter_update(info->waveform_jitter);
    const uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000);

    presence_state_t state = presence_fusion_update(&s_fusion, now_ms, motion,
                                                      info->waveform_wander);

    gpio_set_level(RADAR_APP_PRESENCE_GPIO, state.occupied ? 1 : 0);
    gpio_set_level(RADAR_APP_MOVEMENT_GPIO, state.motion_held ? 1 : 0);

    taskENTER_CRITICAL(&s_snapshot_lock);
    s_snapshot.presence = state;
    s_snapshot.jitter = info->waveform_jitter;
    s_snapshot.wander = info->waveform_wander;
    s_snapshot.calibrating = s_calibrating;
    s_snapshot.updated_at_ms = now_ms;
    taskEXIT_CRITICAL(&s_snapshot_lock);
}

static void calib_timer_cb(TimerHandle_t timer) {
    (void)timer;

    float wander_threshold = 0.0f;
    float jitter_threshold = 0.0f;
    esp_err_t err = esp_radar_train_stop(&wander_threshold, &jitter_threshold);
    s_calibrating = false;

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "calibration failed: %s", esp_err_to_name(err));
        return;
    }

    /* esp_radar_train_stop returns one threshold per signal, not an on/off
     * pair. The off threshold is derived at a fixed ratio below it, the same
     * hysteresis-ratio idea used in src/presence/tracker.py and documented
     * in RuView's own firmware (EDGE_PRESENCE_HYST_RATIO = 0.5). */
    const float hysteresis_ratio = 0.5f;

    s_fusion_config.wander_on_threshold = wander_threshold;
    s_fusion_config.wander_off_threshold = wander_threshold * hysteresis_ratio;
    s_move_threshold = jitter_threshold;

    presence_fusion_init(&s_fusion, &s_fusion_config);

    ESP_LOGI(TAG, "calibration complete: wander_on=%.5f wander_off=%.5f jitter=%.5f",
             s_fusion_config.wander_on_threshold,
             s_fusion_config.wander_off_threshold,
             s_move_threshold);
}

esp_err_t radar_app_calibrate_start(uint32_t duration_s) {
    if (s_calibrating) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t err = esp_radar_train_start();
    if (err != ESP_OK) {
        return err;
    }

    s_calibrating = true;

    if (s_calib_timer == NULL) {
        s_calib_timer = xTimerCreate("radar_calib", pdMS_TO_TICKS(duration_s * 1000),
                                      pdFALSE, NULL, calib_timer_cb);
    } else {
        xTimerChangePeriod(s_calib_timer, pdMS_TO_TICKS(duration_s * 1000), portMAX_DELAY);
    }

    if (s_calib_timer == NULL) {
        s_calibrating = false;
        esp_radar_train_remove();
        return ESP_ERR_NO_MEM;
    }

    xTimerStart(s_calib_timer, portMAX_DELAY);
    ESP_LOGI(TAG, "calibration started, %lu s -- room must stay empty", (unsigned long)duration_s);
    return ESP_OK;
}

bool radar_app_is_calibrating(void) {
    return s_calibrating;
}

esp_err_t radar_app_start(void) {
    s_fusion_config = presence_fusion_default_config();
    presence_fusion_init(&s_fusion, &s_fusion_config);
    memset(s_move_buf, 0, sizeof(s_move_buf));
    s_move_buf_count = 0;

    gpio_set_direction(RADAR_APP_PRESENCE_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_direction(RADAR_APP_MOVEMENT_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(RADAR_APP_PRESENCE_GPIO, 0);
    gpio_set_level(RADAR_APP_MOVEMENT_GPIO, 0);

    esp_err_t err = esp_radar_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_radar_init failed: %s", esp_err_to_name(err));
        return err;
    }

    wifi_radar_config_t radar_config = WIFI_RADAR_CONFIG_DEFAULT();
    radar_config.csi_config.lltf_en = true;
    radar_config.csi_config.htltf_en = false;
    radar_config.csi_config.stbc_htltf2_en = false;
    radar_config.wifi_radar_cb = radar_cb;

    wifi_ap_record_t ap_info = {0};
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        memcpy(radar_config.filter_mac, ap_info.bssid, sizeof(ap_info.bssid));
    } else {
        ESP_LOGW(TAG, "no AP info yet; radar will not filter by source MAC");
    }

    err = esp_radar_set_config(&radar_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_radar_set_config failed: %s", esp_err_to_name(err));
        return err;
    }

    err = esp_radar_start();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_radar_start failed: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "radar started");
    return ESP_OK;
}

esp_err_t radar_app_stop(void) {
    return esp_radar_stop();
}

void radar_app_get_snapshot(radar_app_snapshot_t *out) {
    taskENTER_CRITICAL(&s_snapshot_lock);
    *out = s_snapshot;
    taskEXIT_CRITICAL(&s_snapshot_lock);
}
