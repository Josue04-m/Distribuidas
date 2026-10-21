import html
import hmac
import re
import requests

import time
import threading

product_lock = threading.Lock()

from flask import Flask, jsonify, request
import os
import certifi
import pytds

#Conexion con la base de datos

app  = Flask(__name__)
def getConnection():
   return pytds.connect(
      server = os.environ["DB_SERVER"],
      database = os.environ["DB_DATABASE"],
      user = os.environ["DB_USER"],
      password = os.environ["DB_PASS"],
      port = 1433,
      cafile= certifi.where(),
      validate_host = True,
      row_strategy = pytds.namedtuple_row_strategy #Agregar esta linea 
      
      )

def enviar_correo(proceso, detalle, destinatario):
    api_key = os.environ["BREVO_API_KEY"]
    remitente = os.environ["EMAIL_REMITENTE"]

    respuesta = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        json={
            "sender": {
                "name": "Catálogo de productos",
                "email": remitente,
            },
            "to": [{"email": destinatario}],
            "subject": proceso,
            "htmlContent": detalle,
        },
        timeout=20,
    )

    if not respuesta.ok:
        raise RuntimeError(
            f"Brevo respondió con HTTP {respuesta.status_code}: "
            f"{respuesta.text[:500]}"
        )

@app.route("/api/procesar", methods=["POST"])
def procesar_catalogo():
    clave_configurada = os.environ.get("PROCESS_API_KEY", "")
    clave_recibida = request.headers.get("X-API-Key", "")

    if (
        not clave_configurada
        or not clave_recibida
        or not hmac.compare_digest(clave_recibida, clave_configurada)
    ):
        return jsonify({"message": "No autorizado"}), 401

    datos = request.get_json(silent=True) or {}
    destinatario = datos.get("email", "").strip()

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", destinatario):
        return jsonify({"message": "Ingresa un correo válido"}), 400

    conexion = None
    cursor = None

    try:
        conexion = getConnection()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, name, price, stock FROM products_vm"
        )
        productos = cursor.fetchall()

        if not productos:
            return jsonify({"message": "No hay productos para enviar"}), 404

        filas_html = ""

        for producto in productos:
            nombre = html.escape(str(producto.name or "Sin nombre"))
            precio = html.escape(f"{producto.price or 0:.2f}")
            stock = html.escape(str(producto.stock or 0))

            filas_html += (
                f"<tr><td>{nombre}</td>"
                f"<td>${precio}</td>"
                f"<td>{stock} unidades</td></tr>"
            )

        contenido = f"""
        <h2>Catálogo de productos</h2>
        <p>Estos son los productos disponibles:</p>
        <table border="1" cellpadding="8" cellspacing="0">
            <thead>
                <tr><th>Producto</th><th>Precio</th><th>Stock</th></tr>
            </thead>
            <tbody>{filas_html}</tbody>
        </table>
        """

        enviar_correo(
            "Catálogo de productos",
            contenido,
            destinatario,
        )

        return jsonify({"message": "Catálogo enviado correctamente"}), 200

    except Exception as error:
        app.logger.exception("Error al procesar y enviar el catálogo")
        return jsonify({
            "message": "No se pudo enviar el catálogo",
            "error": str(error),
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()

@app.route('/test-db', methods=['GET'])
def test_db():
    try:
        conn = getConnection()
        cursor = conn.cursor()

        cursor.execute("SELECT DB_NAME()")
        database = cursor.fetchone()[0]
        conn.close()

        return jsonify(
            {
                "message": "Conexión exitosa a la base de datos", 
                "base de datos": database
            }
        ), 200
    
    except Exception as e:
        return jsonify({"message": "Error al conectar a la base de datos", "error": str(e)}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = getConnection()
        cursor = conn.cursor()

        cursor.execute(""" SELECT id, name, price, stock, version FROM products_vm """)
        products = []
        for row in cursor.fetchall():
            products.append({
                "id" : row.id,
                "name" : row.name,
                "price" : row.price,
                "stock" : row.stock,
                "version" : row.version
            })

        return jsonify(products), 200
    

    except Exception as e:
        return jsonify({
            "message": "Error al obtener los productos", 
            "error": str(e)
            }), 500


@app.route('/api/products/<int:id>', methods=['GET'])
def get_product(id):
    try:
        conn = getConnection()
        cursor = conn.cursor()

        cursor.execute(""" SELECT id, name, price, stock, version FROM vistaProductos WHERE id = ? """, (id,))
        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if row:
            return jsonify({
                "id" : row.id,
                "name" : row.name,
                "price" : row.price,
                "stock" : row.stock,
                "version" : row.version
            }), 200

    except Exception as e:
        return jsonify({
            "message": "Error al obtener el producto", 
            "error": str(e)
            }
        ), 404


#sp
@app.route('/api/products', methods=['POST'])
def create_product():
    try:
        data = request.get_json()

        if not data :
            return jsonify({
                "message": "Datos inválidos"
            }), 400

        name = data.get('name')
        price = data.get('price')
        stock = data.get('stock')

        if not name or not price or not stock:
            return jsonify({
                "message": "Datos incompletos"
            }), 400

        conn = getConnection()
        cursor = conn.cursor()

        cursor.execute("EXEC PRODUCTOS_INSERT_SP ?, ?, ?", (name, price, stock))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Producto creado exitosamente"
        }), 201

    except Exception as e:
        return jsonify({
            "message": "Error al crear el producto", 
            "error": str(e)

        }),500

##################UPDATE####################}
###SIN CONTROLL
@app.route("/api/products", methods=["PUT"])
def update_product():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "message": "Sin data"
            }), 400

        conn = getConnection()
        cursor = conn.cursor()

        time.sleep(5)

        cursor.execute(
            """
            UPDATE PRODUCTS
            SET name = ?, price = ?, stock = ?
            WHERE id = ?
            """,
            (
                data.get("name"),
                data.get("price"),
                data.get("stock"),
                data.get("id"),
                data.get("version")
            )
        )

        if cursor.rowcount == 0:
            conn.rollback()
            cursor.close()
            conn.close()

            return jsonify({
                "message": "Producto no encontrado"
            }), 404

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Producto actualizado exitosamente"
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Error al actualizar el producto",
            "error": str(e)
        }), 500

