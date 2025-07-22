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
    # --- CORRECCIÓN CRÍTICA: Pre-procesar los nombres a minúsculas una sola vez al cargar ---
    # Esto crea la columna 'antecedents_lower' que faltaba y hace las búsquedas más rápidas.
    rules['antecedents_lower'] = rules['antecedents'].apply(lambda x: frozenset([item.lower().strip() for item in x]))
    app.logger.info('✅ Modelo de reglas de asociación cargado y pre-procesado.')
except Exception as e:
    app.logger.error(f"❌ Error al cargar 'reglas_asociacion.pkl': {e}")
    rules = pd.DataFrame()

def obtener_recomendaciones_avanzadas(productos_carrito, top_n=8):
    """
    Obtiene las mejores recomendaciones para una lista de productos,
    ignorando mayúsculas/minúsculas y espacios extra.
    """
    if rules.empty or not productos_carrito:
        return []

    # Limpiar la entrada del usuario (minúsculas y sin espacios)
    productos_carrito_limpios = [p.lower().strip() for p in productos_carrito]
    carrito_set_limpio = frozenset(productos_carrito_limpios)
    
    # Estrategia 1: Buscar regla para el carrito completo (usando la columna pre-procesada)
    reglas_exactas = rules[rules['antecedents_lower'] == carrito_set_limpio]
    
    if not reglas_exactas.empty:
        recomendaciones_directas = list(reglas_exactas.iloc[0]['consequents'])
        app.logger.info(f"Recomendación por regla exacta para {productos_carrito}: {recomendaciones_directas}")
        return recomendaciones_directas[:top_n]

    # Estrategia 2 (Fallback): Combinar recomendaciones individuales
    recomendaciones_combinadas = []
    for producto_limpio in productos_carrito_limpios:
        # Se busca en la columna pre-procesada para que la búsqueda sea correcta
        reglas_producto = rules[rules['antecedents_lower'] == frozenset({producto_limpio})]
        if not reglas_producto.empty:
            for items in reglas_producto['consequents']:
                recomendaciones_combinadas.extend(list(items))

    if not recomendaciones_combinadas:
        return []

    conteo = Counter(recomendaciones_combinadas)
    # Eliminar productos que ya están en el carrito de las recomendaciones
    for item_limpio in productos_carrito_limpios:
        original_items = [item for item in conteo if item.lower().strip() == item_limpio]
        for original_item in original_items:
            if original_item in conteo:
                del conteo[original_item]
            
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
