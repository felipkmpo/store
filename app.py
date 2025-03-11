from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///supermercado.db'
db = SQLAlchemy(app)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    precio_compra = db.Column(db.Float, nullable=False)
    precio_venta = db.Column(db.Float, nullable=False)
    stock_disponible = db.Column(db.Integer, nullable=False)
    proveedor = db.Column(db.String(100), nullable=False)
    umbral_alerta = db.Column(db.Integer, nullable=False, default=5)

'''class MovimientoInventario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    tipo_movimiento = db.Column(db.String(10), nullable=False)  # entrada/salida
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
'''

class MovimientoInventario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    producto = db.relationship('Producto', backref='movimientos', lazy=True)  # Relación con Producto
    tipo_movimiento = db.Column(db.String(10), nullable=False)  # entrada/salida
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())



class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    producto = db.relationship('Producto', backref='ventas', lazy=True)  # Relación con Producto
    cantidad_vendida = db.Column(db.Integer, nullable=False)
    fecha_venta = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    precio_venta_unitario = db.Column(db.Float, nullable=False)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/productos')
def productos():
    productos = Producto.query.all()
    return render_template('productos/lista_productos.html', productos=productos)

@app.route('/productos/agregar', methods=['GET', 'POST'])
def agregar_producto():
    if request.method == 'POST':
        nuevo_producto = Producto(
            nombre=request.form['nombre'],
            categoria=request.form['categoria'],
            precio_compra=float(request.form['precio_compra']),
            precio_venta=float(request.form['precio_venta']),
            stock_disponible=int(request.form['stock_disponible']),
            proveedor=request.form['proveedor']
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        return redirect(url_for('productos'))  # Redirige a la lista de productos
    return render_template('productos/agregar_producto.html')


'''@app.route('/movimientos', methods=['GET', 'POST'])
def movimientos():
    if request.method == 'POST':
        nuevo_movimiento = MovimientoInventario(
            producto_id=int(request.form['producto_id']),
            tipo_movimiento=request.form['tipo_movimiento'],
            cantidad=int(request.form['cantidad'])
        )
        db.session.add(nuevo_movimiento)
        db.session.commit()
        return redirect(url_for('movimientos'))
    movimientos = MovimientoInventario.query.all()
    productos = Producto.query.all()
    return render_template('movimientos.html', movimientos=movimientos, productos=productos)
'''

@app.route('/movimientos')
def movimientos():
    movimientos = MovimientoInventario.query.all()
    
    # Para mostrar el nombre del producto en el historial
    movimientos_con_producto = []
    for movimiento in movimientos:
        producto = Producto.query.get(movimiento.producto_id)
        movimiento_con_producto = {
            'id': movimiento.id,
            'producto_nombre': producto.nombre,
            'tipo_movimiento': movimiento.tipo_movimiento,
            'cantidad': movimiento.cantidad,
            'fecha': movimiento.fecha
        }
        movimientos_con_producto.append(movimiento_con_producto)
    
    return render_template('movimientos.html', movimientos=movimientos_con_producto)


@app.route('/alertas')
def alertas():
    productos = Producto.query.all()
    alertas = [p for p in productos if p.stock_disponible < p.umbral_alerta]
    return render_template('alertas.html', alertas=alertas)

@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    if request.method == 'POST':
        productos_ids = request.form.getlist('producto_id')
        cantidades_vendidas = request.form.getlist('cantidad_vendida')
        dinero_recibido = float(request.form['dinero_recibido'])

        total_venta = 0
        for producto_id, cantidad_vendida in zip(productos_ids, cantidades_vendidas):
            producto_id = int(producto_id)
            cantidad_vendida = int(cantidad_vendida)
            producto = Producto.query.get(producto_id)

            if producto and producto.stock_disponible >= cantidad_vendida:
                total_venta += producto.precio_venta * cantidad_vendida
                nueva_venta = Venta(
                    producto_id=producto_id,
                    cantidad_vendida=cantidad_vendida,
                    precio_venta_unitario=producto.precio_venta
                )
                db.session.add(nueva_venta)

                nuevo_movimiento = MovimientoInventario(
                    producto_id=producto_id,
                    tipo_movimiento='salida',
                    cantidad=cantidad_vendida,
                    fecha=datetime.now()
                )
                db.session.add(nuevo_movimiento)

                producto.stock_disponible -= cantidad_vendida
            else:
                return f"No hay suficiente stock para el producto: {producto.nombre}."

        db.session.commit()
        devuelta = dinero_recibido - total_venta
        return render_template('resumen_venta.html', total_venta=total_venta, dinero_recibido=dinero_recibido, devuelta=devuelta)

    productos = Producto.query.all()
    ventas = Venta.query.all()

    # Incluir el nombre del producto y el total de la venta en la lista de ventas
    ventas_con_producto = []
    for venta in ventas:
        producto = Producto.query.get(venta.producto_id)
        total_venta = venta.precio_venta_unitario * venta.cantidad_vendida
        ganancia_venta = (venta.precio_venta_unitario - producto.precio_compra) * venta.cantidad_vendida if producto else 0 # Cálculo de ganancia

        ventas_con_producto.append({
            'id': venta.id,
            'producto_nombre': producto.nombre if producto else "Producto eliminado",
            'cantidad_vendida': venta.cantidad_vendida,
            'fecha_venta': venta.fecha_venta,
            'total_venta': total_venta,  # Nuevo campo
            'ganancia_venta': ganancia_venta  #Nuevo campo
        })

    return render_template('ventas2.html', productos=productos, ventas=ventas_con_producto)



'''@app.route('/ganancias')
def ganancias():
    productos = Producto.query.all()
    ventas = Venta.query.all()
    
    # Cálculo de ganancias por producto
    ganancias_por_producto = {}
    for producto in productos:
        ganancia_total = 0
        for venta in ventas:
            if venta.producto_id == producto.id:
                ganancia_total += (venta.precio_venta_unitario - producto.precio_compra) * venta.cantidad_vendida
        ganancias_por_producto[producto.nombre] = ganancia_total
    
    # Cálculo de ganancias por período de tiempo
    ganancias_diarias = {}
    ganancias_semanales = {}
    ganancias_mensuales = {}
    
    from datetime import datetime, timedelta
    hoy = datetime.now()
    ayer = hoy - timedelta(days=1)
    semana_pasada = hoy - timedelta(days=7)
    mes_pasado = hoy - timedelta(days=30)
    
    for venta in ventas:
        fecha_venta = venta.fecha_venta
        if fecha_venta > ayer:
            if fecha_venta.strftime('%Y-%m-%d') not in ganancias_diarias:
                ganancias_diarias[fecha_venta.strftime('%Y-%m-%d')] = 0
            producto = Producto.query.get(venta.producto_id)
            ganancias_diarias[fecha_venta.strftime('%Y-%m-%d')] += (venta.precio_venta_unitario - producto.precio_compra) * venta.cantidad_vendida
        
        if fecha_venta > semana_pasada:
            if fecha_venta.strftime('%Y-%W') not in ganancias_semanales:
                ganancias_semanales[fecha_venta.strftime('%Y-%W')] = 0
            producto = Producto.query.get(venta.producto_id)
            ganancias_semanales[fecha_venta.strftime('%Y-%W')] += (venta.precio_venta_unitario - producto.precio_compra) * venta.cantidad_vendida
        
        if fecha_venta > mes_pasado:
            if fecha_venta.strftime('%Y-%m') not in ganancias_mensuales:
                ganancias_mensuales[fecha_venta.strftime('%Y-%m')] = 0
            producto = Producto.query.get(venta.producto_id)
            ganancias_mensuales[fecha_venta.strftime('%Y-%m')] += (venta.precio_venta_unitario - producto.precio_compra) * venta.cantidad_vendida
    
    return render_template('ganancias.html', ganancias_por_producto=ganancias_por_producto, 
                           ganancias_diarias=ganancias_diarias, ganancias_semanales=ganancias_semanales, 
                           ganancias_mensuales=ganancias_mensuales)
'''
@app.route('/ganancias', methods=['GET'])
def ganancias():
    fecha_str = request.args.get('fecha')
    fecha_seleccionada = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else datetime.now().date()
    
    productos = Producto.query.all()
    ventas = Venta.query.all()
    
    # Cálculo de ganancias por producto
    ganancias_por_producto = {}

    for producto in productos:
        cantidad_total = sum(venta.cantidad_vendida for venta in ventas if venta.producto_id == producto.id)
        ganancia_total = sum(
            (venta.precio_venta_unitario - producto.precio_compra) * venta.cantidad_vendida
            for venta in ventas if venta.producto_id == producto.id
        )
        ganancias_por_producto[producto.nombre] = {
            "cantidad_vendida": cantidad_total,
            "ganancia": ganancia_total
        }
    
    # Cálculo de ganancias diarias corregido
    ganancias_diarias = {}
    for venta in ventas:
        try:
            fecha_venta = datetime.strptime(venta.fecha_venta, "%Y-%m-%d %H:%M:%S").date()  # Convertir a objeto datetime
        except TypeError:
            fecha_venta = venta.fecha_venta.date()  # Si ya es datetime, tomar solo la fecha
        
        if fecha_venta == fecha_seleccionada:
            producto = Producto.query.get(venta.producto_id)
            if producto:
                ganancia = (venta.precio_venta_unitario - producto.precio_compra) * venta.cantidad_vendida
                ganancias_diarias[fecha_seleccionada.strftime('%Y-%m-%d')] = ganancias_diarias.get(fecha_seleccionada.strftime('%Y-%m-%d'), 0) + ganancia

    # Cálculo de ganancias semanales y mensuales (sin cambios)
    ganancias_semanales = {}
    ganancias_mensuales = {}

    hoy = datetime.now()
    semana_pasada = hoy - timedelta(days=7)
    mes_pasado = hoy - timedelta(days=30)

    for venta in ventas:
        fecha_venta = venta.fecha_venta
        if fecha_venta > semana_pasada:
            if fecha_venta.strftime('%Y-%W') not in ganancias_semanales:
                ganancias_semanales[fecha_venta.strftime('%Y-%W')] = 0
            producto = Producto.query.get(venta.producto_id)
            ganancias_semanales[fecha_venta.strftime('%Y-%W')] += (venta.precio_venta_unitario - producto.precio_compra) * venta.cantidad_vendida
        
        if fecha_venta > mes_pasado:
            if fecha_venta.strftime('%Y-%m') not in ganancias_mensuales:
                ganancias_mensuales[fecha_venta.strftime('%Y-%m')] = 0
            producto = Producto.query.get(venta.producto_id)
            ganancias_mensuales[fecha_venta.strftime('%Y-%m')] += (venta.precio_venta_unitario - producto.precio_compra) * venta.cantidad_vendida
    
    return render_template(
        'ganancias.html',
        ganancias_por_producto=ganancias_por_producto,
        ganancias_diarias=ganancias_diarias,
        ganancias_semanales=ganancias_semanales,
        ganancias_mensuales=ganancias_mensuales,
        fecha_seleccionada=fecha_seleccionada
    )


@app.route('/editar_producto/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    producto = Producto.query.get(id)
    
    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.categoria = request.form['categoria']
        producto.precio_compra = float(request.form['precio_compra'])
        producto.precio_venta = float(request.form['precio_venta'])
        producto.stock_disponible = int(request.form['stock_disponible'])
        producto.proveedor = request.form['proveedor']
        producto.umbral_alerta = int(request.form['umbral_alerta'])
        
        db.session.commit()
        return redirect(url_for('productos'))
    
    return render_template('editar_producto.html', producto=producto)

@app.route('/agregar_stock/<int:id>', methods=['GET', 'POST'])
def agregar_stock(id):
    producto = Producto.query.get(id)
    
    if request.method == 'POST':
        cantidad_a_agregar = int(request.form['cantidad_a_agregar'])
        producto.stock_disponible += cantidad_a_agregar
         # Registrar movimiento de inventario (entrada)
        nuevo_movimiento = MovimientoInventario(
            producto_id=producto.id,
            tipo_movimiento='entrada',
            cantidad=cantidad_a_agregar,
            fecha=datetime.now()
        )
        db.session.add(nuevo_movimiento)

        db.session.commit()
        return redirect(url_for('productos'))
    
    return render_template('agregar_stock.html', producto=producto)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
