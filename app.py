# app.py (versión final y correcta)
from flask import Flask, request, jsonify
import pickle
import pandas as pd
from collections import Counter
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

try:
    with open('reglas_asociacion.pkl', 'rb') as f:
        rules = pickle.load(f)
    # Pre-procesar los nombres a minúsculas y sin espacios para búsquedas eficientes
    rules['antecedents_lower'] = rules['antecedents'].apply(lambda x: frozenset([str(item).lower().strip() for item in x]))
    app.logger.info('✅ Modelo de reglas de asociación cargado y pre-procesado.')
except Exception as e:
    app.logger.error(f"❌ Error al cargar 'reglas_asociacion.pkl': {e}")
    rules = pd.DataFrame()

def obtener_recomendaciones_avanzadas(productos_carrito, top_n=8):
    """
    Obtiene las mejores recomendaciones para una lista de productos,
    ordenando por CONFIANZA.
    """
    if rules.empty or not productos_carrito:
        return []

    productos_carrito_limpios = [str(p).lower().strip() for p in productos_carrito]
    carrito_set_limpio = frozenset(productos_carrito_limpios)
    
    # Estrategia 1: Buscar regla para el carrito completo
    reglas_exactas = rules[rules['antecedents_lower'] == carrito_set_limpio].sort_values(by='confidence', ascending=False)
    
    if not reglas_exactas.empty:
        recomendaciones_directas = list(reglas_exactas.iloc[0]['consequents'])
        app.logger.info(f"Recomendación por regla exacta para {productos_carrito}: {recomendaciones_directas}")
        return recomendaciones_directas[:top_n]

    # --- LÓGICA DE FALLBACK CORREGIDA ---
    # Estrategia 2: Combinar y ordenar por confianza
    
    candidatos_df = pd.DataFrame()
    for producto_limpio in productos_carrito_limpios:
        reglas_producto = rules[rules['antecedents_lower'] == frozenset({producto_limpio})]
        if not reglas_producto.empty:
            candidatos_df = pd.concat([candidatos_df, reglas_producto])

    if candidatos_df.empty:
        return []

    # "Explotar" los consecuentes para tener una fila por cada producto recomendado
    candidatos_df = candidatos_df.explode('consequents')
    
    # Eliminar recomendaciones que ya están en el carrito
    # Convertimos a minúsculas para una comparación segura
    candidatos_df['consequents_lower'] = candidatos_df['consequents'].str.lower().str.strip()
    candidatos_df = candidatos_df[~candidatos_df['consequents_lower'].isin(productos_carrito_limpios)]
    
    # --- PASO CLAVE: Ordenar por confianza ---
    candidatos_df = candidatos_df.sort_values(by='confidence', ascending=False)
    
    # Eliminar productos recomendados duplicados, manteniendo solo el de mayor confianza (porque ya está ordenado)
    recomendaciones_finales = candidatos_df.drop_duplicates(subset=['consequents_lower'])['consequents'].tolist()
    
    app.logger.info(f"Recomendación por fallback para {productos_carrito}: {recomendaciones_finales[:top_n]}")
    return recomendaciones_finales[:top_n]

@app.route('/recomendar', methods=['POST'])
def recomendar():
    data = request.get_json()
    if not data or 'productos' not in data or not isinstance(data['productos'], list):
        return jsonify({'error': 'Se esperaba un JSON con una lista de productos: {"productos": ["item1", ...]}'}), 400

    recomendaciones = obtener_recomendaciones_avanzadas(data['productos'])
    return jsonify({'recomendaciones': recomendaciones})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
