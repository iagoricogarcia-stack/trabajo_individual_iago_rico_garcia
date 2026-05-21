

import matplotlib.pyplot as plt
import networkx as nx
import sqlite3
import random
import os

class RedDistribucion:
    def __init__(self):
        # Listas originales intactas
        self.estaciones = []
        self.tuberias = []
        
        # 1. Averiguamos la ruta EXACTA de la carpeta donde está este script (.py)
        directorio_script = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Definimos el nombre de la carpeta y del archivo
        nombre_carpeta = "BaseDeDatos"
        nombre_archivo = "red_aguas.db"
        
        # 3. Unimos la ruta del script con la nueva carpeta
        
        self.carpeta_bd = os.path.join(directorio_script, nombre_carpeta)
        
        # 4. Unimos la carpeta final con el archivo .db
        self.ruta_bd = os.path.join(self.carpeta_bd, nombre_archivo)


    def agregar_estacion(self, nombre):
        """Añade una nueva estación a la red si no existe."""
        if nombre not in self.estaciones:
            self.estaciones.append(nombre)
            
            self.guardar_en_sqlite()

    def agregar_tuberia(self, origen, destino, costo, capacidad):
        """Añade una tubería dirigida entre dos estaciones."""
        self.agregar_estacion(origen)
        self.agregar_estacion(destino)
        
        self.tuberias.append((origen, destino, costo, capacidad))
       
        self.guardar_en_sqlite()

    def eliminar_estacion(self, nombre):
        """
        Elimina una estación y todas las tuberías conectadas a ella 
        (entrantes y salientes).
        """
        if nombre not in self.estaciones:
            return False

        # 1. Eliminar de la lista de estaciones
        self.estaciones.remove(nombre)

        # 2. Eliminar todas las tuberías donde la estación sea origen o destino
        # Esto evita "tuberías fantasma" que apunten a nodos que ya no existen
        self.tuberias = [tub for tub in self.tuberias if tub[0] != nombre and tub[1] != nombre]

        # 3. Persistir cambios
        self.guardar_en_sqlite()
        return True

    def eliminar_tuberia_por_id(self, id_tuberia):
        """
        Elimina una tubería basándose en su número (N°) de índice en la lista.
        """
        # A los usuarios les mostramos los IDs empezando desde 1,
        # pero las listas de Python empiezan en 0. Por eso restamos 1.
        indice = id_tuberia - 1
        
        # Comprobamos que el ID exista (que no sea negativo ni mayor que el tamaño de la lista)
        if 0 <= indice < len(self.tuberias):
            # pop() saca el elemento de la lista y lo guarda en la variable
            tuberia_eliminada = self.tuberias.pop(indice)
            
            # Guardamos los cambios en la base de datos
            self.guardar_en_sqlite()
            
            # Devolvemos los datos de la tubería borrada para el print del menú
            return tuberia_eliminada
        else:
            return None

    def renombrar_estacion(self, nombre_antiguo, nombre_nuevo):
        """
        Cambia el nombre de una estación y actualiza todas las tuberías 
        que conectaban con ella.
        """
        if nombre_antiguo not in self.estaciones:
            print(f"Error: La estación '{nombre_antiguo}' no existe.")
            return False
        
        if nombre_nuevo in self.estaciones:
            print(f"Error: Ya existe una estación llamada '{nombre_nuevo}'.")
            return False

        # 1. Renombrar en la lista de estaciones
        indice = self.estaciones.index(nombre_antiguo)
        self.estaciones[indice] = nombre_nuevo

        # 2. Actualizar todas las tuberías vinculadas (Origen o Destino)
        # Las tuplas son inmutables, así que creamos una nueva lista
        nuevas_tuberias = []
        for u, v, costo, cap in self.tuberias:
            nuevo_u = nombre_nuevo if u == nombre_antiguo else u
            nuevo_v = nombre_nuevo if v == nombre_antiguo else v
            nuevas_tuberias.append((nuevo_u, nuevo_v, costo, cap))
        
        self.tuberias = nuevas_tuberias
        
        # 3. Persistir cambios
        self.guardar_en_sqlite()
        return True

    def dibujar_grafo_visual(self):
        
        # 1. Crear el objeto grafo dirigido
        grafo_visual = nx.DiGraph()
        
        # 2. Agregar nodos (estaciones)
        for estacion in self.estaciones:
            grafo_visual.add_node(estacion)
            
        # 3. Agregar aristas (tuberías) y crear diccionario de etiquetas
        etiquetas_aristas = {}
        for tuberia in self.tuberias:
            origen = tuberia[0]
            destino = tuberia[1]
            costo = tuberia[2]
            capacidad = tuberia[3]
            
            grafo_visual.add_edge(origen, destino)
            etiquetas_aristas[(origen, destino)] = f"C:{costo}\nCap:{capacidad}L"

        
        plt.figure(figsize=(16, 10)) 

        
        posiciones = nx.spring_layout(grafo_visual, k=3.5, iterations=100, seed=42) 
        
        # Dibujar Nodos 
        nx.draw_networkx_nodes(grafo_visual, posiciones, node_size=1000, node_color="skyblue", edgecolors="black")
        
        # Dibujar Etiquetas de Nodos
        nx.draw_networkx_labels(grafo_visual, posiciones, font_size=10, font_weight="bold")
        

        # Modificamos curvatura de las flechas, tamaño, grosor y color
        nx.draw_networkx_edges(grafo_visual,posiciones,arrowstyle="-|>",arrowsize=35,width=2.0,edge_color="dimgray",connectionstyle="arc3,rad=0.2")
        
        # Creamos un pequeño recuadro blanco alrededor del texto para que la línea no lo tache
        propiedades_caja = dict(boxstyle="round,pad=0.3", ec="white", fc="white", alpha=0.8)

        # 6. Dibujar Etiquetas de Aristas
        nx.draw_networkx_edge_labels(
            grafo_visual, 
            posiciones, 
            edge_labels=etiquetas_aristas, 
            font_color="red", 
            font_size=9, 
            label_pos=0.3,         
            bbox=propiedades_caja, 
            rotate=False           
        )

        plt.title("Mapa Visual Disperso de la Red de Distribución", fontsize=14, fontweight="bold")
        plt.axis("off") 
        plt.margins(0.1) 
        plt.show()

    # MÉTODOS DE BASE DE DATOS 
    
    def configurar_bd(self):
        """Crea la carpeta si no existe y luego las tablas."""
        # Crea la carpeta físicamente en tu disco duro 
        if not os.path.exists(self.carpeta_bd):
            os.makedirs(self.carpeta_bd)
            
        conexion = sqlite3.connect(self.ruta_bd)
        cursor = conexion.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS estaciones (nombre TEXT PRIMARY KEY)")
        cursor.execute("CREATE TABLE IF NOT EXISTS tuberias (origen TEXT, destino TEXT, costo INTEGER, capacidad INTEGER)")
        conexion.commit()
        conexion.close()

    def guardar_en_sqlite(self):
        """Vuelca las listas en la ruta especificada."""
        self.configurar_bd()
        conexion = sqlite3.connect(self.ruta_bd)
        cursor = conexion.cursor()
        
        cursor.execute("DELETE FROM estaciones")
        cursor.execute("DELETE FROM tuberias")
        
        for est in self.estaciones:
            cursor.execute("INSERT INTO estaciones (nombre) VALUES (?)", (est,))
            
        for tub in self.tuberias:
            cursor.execute("INSERT INTO tuberias (origen, destino, costo, capacidad) VALUES (?, ?, ?, ?)", tub)
            
        conexion.commit()
        conexion.close()

    def cargar_desde_sqlite(self):
        """Recupera los datos respetando la nueva ruta."""
        # Evita errores si la carpeta aún no se ha creado 
        if not os.path.exists(self.ruta_bd):
            return 

        conexion = sqlite3.connect(self.ruta_bd)
        cursor = conexion.cursor()
        
        cursor.execute("SELECT nombre FROM estaciones")
        self.estaciones = [fila[0] for fila in cursor.fetchall()]
        
        cursor.execute("SELECT origen, destino, costo, capacidad FROM tuberias")
        self.tuberias = cursor.fetchall()
        
        conexion.close()

    def mostrar_tabla(self):
        """Muestra en consola el reporte formateado (Intacto, solo adaptado a la nueva ruta)."""
        self.cargar_desde_sqlite()
        
        print("\n" + "═" * 65)
        print(" 📋 REPORTE DE BASE DE DATOS: RED DE DISTRIBUCIÓN ")
        print("═" * 65)

        print("\n📍 ESTACIONES REGISTRADAS")
        print("-" * 30)
        if not self.estaciones:
            print(" [ ! ] No hay estaciones en la base de datos.")
        else:
            for i, nombre in enumerate(self.estaciones, 1):
                print(f" {i}. {nombre}")
        
        print("\n💧 TUBERÍAS (CONEXIONES)")
        print("_"*70)
        print(f"{'N°':<4} | {'ORIGEN':<15} | {'DESTINO':<15} | {'COSTE':<7} | {'CAPACIDAD':<10}")
        print("_"*70)
        
        if not self.tuberias:
            print(f"{' ':^65}")
            print(f"{' ( No hay tuberías registradas ) ':^65}")
        else:
            for idx, tub in enumerate(self.tuberias, 1):
                u, v, costo, cap = tub
                print(f"{idx:<4} | {u:<15} | {v:<15} | {costo:<7} | {cap:<10} L/s")
        
        print("_" * 70 + "\n")


