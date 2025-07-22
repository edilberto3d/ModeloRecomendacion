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
    app.logger.info('✅ Modelo de reglas de asociación cargado.')
except Exception as e:
    app.logger.error(f"❌ Error al cargar 'reglas_asociacion.pkl': {e}")
    rules = pd.DataFrame()

def obtener_recomendaciones_avanzadas(productos_carrito, top_n=3):
    if rules.empty or not productos_carrito:
        return []

    carrito_set = frozenset(productos_carrito)
    
    # Estrategia 1: Buscar regla para el carrito completo
    reglas_exactas = rules[rules['antecedents'] == carrito_set]
    if not reglas_exactas.empty:
        recomendaciones_directas = list(reglas_exactas.iloc[0]['consequents'])
        app.logger.info(f"Recomendación por regla exacta encontrada para {list(carrito_set)}: {recomendaciones_directas}")
        return recomendaciones_directas[:top_n]

    # Estrategia 2 (Fallback): Combinar recomendaciones individuales
    recomendaciones_combinadas = []
    for producto in productos_carrito:
        reglas_producto = rules[rules['antecedents'] == frozenset({producto})]
        if not reglas_producto.empty:
            for items in reglas_producto['consequents']:
                recomendaciones_combinadas.extend(list(items))

    if not recomendaciones_combinadas:
        return []

    conteo = Counter(recomendaciones_combinadas)
    for item in productos_carrito:
        if item in conteo:
            del conteo[item]
            
    recomendaciones_finales = [item for item, count in conteo.most_common(top_n)]
    app.logger.info(f"Recomendación por fallback para {productos_carrito}: {recomendaciones_finales}")
    return recomendaciones_finales

@app.route('/recomendar', methods=['POST'])
def recomendar():
    data = request.get_json()
    if not data or 'productos' not in data or not isinstance(data['productos'], list):
        return jsonify({'error': 'Se esperaba un JSON con una lista de productos: {"productos": ["item1", ...]}'}), 400

    recomendaciones = obtener_recomendaciones_avanzadas(data['productos'])
    return jsonify({'recomendaciones': recomendaciones})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)