@app.route("/api/products/lock", methods=["PUT"])
def update_lock():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "message " : "Sin data",
                "error" :str(e)
            }),400


        with product_lock:
            print("Entra al Bloqueo")
            conn = conn.getConnection()
            cursor = conn.cursor()

            time.sleep(3)
            cursor.execute("UPDATE PRODUCTS SET name = ?, price = ?, stock = ? WHERE id = ?", 
                           (data.get("name"), data.get("price"), data.get("stock"), data.get("id")))
            if cursor.rowcount == 0:
                conn.rollback()
                cursor.close()
                conn.close()

                return jsonify({
                    "message": "Registro no encontrado"
                }), 404
            
            conn.commit()
            cursor.close()
            print("Sale del Bloqueo")
        return jsonify({
            "message": "Producto actualizado exitosamente"
        }), 200



    except Exception as e:
        return jsonify({
            "message": "Error al actualizar el producto",
            "error": str(e)
        })

@app.route("/api/products/version", methods=["PUT"])
def update_product_lock():
    try:
        data = get_json()

        if not data:
            return jsonify({
                "message": "Sin data"
            }), 400
        
        if data.get("version") is None :
            return jsonify({
                "message": "Falta parametro (version)"
            }), 400

        conn = getConnection()
        cursor = conn.cursor()

        cursor.execute("UPDATE PRODUCTS SET name = ?, price = ?, stock = ?, version = version + 1 WHERE id = ? AND version = ?",
                       (data.get("name"), data.get("price"), data.get("stock"), data.get("id"), data.get("version")))

        
        if cursor.rowcount == 0:
            cursor.execute("SELECT version FROM PRODUCTS WHERE id = ?", (data.get("id"),))
            row = cursor.fetchone()
            conn.rollback()
            cursor.close()
            conn.close()

            if row:
                productoActual = {
                    "id" : data.get("id"),
                    "version" : row.version
                }

                return jsonify({
                    "message" : "Ya actualizaron este producto",
                    "error" : productoActual
                })
            else :
                return jsonify({
                    "message": "Registro no encontrado"
                }), 404
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message" : "Producto Actualizado exitosamente"
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Error al actualizar el producto",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(
        host='0.0.0.0', port=5000, debug=True
    )