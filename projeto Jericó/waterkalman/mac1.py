import numpy as np
import matplotlib.pyplot as plt
import requests
import re
import mysql.connector
from datetime import datetime

class Veronica():
    def __init__(self):
        self.api_url = "https://laica.ifrn.edu.br/access-ng/log"
        self.parametros = {
            "previous": 0,
            "next": 1,
            "pageSize": 60,
            "topic": "monitoramento_FF",
            "type": "INFO",
            "order": "desc"
        }
        self.log = self.puxando_log()

        # Debug: Mostrar as primeiras mensagens recebidas
        print("\nDebug - Primeiras mensagens recebidas:")
        for i, item in enumerate(self.log[:3]):
            print(f"Mensagem {i+1}: {item.get('message', '')}")

    def puxando_log(self):
        try:
            response = requests.get(self.api_url, params=self.parametros)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print("Erro ao tentar puxar o log:", e)
            return []

    def parse_mensagem(self, mensagem):
        """Parser robusto para extrair os valores da mensagem"""
        try:
            padrao_numero = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
            numeros = re.findall(padrao_numero, mensagem)
            numeros = [float(num) for num in numeros]

            print(f"\nDebug - Mensagem original: {mensagem}")
            print(f"Debug - Números extraídos: {numeros}")

            if len(numeros) >= 6:
                return tuple(numeros[:6])
            return None
        except Exception as e:
            print(f"Erro ao parsear mensagem '{mensagem}': {e}")
            return None

    def separando_infos_log(self):
        resultados_api = []
        for item in self.log:
            mensagem = item.get('message', '')
            if not mensagem:
                continue
            dados = self.parse_mensagem(mensagem)
            if dados is not None:
                resultados_api.append(dados)
                if len(resultados_api) == 1:
                    print("\nDebug - Primeiro registro parseado:")
                    print(f"Frequência: {dados[0]}")
                    print(f"Fluxo: {dados[1]}")
                    print(f"Volume: {dados[2]}")
                    print(f"Frequência filtrada: {dados[3]}")
                    print(f"Fluxo filtrado: {dados[4]}")
                    print(f"Volume filtrado: {dados[5]}")
        return resultados_api

    def regressao_linear_matricial(self):
        dados = self.separando_infos_log()

        if not dados:
            print("\nErro: Nenhum dado válido foi extraído das mensagens.")
            print("Possíveis causas:")
            print("1. O formato das mensagens não contém os valores esperados")
            print("2. As mensagens não seguem o padrão numérico esperado")
            print("3. O tópico 'monitoramento_FF' não contém dados de fluxo")
            print("\nSugestão: Verifique as mensagens brutas mostradas no debug acima")
            return

        print(f"\nSucesso! {len(dados)} registros foram processados.\n")

        frequencia_filtrada = np.array([linha[3] for linha in dados])
        fluxo_filtrado = np.array([linha[4] for linha in dados])

        lambda_ = 0.95
        theta = np.zeros((2, 1))
        P = np.eye(2) * 1000

        print("Executando regressão linear recursiva...")
        for t in range(len(frequencia_filtrada)):
            ft = frequencia_filtrada[t]
            Qt = fluxo_filtrado[t]

            phi_t = np.array([[ft], [1]])
            y_pred = float(phi_t.T @ theta)
            erro = Qt - y_pred

            K = (P @ phi_t) / (lambda_ + (phi_t.T @ P @ phi_t))
            theta = theta + K * erro
            P = (P - K @ phi_t.T @ P) / lambda_

            if t % 10 == 0 or t == len(frequencia_filtrada) - 1:
                print(f"Iteração {t+1}: a={theta[0][0]:.6f}, b={theta[1][0]:.6f}")

        a_final, b_final = theta[0][0], theta[1][0]
        print(f"\nEquação final: Q(f) = {a_final:.6f} * f + {b_final:.6f}")
        self.a_final = a_final
        self.b_final = b_final

        plt.figure(figsize=(12, 7))
        plt.scatter(frequencia_filtrada, fluxo_filtrado, c='blue', alpha=0.5, label='Dados')
        x_plot = np.linspace(min(frequencia_filtrada), max(frequencia_filtrada), 100)
        plt.plot(x_plot, a_final*x_plot + b_final, 'r-', label='Regressão RLS')

        plt.xlabel('Frequência (Hz)', fontsize=12)
        plt.ylabel('Vazão (L/min)', fontsize=12)
        plt.title('Relação Frequência-Vazão com Regressão Recursiva', fontsize=14)
        plt.legend(fontsize=11)
        plt.grid(True)
        plt.show()

    def inserindo_bd(self):
        if not hasattr(self, "a_final") or not hasattr(self, "b_final"):
            print("Coeficientes não encontrados. Verifique a execução da regressão!")
            return

        for i in range(10):
            try:
                conn = mysql.connector.connect(
                    host='mysqlsrv',
                    user='root',
                    password='laica',
                    database='monitoramento_agua'
                )
                print("Conectado com sucesso ao MySQL!")
                break
            except mysql.connector.Error as err:
                print(f"Erro ao tentar conectar (tentativa {i+1}/10): {err}")
                import time
                time.sleep(5)
        else:
            print("Não foi possível conectar ao MySQL após várias tentativas.")
            return

        try:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leituras_fluxo (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    created_at DATETIME(3),
                    frequencia_bruta FLOAT,
                    fluxo_bruto FLOAT,
                    volume_bruto FLOAT,
                    frequencia_filtrada FLOAT,
                    fluxo_filtrado FLOAT,
                    volume_filtrado FLOAT,
                    coef_a FLOAT,
                    coef_b FLOAT
                );
            """)

            dados = self.separando_infos_log()
            registros_inseridos = 0

            for i, item in enumerate(self.log):
                mensagem = item.get('message', '')
                iso_ts = item.get('createdAt')

                if not mensagem or not iso_ts:
                    continue

                try:
                    dt_obj = datetime.strptime(iso_ts.rstrip('Z'), "%Y-%m-%dT%H:%M:%S.%f")
                    timestamp = dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                except Exception as e:
                    print(f"Erro ao converter timestamp '{iso_ts}': {e}")
                    continue

                dados_extraidos = self.parse_mensagem(mensagem)
                if not dados_extraidos:
                    continue

                cursor.execute("""
                    INSERT INTO leituras_fluxo (
                        created_at,
                        frequencia_bruta,
                        fluxo_bruto,
                        volume_bruto,
                        frequencia_filtrada,
                        fluxo_filtrado,
                        volume_filtrado,
                        coef_a,
                        coef_b
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    timestamp,
                    float(dados_extraidos[0]),
                    float(dados_extraidos[1]),
                    float(dados_extraidos[2]),
                    float(dados_extraidos[3]),
                    float(dados_extraidos[4]),
                    float(dados_extraidos[5]),
                    float(self.a_final),
                    float(self.b_final)
                ))

                registros_inseridos += 1

            conn.commit()
            cursor.close()
            conn.close()
            print(f"{registros_inseridos} registros salvos no MySQL :)")

        except mysql.connector.Error as err:
            print("Erro ao executar operação no MySQL:", err)


# Execução do script
print("\nIniciando processamento...")
v = Veronica()
v.regressao_linear_matricial()
v.inserindo_bd()
