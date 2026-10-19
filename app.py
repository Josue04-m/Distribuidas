

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
      server = os.environ["DB_SEERVER"],
      database = os.environ["DB_DATABASE"],
      user = os.environ["DB_USER"],
      password = os.environ["DB_PASS"],
      port = 1433,
      cafile= certifi.where(),
      validate_host = True
      
      )

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