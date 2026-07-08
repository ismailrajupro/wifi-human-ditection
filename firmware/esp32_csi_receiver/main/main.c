#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/uart.h"

#define UART_PORT UART_NUM_0
#define BUF_SIZE 4096

static const char *TAG = "CSI_RECV";

static uint32_t frame_count = 0;

static void csi_callback(void *ctx, wifi_csi_info_t *data) {
    if (!data || !data->buf) return;

    uint8_t *buf = data->buf;
    uint8_t len = data->len;

    frame_count++;

    printf("CSI_DATA: frame=%lu,mac=", frame_count);
    printf("%02x:%02x:%02x:%02x:%02x:%02x,",
           data->mac[0], data->mac[1], data->mac[2],
           data->mac[3], data->mac[4], data->mac[5]);

    printf("rssi=%d,rssi_ack=%d,rate=%d,channel=%d,",
           data->rx_ctrl.rssi, data->rx_ctrl.rssi_ack,
           data->rx_ctrl.rate, data->rx_ctrl.chan);

    printf("len=%d,data=", len);
    for (int i = 0; i < len; i++) {
        printf("%02x", buf[i]);
    }
    printf("\n");

    vTaskDelay(pdMS_TO_TICKS(10));
}

static void wifi_init(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = CONFIG_ESP_WIFI_SSID,
            .password = CONFIG_ESP_WIFI_PASSWORD,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "Connecting to WiFi...");
    esp_wifi_connect();

    vTaskDelay(pdMS_TO_TICKS(5000));
}

static void csi_init(void) {
    wifi_csi_config_t csi_config = {
        .lltf_en = 1,
        .htltf_en = 1,
        .stbc_htltf2_en = 0,
        .ltf_merge_en = 1,
        .channel_filter_en = 0,
        .manu_scale = 0,
        .shift = 0,
    };

    ESP_ERROR_CHECK(esp_wifi_set_csi(&csi_config));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(&csi_callback, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&csi_config));
    ESP_ERROR_CHECK(esp_wifi_enable_csi());

    ESP_LOGI(TAG, "CSI enabled on channel %d", CONFIG_ESP_WIFI_CHANNEL);
}

void app_main(void) {
    ESP_ERROR_CHECK(nvs_flash_init());

    wifi_init();
    csi_init();

    ESP_LOGI(TAG, "CSI receiver ready. Sending pings to trigger CSI...");

    while (1) {
        esp_wifi_csi_trigger();
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