class AlgoritmoBellmanFord:
    def __init__(self, red):
        self.red = red

    def _calcular_costo_ciclo(self, ciclo_nodos, caudal_requerido):
        """Suma el costo de las aristas que forman el ciclo para verificar si el balance es negativo."""
        costo_total = 0
        for i in range(len(ciclo_nodos) - 1):
            u = ciclo_nodos[i]
            v = ciclo_nodos[i+1]
            mejor_costo = float('inf')
            
            for tub in self.red.tuberias:
                if tub[0] == u and tub[1] == v and tub[3] >= caudal_requerido:
                    if tub[2] < mejor_costo:
                        mejor_costo = tub[2]
            costo_total += mejor_costo
            
        return costo_total

    def calcular_rutas(self, origen, caudal_requerido):
        """
        Calcula y devuelve DOS diccionarios:
        1. Las rutas óptimas puramente simples (sin repetir estaciones).
        2. Las rutas óptimas aprovechando un ciclo negativo EXACTAMENTE UNA VEZ.
        """
        # 1. INICIALIZACIÓN DE LA DOBLE MEMORIA (Guardamos Costo y Camino Exacto)
        rutas_simples = {est: {'costo': float('inf'), 'camino': []} for est in self.red.estaciones}
        rutas_ciclo = {est: {'costo': float('inf'), 'camino': []} for est in self.red.estaciones}
        
        rutas_simples[origen] = {'costo': 0, 'camino': [origen]}

        # 2. RELAJACIÓN EXPANDIDA (Iteramos 2*V veces para que los ciclos tengan tiempo de expandirse hasta el final)
        total_estaciones = len(self.red.estaciones)
        
        for _ in range(total_estaciones * 2):
            for tuberia in self.red.tuberias:
                u = tuberia[0]
                v = tuberia[1]
                costo = tuberia[2]
                capacidad = tuberia[3]
                
                if capacidad < caudal_requerido:
                    continue

                # --- A. INTENTAR EXPANDIR RUTAS SIMPLES ---
                if rutas_simples[u]['costo'] != float('inf'):
                    
                    if v not in rutas_simples[u]['camino']:
                        # Es un camino simple válido (no repite estaciones)
                        nuevo_costo = rutas_simples[u]['costo'] + costo
                        if nuevo_costo < rutas_simples[v]['costo']:
                            rutas_simples[v] = {'costo': nuevo_costo, 'camino': rutas_simples[u]['camino'] + [v]}
                    else:
                        # Intenta repetir estación -> Significa que hemos formado un ciclo.
                        # Lo extraemos y calculamos su coste.
                        indice_v = rutas_simples[u]['camino'].index(v)
                        ciclo = rutas_simples[u]['camino'][indice_v:] + [v]
                        costo_ciclo = self._calcular_costo_ciclo(ciclo, caudal_requerido)
                        
                        if costo_ciclo < 0:
                            # ¡Premio! Es un ciclo negativo. Abrimos la dimensión de "rutas_ciclo"
                            nuevo_costo = rutas_simples[u]['costo'] + costo
                            if nuevo_costo < rutas_ciclo[v]['costo']:
                                rutas_ciclo[v] = {'costo': nuevo_costo, 'camino': rutas_simples[u]['camino'] + [v]}

                # --- B. INTENTAR EXPANDIR RUTAS QUE YA USARON UN CICLO NEGATIVO ---
                if rutas_ciclo[u]['costo'] != float('inf'):
                    # ESCUDO ANTI-BUCLES INFINITOS: 
                    # Solo permitimos avanzar si el nodo 'v' NO ha sido pisado antes en este camino.
                    # Esto garantiza que el ciclo negativo se usa "una única vez" y continuamos ruta.
                    if v not in rutas_ciclo[u]['camino']:
                        nuevo_costo = rutas_ciclo[u]['costo'] + costo
                        if nuevo_costo < rutas_ciclo[v]['costo']:
                            rutas_ciclo[v] = {'costo': nuevo_costo, 'camino': rutas_ciclo[u]['camino'] + [v]}

        # Devolvemos los dos estados al Simulador
        return rutas_simples, rutas_ciclo

