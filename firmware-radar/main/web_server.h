/**
 * @file web_server.h
 * @brief Minimal self-hosted status dashboard and calibration control.
 *
 * Deliberately smaller than WaveSight's ~1,470-line embedded dashboard: one
 * status page, one JSON endpoint, one calibration trigger. No login, no
 * WiFi-provisioning UI, no LED/pin configuration screens. Those are real,
 * useful features WaveSight has that this project does not yet -- see
 * firmware-radar/README.md "What this does not do yet" before assuming
 * feature parity.
 */
#ifndef WEB_SERVER_H
#define WEB_SERVER_H

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t web_server_start(void);

#ifdef __cplusplus
}
#endif

#endif /* WEB_SERVER_H */
