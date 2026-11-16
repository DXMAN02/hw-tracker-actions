import os, json, smtplib, requests
from email.mime.text import MIMEText
from datetime import datetime
from zoneinfo import ZoneInfo

EMAIL_ORIGEN = os.environ["EMAIL_ORIGEN"]
EMAIL_CONTRASENA = os.environ["EMAIL_CONTRASENA"]
EMAIL_DESTINO = os.environ["EMAIL_DESTINO"]
UMBRAL_SUBIDA = int(os.environ.get("UMBRAL_SUBIDA", "50"))

URL_PRODUCTO = "https://www.farmatodo.com.co/producto/1035283-juguete-hot-wheels-carro"
PRODUCTO_ID = 1035283
REGISTRO_FILE = "hw_registro.json"

TIENDAS_INTERES = {
    1151: "Sabaneta", 1114: "Alto de las palmas", 1189: "Mayorca",
    1103: "La Sebastiana", 1100: "San Lucas", 1131: "Las Vegas",
}
OTRAS_TIENDAS = {
    97: "Mall del este", 1106: "Milla de Oro", 1108: "Ciudad del Rio",
    1110: "Visitacion", 1119: "Los Parra", 1109: "Laureles",
    1158: "Provenza", 1184: "Arkadia", 1187: "Santafé", 98: "Tesoro",
    96: "Llanogrande", 1156: "Barroblanco",
}
TODAS = {**TIENDAS_INTERES, **OTRAS_TIENDAS}

STORE_IDS = [31,1160,39,43,47,54,74,53,2,80,79,76,81,3,4,6,7,9,11,15,51,52,67,85,83,22,23,24,26,27,28,29,30,37,40,41,42,44,45,46,50,61,62,63,64,68,69,71,72,73,14,19,20,89,88,93,94,95,1132,87,97,99,92,1106,1101,1108,91,1100,1102,1103,1107,1112,1118,1124,1136,1123,1122,1110,1113,1121,1128,1125,1134,1131,1135,1119,1115,1133,1147,96,1117,1130,1141,1140,1126,1129,1139,1143,1146,1137,1000,1001,1116,1163,1158,1156,1127,1175,1165,1161,1176,1109,1162,1169,1166,1168,1114,1154,1184,1187,1189,1173,1190,1159,1171,16,32,1151,1177,98]


def cargar_registro():
    if os.path.exists(REGISTRO_FILE):
        with open(REGISTRO_FILE, "r") as f:
            return json.load(f)
    return {"stock_anterior": {}, "historial": []}


def guardar_registro(registro):
    with open(REGISTRO_FILE, "w") as f:
        json.dump(registro, f, indent=2, ensure_ascii=False)


def obtener_stock():
    url = "https://ftd-td-webcomponents-793791410058.us-central1.run.app/proxy/store-stock/individual-stock"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept": "application/json",
    }
    r = requests.post(url, json={"itemId": PRODUCTO_ID, "storeIds": STORE_IDS}, headers=headers, timeout=30)
    r.raise_for_status()
    return {item["storeId"]: item["stock"] for item in r.json()["data"]["stocks"]}


def calcular_cajas(subida):
    cajas = subida // 72
    if cajas == 0:
        return ""
    return " 📦 +1 caja" if cajas == 1 else f" 📦 +{cajas} cajas"


def enviar_email(asunto, cuerpo):
    msg = MIMEText(cuerpo, "plain", "utf-8")
    msg["Subject"] = asunto
    msg["From"] = EMAIL_ORIGEN
    msg["To"] = EMAIL_DESTINO
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ORIGEN, EMAIL_CONTRASENA)
        server.sendmail(EMAIL_ORIGEN, EMAIL_DESTINO, msg.as_string())
    print("✅ Email enviado")


def main():
    now = datetime.now(ZoneInfo("America/Bogota"))
    print(f"🔍 Revisando... {now:%d/%m/%Y %H:%M:%S}")

    registro = cargar_registro()
    stock_actual = obtener_stock()
    anterior_all = registro["stock_anterior"]
    primera_vez = not anterior_all

    principales, otras = [], []
    nombres_p, nombres_o = [], []

    if not primera_vez:
        for store_id, stock in stock_actual.items():
            if store_id not in TODAS:
                continue
            nombre = TODAS[store_id]
            anterior = anterior_all.get(str(store_id), 0)
            subida = stock - anterior
            if subida >= UMBRAL_SUBIDA:
                linea = f"  • {nombre}: {anterior} → {stock} unidades (+{subida}){calcular_cajas(subida)}"
                if store_id in TIENDAS_INTERES:
                    principales.append(linea); nombres_p.append(nombre)
                else:
                    otras.append(linea); nombres_o.append(nombre)
                registro["historial"].append({
                    "fecha": now.strftime("%Y-%m-%d"), "hora": now.strftime("%H:%M"),
                    "tienda": nombre, "stock_anterior": anterior,
                    "stock_nuevo": stock, "subida": subida,
                })

    if principales or otras:
        cuerpo = f"Llegó mercancía de Hot Wheels!\nFecha: {now:%d/%m/%Y %H:%M}\n\n"
        if principales:
            cuerpo += "⚠️ SEDES PRINCIPALES:\n" + "\n".join(principales) + "\n\n"
        if otras:
            cuerpo += "🏁 OTRAS SEDES ANTIOQUIA:\n" + "\n".join(otras) + "\n\n"
        cuerpo += f"Compra aquí: {URL_PRODUCTO}"
        partes = []
        if nombres_p:
            partes.append("⚠️ " + ", ".join(nombres_p))
        if nombres_o:
            partes.append("🏁 " + ", ".join(nombres_o))
        enviar_email(" | ".join(partes), cuerpo)
    else:
        print("😴 Sin cambios significativos" if not primera_vez else "📝 Primera ejecución: guardando stock base")

    registro["stock_anterior"] = {str(k): v for k, v in stock_actual.items()}
    guardar_registro(registro)


if __name__ == "__main__":
    main()
