#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "TPLINK";
const char* password = "02652474";

WebServer server(80);


const int LED_PIN = 2;
bool ledState = false; 


void handleRoot() {
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  String html = R"rawliteral(
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Керування світлодіодом ESP32</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #1e1e2f;
      color: #fff;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
    }
    h1 { margin-bottom: 10px; }
    .status {
      font-size: 20px;
      margin-bottom: 30px;
      padding: 8px 20px;
      border-radius: 20px;
    }
    .status.on { background: #2ecc71; }
    .status.off { background: #555; }
    button {
      font-size: 20px;
      padding: 15px 40px;
      margin: 10px;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      color: #fff;
    }
    .btn-on { background: #2ecc71; }
    .btn-off { background: #e74c3c; }
    button:active { opacity: 0.7; }
  </style>
</head>
<body>
  <h1>Керування світлодіодом</h1>
  <div id="status" class="status off">Завантаження...</div>
  <div>
    <button class="btn-on" onclick="sendCmd('on')">Увімкнути</button>
    <button class="btn-off" onclick="sendCmd('off')">Вимкнути</button>
  </div>

  <script>
    function updateStatus(state) {
      const el = document.getElementById('status');
      if (state === 'ON') {
        el.textContent = 'Світлодіод: УВІМКНЕНО';
        el.className = 'status on';
      } else {
        el.textContent = 'Світлодіод: ВИМКНЕНО';
        el.className = 'status off';
      }
    }

    function sendCmd(cmd) {
      fetch('/led/' + cmd)
        .then(r => r.text())
        .then(t => updateStatus(cmd === 'on' ? 'ON' : 'OFF'))
        .catch(e => console.error(e));
    }

    // При завантаженні сторінки одразу питаємо поточний стан
    fetch('/led/status')
      .then(r => r.text())
      .then(t => updateStatus(t.trim()))
      .catch(e => console.error(e));
  </script>
</body>
</html>
)rawliteral";

  server.send(200, "text/html", html);
}

void handleLedOn() {
  ledState = true;
  digitalWrite(LED_PIN, HIGH);
  server.send(200, "text/plain", "ON");
  Serial.println("Світлодіод увімкнено!");
}

void handleLedOff() {
  ledState = false;
  digitalWrite(LED_PIN, LOW);
  server.send(200, "text/plain", "OFF");
  Serial.println("Світлодіод вимкнено!");
}

void handleLedStatus() {
  server.send(200, "text/plain", ledState ? "ON" : "OFF");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- СТАРТ ПЛАТИ ---");

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  WiFi.begin(ssid, password);
  Serial.print("Підключення до Wi-Fi: ");
  Serial.println(ssid);

  while (WiFi.status() != WL_CONNECTED) {
    delay(5000);
    Serial.print(".");
  }

  delay(1000);

  Serial.println("");
  
  Serial.print(" УСПІШНО ПІДКЛЮЧЕНО!\n");
  Serial.print(" IP-АДРЕСА ТВОЄЇ ESP32: ");
  Serial.println(WiFi.localIP());
  Serial.println(" Відкрий цю адресу в браузері, щоб керувати світлодіодом.");
  Serial.println(" Скопіюй її та встав у свій Python-скрипт, якщо потрібно.");
 
  server.on("/", handleRoot);
  server.on("/led/on", handleLedOn);
  server.on("/led/off", handleLedOff);
  server.on("/led/status", handleLedStatus);

  server.begin();
  Serial.println("HTTP сервер запущено і слухає порт 80...");
}

void loop() {
  server.handleClient();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Увага: З'єднання Wi-Fi втрачено!");
    delay(5000);
  }
}
