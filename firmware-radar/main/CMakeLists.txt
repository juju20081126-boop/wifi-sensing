idf_component_register(
    SRCS
        "app_main.c"
        "radar_app.c"
        "presence_fusion.c"
        "web_server.c"
    INCLUDE_DIRS "."
    REQUIRES
        esp_wifi
        esp_event
        esp_netif
        nvs_flash
        esp_http_server
        json
        driver
        esp_timer
        esp-radar
)
