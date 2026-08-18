/**
 * @file web_server.c
 * @brief See web_server.h. Verification status: source-backed only, never
 *        compiled or flashed as of writing -- see firmware-radar/README.md.
 */
#include "web_server.h"

#include "cJSON.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "radar_app.h"

static const char *TAG = "web_server";

static const char *reason_to_string(presence_reason_t reason) {
    switch (reason) {
        case PRESENCE_REASON_MOTION:
            return "motion";
        case PRESENCE_REASON_WANDER:
            return "wander";
        case PRESENCE_REASON_MOTION_AND_WANDER:
            return "motion+wander";
        case PRESENCE_REASON_EMPTY:
        default:
            return "empty";
    }
}

static const char *DASHBOARD_HTML =
    "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
    "<title>Presence radar</title><style>"
    "body{font-family:sans-serif;max-width:32rem;margin:2rem auto;padding:0 1rem}"
    "h1{font-size:1.2rem}"
    ".tile{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:0.5rem 0}"
    ".big{font-size:1.6rem;font-weight:bold}"
    ".occupied{color:#0a7a2f}.empty{color:#888}"
    "button{padding:0.6rem 1rem;font-size:1rem}"
    "</style></head><body>"
    "<h1>Presence radar</h1>"
    "<div class=\"tile\">Occupied<br><span id=\"occupied\" class=\"big\">--</span>"
    "<br><small id=\"reason\"></small></div>"
    "<div class=\"tile\">Jitter (movement) <span id=\"jitter\">--</span><br>"
    "Wander (stillness) <span id=\"wander\">--</span></div>"
    "<div class=\"tile\">"
    "<button onclick=\"calibrate()\">Start 60s empty-room calibration</button>"
    "<div id=\"calib_status\"></div></div>"
    "<script>"
    "async function poll(){"
    "const r=await fetch('/api/status');const s=await r.json();"
    "const o=document.getElementById('occupied');"
    "o.textContent=s.occupied?'YES':'no';"
    "o.className='big '+(s.occupied?'occupied':'empty');"
    "document.getElementById('reason').textContent='reason: '+s.reason;"
    "document.getElementById('jitter').textContent=s.jitter.toFixed(5);"
    "document.getElementById('wander').textContent=s.wander.toFixed(5);"
    "document.getElementById('calib_status').textContent="
    "s.calibrating?'Calibrating... keep the room empty.':'';"
    "}"
    "async function calibrate(){"
    "await fetch('/api/calibrate',{method:'POST'});poll();"
    "}"
    "poll();setInterval(poll,1000);"
    "</script></body></html>";

static esp_err_t root_get_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, DASHBOARD_HTML, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t status_get_handler(httpd_req_t *req) {
    radar_app_snapshot_t snap;
    radar_app_get_snapshot(&snap);

    cJSON *root = cJSON_CreateObject();
    cJSON_AddBoolToObject(root, "occupied", snap.presence.occupied);
    cJSON_AddBoolToObject(root, "motion_held", snap.presence.motion_held);
    cJSON_AddBoolToObject(root, "wander_present", snap.presence.wander_present);
    cJSON_AddStringToObject(root, "reason", reason_to_string(snap.presence.reason));
    cJSON_AddNumberToObject(root, "jitter", snap.jitter);
    cJSON_AddNumberToObject(root, "wander", snap.wander);
    cJSON_AddBoolToObject(root, "calibrating", snap.calibrating);
    cJSON_AddNumberToObject(root, "updated_at_ms", snap.updated_at_ms);

    char *body = cJSON_PrintUnformatted(root);
    httpd_resp_set_type(req, "application/json");
    esp_err_t err = httpd_resp_send(req, body, HTTPD_RESP_USE_STRLEN);

    cJSON_free(body);
    cJSON_Delete(root);
    return err;
}

static esp_err_t calibrate_post_handler(httpd_req_t *req) {
    esp_err_t err = radar_app_calibrate_start(60);

    cJSON *root = cJSON_CreateObject();
    cJSON_AddBoolToObject(root, "started", err == ESP_OK);
    if (err != ESP_OK) {
        cJSON_AddStringToObject(root, "error", esp_err_to_name(err));
    }
    char *body = cJSON_PrintUnformatted(root);
    httpd_resp_set_type(req, "application/json");
    esp_err_t send_err = httpd_resp_send(req, body, HTTPD_RESP_USE_STRLEN);

    cJSON_free(body);
    cJSON_Delete(root);
    return send_err;
}

esp_err_t web_server_start(void) {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    httpd_handle_t server = NULL;

    esp_err_t err = httpd_start(&server, &config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "httpd_start failed: %s", esp_err_to_name(err));
        return err;
    }

    const httpd_uri_t root_uri = {
        .uri = "/", .method = HTTP_GET, .handler = root_get_handler};
    const httpd_uri_t status_uri = {
        .uri = "/api/status", .method = HTTP_GET, .handler = status_get_handler};
    const httpd_uri_t calibrate_uri = {
        .uri = "/api/calibrate", .method = HTTP_POST, .handler = calibrate_post_handler};

    httpd_register_uri_handler(server, &root_uri);
    httpd_register_uri_handler(server, &status_uri);
    httpd_register_uri_handler(server, &calibrate_uri);

    ESP_LOGI(TAG, "web server started");
    return ESP_OK;
}
