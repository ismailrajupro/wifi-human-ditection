#include <WiFi.h>
#include <esp_wifi.h>
#include <esp_log.h>

const char* ssid     = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";

static uint32_t frame_count = 0;

static void wifi_csi_callback(void *ctx, wifi_csi_info_t *data) {
  if (!data || !data->buf) return;

  frame_count++;

  Serial.printf("CSI_DATA: frame=%lu,mac=", frame_count);
  Serial.printf("%02x:%02x:%02x:%02x:%02x:%02x,",
    data->mac[0], data->mac[1], data->mac[2],
    data->mac[3], data->mac[4], data->mac[5]);

  Serial.printf("rssi=%d,", data->rx_ctrl.rssi);

  Serial.printf("len=%d,data=", data->len);
  for (int i = 0; i < data->len; i++) {
    Serial.printf("%02x", data->buf[i]);
  }
  Serial.println();
}

void setup() {
  Serial.begin(921200);
  delay(1000);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");

  wifi_csi_config_t csi_config = {
    .lltf_en = 1,
    .htltf_en = 1,
    .stbc_htltf2_en = 0,
    .ltf_merge_en = 1,
    .channel_filter_en = 0,
    .manu_scale = 0,
    .shift = 0,
  };

  esp_wifi_set_csi(&csi_config);
  esp_wifi_set_csi_rx_cb(&wifi_csi_callback, NULL);
  esp_wifi_set_csi_config(&csi_config);
  esp_wifi_enable_csi();

  Serial.println("CSI receiver ready");
}

void loop() {
  esp_wifi_csi_trigger();
  delay(100);
}
