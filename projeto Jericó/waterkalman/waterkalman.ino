/ Autor: Elohim Felipe
// 2025, Março

#include <WiFi.h>
#include <HTTPClient.h>

// Configuração do WiFi
const char* SECRET_SSID = "REDE 2G";
const char* SECRET_PASS = "ee061224";

//==========================================================
// Configuração do sensor
const int PINO_SENSOR = 32;
volatile unsigned long pulsos = 0;
const float fator_calibracao = 450.0; // Ajuste conforme seu sensor
//===========================================================
// Temporização
unsigned long tempo_anterior = 0;
const unsigned long intervalo_envio = 30000; // 30 segundos
//==============================================================
// Volume acumulado em litros
float volume_total = 0.0;
float volume_total_filtrado = 0.0;
float valor_filtrado_freq = 0.0;
float fluxo_filtrado = 0.0;

// Declaração antecipada das funções
void contador_pulso();
void enviar_dados(float frequencia, float fluxo, float volume_total);
float algoritmo_kalman(int input);

//=====================================================================
void setup() {
  Serial.begin(115200);
  pinMode(PINO_SENSOR, INPUT_PULLUP);

  WiFi.begin(SECRET_SSID, SECRET_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Conectando ao WiFi...");
  }
  Serial.println("Conectado ao WiFi");

  attachInterrupt(digitalPinToInterrupt(PINO_SENSOR), contador_pulso, RISING);

  // Executa a primeira medição imediatamente
  tempo_anterior = millis() - intervalo_envio;
}

//=====================================================================
void loop() {
  unsigned long tempo_atual = millis();

  if (tempo_atual - tempo_anterior >= intervalo_envio) {
    detachInterrupt(digitalPinToInterrupt(PINO_SENSOR));

    float segundos = intervalo_envio / 1000.0;
    float frequencia = pulsos / segundos;
    float fluxo = (frequencia / fator_calibracao) * 60.0; // L/min

    // Cálculo do volume no intervalo
    float volume_intervalo = (fluxo / 60.0) * segundos;
    volume_total += volume_intervalo;

    // Enviar para API FREQ e vol sem filtro
    enviar_dados(frequencia, fluxo, volume_total);

    //=======================================================================
    // Aplicando a função algoritmo_kalman
    // nas linhas 129/130 estou achando o equilíbrio para a medição

    if (pulsos > 0) {
      int valor_ruido = pulsos / segundos;
      valor_filtrado_freq = algoritmo_kalman(valor_ruido);
    } else {
      // Nenhum pulso: estado parado, zera o valor filtrado
      valor_filtrado_freq = 0.0;
    }

    // Fluxo e volume filtrado só se frequência filtrada > 0
    if (valor_filtrado_freq > 0.0) {
      fluxo_filtrado = (valor_filtrado_freq / fator_calibracao) * 60.0;
      float volume_filtrado_intervalo = (fluxo_filtrado / 60.0) * segundos;
      volume_total_filtrado += volume_filtrado_intervalo;
    } else {
      fluxo_filtrado = 0.0;
    }

    //==========================================================
    // Envio para Serial Plotter — apenas frequencia e valor filtrado
    Serial.print(frequencia, 3);
    Serial.print(";");
    Serial.println(valor_filtrado_freq, 3);

    //==========================================================
    // Exibir no Serial Monitor de forma organizada
    Serial.println("--------------------------------------------------");
    Serial.printf("Frequência:           %.3f Hz\n", frequencia);
    Serial.printf("Fluxo:                %.3f L/min\n", fluxo);
    Serial.printf("Volume Total:         %.3f Litros\n", volume_total);
    Serial.printf("Frequência Filtrada:  %.3f Hz\n", valor_filtrado_freq);
    Serial.printf("Fluxo Filtrado:       %.3f L/min\n", fluxo_filtrado);
    Serial.printf("Volume Filtrado:      %.3f Litros\n", volume_total_filtrado);
    Serial.println("--------------------------------------------------");

    // Resetar contagem de pulsos
    pulsos = 0;
    tempo_anterior = tempo_atual;

    attachInterrupt(digitalPinToInterrupt(PINO_SENSOR), contador_pulso, RISING);
  }
}

//=====================================================================
// Função de interrupção para contar pulsos
void contador_pulso() {
  pulsos++;
}

//=====================================================================
// Função para enviar os dados(volume sem/com filtro) para a API
void enviar_dados(float frequencia, float fluxo, float volume) {
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    http.begin(client, "http://laica.ifrn.edu.br/access-ng/log/");
    http.addHeader("Content-Type", "application/json");

    // ==================================================
    // enviando para API valores não filtrados
    String body = "{\"deviceMac\": \"A0:DD:6C:85:96:D0\",";
    body += "\"topic\": \"monitoramento_FF\",";
    body += "\"type\": \"INFO\",";
    body += "\"message\": \"frequencia = ";
    body += String(frequencia, 3);
    body += " Hz, fluxo = ";
    body += String(fluxo, 3);
    body += " L/min, volume total = ";
    body += String(volume, 3);
    body += " L, ";
    // ======================================================
    //enviando para API valores filtrados
    body += "frequencia filtrada = ";
    body += String(valor_filtrado_freq, 3);
    body += " Hz, fluxo filtrado = ";
    body += String(fluxo_filtrado, 3);
    body += " L/min, volume total filtrado = ";
    body += String(volume_total_filtrado, 3);
    body += " L\"}";

    Serial.println("Enviando dados para API...");
    Serial.println(body);  // Debug do JSON montado

    int httpCode = http.POST(body);

    if (httpCode > 0) {
      Serial.print("Código de resposta: ");
      Serial.println(httpCode);
      Serial.print("Resposta da API: ");
      Serial.println(http.getString());
    } else {
      Serial.print("Erro na requisição: ");
      Serial.println(http.errorToString(httpCode).c_str());
    }

    http.end();
  } else {
    Serial.println("WiFi desconectado, não foi possível enviar os dados.");
  }
}

//=============================================================================
//  FUNÇÃO PARA O ALGORITMO DE KALMAN
float algoritmo_kalman(int input) {
  // nas linhas 129/130 estou achando o equilíbrio para a medição
  static float Q = 0.05;   // variância do processo (quanto confio na medição)
  static float R = 1.0;    // erro de medição
  static float X_est = 0.0; // estimativa inicial do estado
  static float P = 1.0;    // incerteza da estimativa

  float Z = (float)input; // medida atual
  float X_pred = X_est;   // previsão do estado
  float P_pred = P + Q;   // previsão da incerteza
  float K = P_pred / (P_pred + R); // ganho de Kalman

  X_est = X_pred + K * (Z - X_pred); // atualização do estado
  P = (1 - K) * P_pred; // atualização da incerteza

  return X_est; // retorna a estimativa filtrada
}