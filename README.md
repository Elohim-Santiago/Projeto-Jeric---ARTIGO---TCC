# Projeto-Jeric---ARTIGO---TCC


# 🌊 Arquitetura IoT para Vazão Hídrica com Sensor Hall e Processamento Virtualizado

Este repositório apresenta um sistema **IoT** para monitoramento de fluxo de água em tempo real, combinando hardware de baixo custo, técnicas de filtragem adaptativa e backend containerizado.

## 🚀 Visão Geral

O sistema foi desenvolvido para **monitoramento preciso de vazão hídrica** em ambientes industriais, comerciais e institucionais. Ele combina um **ESP32** com o sensor de efeito Hall **YF-S201**, filtragem embarcada com **Filtro de Kalman** e **calibração adaptativa por Regressão Linear Recursiva (RLS)** no backend containerizado com Docker.

### 🔧 Tecnologias Utilizadas

- **ESP32** (ESP-WROOM-32)
- **Sensor de Fluxo YF-S201** (Efeito Hall)
- **Filtro de Kalman** (suavização de ruído no ESP32)
- **Regressão Linear Recursiva (RLS)** (calibração adaptativa no backend)
- **FastAPI** (API REST sobre TCP/IP)
- **PostgreSQL** (armazenamento de dados)
- **Grafana** (dashboards dinâmicos)
- **Docker & Docker Compose** (virtualização e escalabilidade)

## 🗂 Arquitetura do Sistema

- **ESP32** coleta pulsos do sensor YF-S201, aplica filtro de Kalman e envia dados via REST/JSON.
- **Backend em Docker**:
  - **FastAPI** (porta 8000): Recebe e valida os dados.
  - **PostgreSQL** (porta 5432): Armazena leituras de vazão.
  - **Grafana** (porta 3000): Exibe dashboards para visualização dos dados.

```
ESP32 -> API REST (FastAPI/Docker) -> PostgreSQL -> Grafana
```

## 📊 Resultados Principais

- **Erro médio final:** ≈2,1% (vs. ~10% do sensor bruto).
- **Latência ponta a ponta:** < 120 ms.
- **Redução de ruído e outliers** com Kalman.
- **Calibração adaptativa** com RLS para diferentes condições operacionais.

## 📝 Diferenciais

- Integração **Kalman + RLS** para maior precisão.
- Comunicação padronizada (REST/JSON).
- **Stack Docker Compose pronta** para replicação em diversos ambientes.
- Solução leve, portátil e escalável para aplicações reais.

## 📥 Como Executar

1. Clone este repositório:
   ```bash
   git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   cd SEU_REPOSITORIO
   ```

2. Inicie os serviços Docker:
   ```bash
   docker-compose up -d
   ```

3. Configure seu ESP32 para enviar dados via HTTP POST para:
   ```
   http://SEU_SERVIDOR:8000/api/v1/flow
   ```

4. Acesse o Grafana em `http://localhost:3000` e visualize os dados.

## 🧠 Aplicações

- Gestão de recursos hídricos.
- Supervisão em tempo real.
- Projetos educacionais e ambientes industriais/comerciais.

## 📜 Licença

Este projeto é distribuído sob a licença MIT. Consulte o arquivo LICENSE para mais informações.