class Simulador:
    def __init__(self):
        self.red = RedDistribucion()
        self.analizador = AlgoritmoBellmanFord(self.red)
        self.red.cargar_desde_sqlite()

    def iniciar(self):
        while True:

            # Ancho total del menú
            ancho = 65
            
            print("\n" + "╔" + "═" * (ancho - 2) + "╗")
            print("║" + "💧 SIMULADOR DE REDES DE DISTRIBUCIÓN 💧".center(ancho - 4) + "║")
            print("╠" + "═" * (ancho - 2) + "╣")
            
            # Categoría: Visualización
            print("║ " + "[ VISUALIZACIÓN Y CÁLCULO ]".ljust(ancho - 3) + "║")
            print("║ " + "  1. Mostrar topología de la red".ljust(ancho - 3) + "║")
            print("║ " + "  2. Calcular ruta óptima de suministro".ljust(ancho - 3) + "║")
            print("║" + " " * (ancho - 2) + "║") # Fila vacía separadora
            
            # Categoría: Gestión
            print("║ " + "[ GESTIÓN DE LA RED ]".ljust(ancho - 3) + "║")
            print("║ " + "  3. Agregar una nueva estación".ljust(ancho - 3) + "║")
            print("║ " + "  4. Agregar una nueva tubería".ljust(ancho - 3) + "║")
            print("║ " + "  5. Eliminar una estación".ljust(ancho - 3) + "║")
            print("║ " + "  6. Eliminar una tubería".ljust(ancho - 3) + "║")
            print("║ " + "  7. Renombrar una estación".ljust(ancho - 3) + "║")
            print("║" + " " * (ancho - 2) + "║") # Fila vacía separadora
            
            # Categoría: Sistema
            print("║ " + "[ SISTEMA ]".ljust(ancho - 3) + "║")
            print("║ " + "  8. Salir del simulador".ljust(ancho - 3) + "║")
            
            print("╚" + "═" * (ancho - 2) + "╝")

            
            opcion = input("Elige una opción: ")

            if opcion == "1":
                self.red.mostrar_tabla()
                self.red.dibujar_grafo_visual()

            elif opcion == "2":
                self._menu_calcular()

            elif opcion == "3":
                nombre = input("Dime el nombre de la estación a agregar:")
                self.red.agregar_estacion(nombre)
                print(f"La estación {nombre} correctamente")

            elif opcion == "4":
                origen = input("Dime el nombre de la estación de origen:").strip()
                destino = input("Dime el nombre de la estación de destino:").strip()
                coste = random.randint(-10, 10)
                capacidad = random.randrange(10,150,10)
                self.red.agregar_tuberia(origen, destino , coste, capacidad )
                print(f"La tubería de la estación {origen} a la estación {destino} con un coste de {coste} y de capacidad {capacidad} correctamente")

            elif opcion == "5": 
                nombre = input("Nombre de la estación a ELIMINAR: ").strip()
                confirmar = input(f" ¿Seguro que quieres borrar '{nombre}' y sus tuberías? (s/n): ").lower()
                if confirmar == 's':
                    if self.red.eliminar_estacion(nombre):
                        print(f" Estación '{nombre}' y sus conexiones eliminadas.")
                    else:
                        print(f"La estación '{nombre}' no existe.")

            elif opcion == "6":  
                # 1. Mostramos la tabla para que el usuario vea los N° (IDs)
                self.red.mostrar_tabla()
                
                # 2. Pedimos el ID
                try:
                    id_borrar = int(input("Dime el N° (ID) de la tubería que quieres borrar: ").strip())
                except ValueError:
                    print(" Error: Debes introducir un número entero.")
                    continue
                
                # 3. Llamamos a nuestra nueva función
                tuberia_borrada = self.red.eliminar_tuberia_por_id(id_borrar)
                
                # 4. Comprobamos el resultado
                if tuberia_borrada:
                    # Desempaquetamos la tupla borrada para hacer un mensaje bonito
                    origen, destino, costo, cap = tuberia_borrada
                    print(f"La tubería N°{id_borrar} (que iba de '{origen}' a '{destino}') ha sido eliminada correctamente.")
                else:
                    print(f"Error: No existe ninguna tubería con el N° {id_borrar}.")

            elif opcion == "7": # Renombrar
                try: 
                     antiguo = input("Nombre de la estación a renombrar: ").strip()
                     nuevo = input("Nuevo nombre para la estación: ").strip()
                except KeyboardInterrupt:
                    print(" Error: No has introducido bien el nombre.")
                    continue

                if antiguo and nuevo:
                    if self.red.renombrar_estacion(antiguo, nuevo):
                        print(f" Estación '{antiguo}' renombrada a '{nuevo}' correctamente.")
                else:
                    print(" Los nombres no pueden estar vacíos.")
                
            elif opcion == "8":
                print("Cerrando el simulador...")
                break
        
            else:
                print("Opción inválida.")

    def _menu_calcular(self):
        print("\nNodos disponibles:", ", ".join(self.red.estaciones))
        origen = input("Introduce la estación de origen : ").strip()
        destino = input("Introduce la estación de destino : ").strip()
        
        if origen not in self.red.estaciones or destino not in self.red.estaciones:
            print("Error: Una de las estaciones no existe en la red.")
            return

        try:
            caudal = int(input("¿Qué caudal (L/s) necesitas transportar?: ").strip())
        except ValueError:
            print("Por favor, introduce un número entero para el caudal.")
            return

      # Ejecutamos nuestra versión avanzada de Bellman-Ford
        rutas_simples, rutas_ciclo = self.analizador.calcular_rutas(origen, caudal)

        print(f"\n ANÁLISIS DE RUTAS DE {origen} A {destino} (Caudal: {caudal} L/s)")
        print("="*65)

        # 1. EXTRAER RUTA SIMPLE
        coste_simple = rutas_simples[destino]['costo']
        camino_simple = rutas_simples[destino]['camino']

        if coste_simple == float('inf'):
            print(" RUTA 1 (Simple): Imposible llegar físicamente al destino.")
        else:
            print(f" RUTA 1 (Estándar): {' -> '.join(camino_simple)}")
            print(f"   Coste de operación: {coste_simple}")

        print("-" * 65)

        # 2. EXTRAER RUTA CON CICLO NEGATIVO
        coste_ciclo = rutas_ciclo[destino]['costo']
        camino_ciclo = rutas_ciclo[destino]['camino']

        if coste_ciclo == float('inf'):
            print(" RUTA 2 (Con Ciclo Negativo): No existe ninguna anomalía topológica a favor en esta red.")
        else:
            print(f" RUTA 2 (Ciclo Negativo 1 vez): {' -> '.join(camino_ciclo)}")
            print(f"   Coste de operación (Mejorado): {coste_ciclo}")
            
            # Cálculo de la ganancia
            if coste_simple != float('inf'):
                ahorro = coste_simple - coste_ciclo
                print(f"   (Ahorraste {ahorro} de coste respecto a la ruta estándar)")

# ================= EJECUCIÓN =================
if __name__ == "__main__":
    app = Simulador()
    app.iniciar()
 
