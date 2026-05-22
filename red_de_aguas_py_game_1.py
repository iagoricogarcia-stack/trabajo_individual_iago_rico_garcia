import matplotlib.pyplot as plt
import networkx as nx
import sqlite3
import random
import os
import pygame
import math

# =========================================================================
# 1. MODELO DE DATOS Y PERSISTENCIA (MÉTODOS INTACTOS CON AUTOGUARDADO)
# =========================================================================

class RedDistribucion:
    def __init__(self):
        self.estaciones = []
        self.tuberias = []
        directorio_script = os.path.dirname(os.path.abspath(__file__))
        nombre_carpeta = "BaseDeDatos"
        nombre_archivo = "red_aguas.db"
        self.carpeta_bd = os.path.join(directorio_script, nombre_carpeta)
        self.ruta_bd = os.path.join(self.carpeta_bd, nombre_archivo)

    def agregar_estacion(self, nombre):
        if nombre not in self.estaciones:
            self.estaciones.append(nombre)
            self.guardar_en_sqlite()

    def agregar_tuberia(self, origen, destino, costo, capacidad):
        self.agregar_estacion(origen)
        self.agregar_estacion(destino)
        self.tuberias.append((origen, destino, costo, capacidad))
        self.guardar_en_sqlite()

    def eliminar_tuberia_por_id(self, id_tuberia):
        indice = id_tuberia - 1
        if 0 <= indice < len(self.tuberias):
            tuberia_eliminada = self.tuberias.pop(indice)
            self.guardar_en_sqlite()
            return tuberia_eliminada
        return None

    def eliminar_tuberia(self, origen, destino, costo):
        """Elimina una tubería específica buscando coincidencia de origen, destino y costo."""
        longitud_original = len(self.tuberias)
        self.tuberias = [tub for tub in self.tuberias if not (tub[0] == origen and tub[1] == destino and tub[2] == costo)]
        if len(self.tuberias) < longitud_original:
            self.guardar_en_sqlite()
            return True
        return False

    def renombrar_estacion(self, nombre_antiguo, nombre_nuevo):
        if nombre_antiguo in self.estaciones:
            indice = self.estaciones.index(nombre_antiguo)
            self.estaciones[indice] = nombre_nuevo
            nuevas_tuberias = []
            for u, v, costo, cap in self.tuberias:
                nuevo_u = nombre_nuevo if u == nombre_antiguo else u
                nuevo_v = nombre_nuevo if v == nombre_antiguo else v
                nuevas_tuberias.append((nuevo_u, nuevo_v, costo, cap))
            self.tuberias = nuevas_tuberias
            self.guardar_en_sqlite()

    def guardar_en_sqlite(self):
        if not os.path.exists(self.carpeta_bd):
            os.makedirs(self.carpeta_bd)
        conn = sqlite3.connect(self.ruta_bd)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS estaciones")
        cursor.execute("DROP TABLE IF EXISTS tuberias")
        cursor.execute("CREATE TABLE estaciones (nombre TEXT)")
        cursor.execute("CREATE TABLE tuberias (origen TEXT, destino TEXT, costo INTEGER, capacidad INTEGER)")
        for est in self.estaciones:
            cursor.execute("INSERT INTO estaciones VALUES (?)", (est,))
        for tub in self.tuberias:
            cursor.execute("INSERT INTO tuberias VALUES (?, ?, ?, ?)", tub)
        conn.commit()
        conn.close()

    def cargar_desde_sqlite(self):
        if not os.path.exists(self.ruta_bd):
            return
        conn = sqlite3.connect(self.ruta_bd)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM estaciones")
        self.estaciones = [fila[0] for fila in cursor.fetchall()]
        cursor.execute("SELECT origen, destino, costo, capacidad FROM tuberias")
        self.tuberias = [tuple(fila) for fila in cursor.fetchall()]
        conn.close()

    def mostrar_tabla(self):
        print("\n=== TUBERÍAS REGISTRADAS ===")
        for idx, tub in enumerate(self.tuberias, 1):
            print(f"N° {idx} | {tub[0]} -> {tub[1]} | Costo: {tub[2]} | Cap: {tub[3]}L")

    def dibujar_grafo_visual(self):
        grafo_visual = nx.DiGraph()
        for estacion in self.estaciones:
            grafo_visual.add_node(estacion)
        etiquetas_aristas = {}
        for tuberia in self.tuberias:
            origen, destino, costo, capacidad = tuberia
            grafo_visual.add_edge(origen, destino)
            etiquetas_aristas[(origen, destino)] = f"C:{costo}\nCap:{capacidad}L"

        plt.figure(figsize=(16, 10)) 
        posiciones = nx.spring_layout(grafo_visual, k=3.5, iterations=100, seed=42) 
        nx.draw_networkx_nodes(grafo_visual, posiciones, node_size=2000, node_color="skyblue", edgecolors="black")
        nx.draw_networkx_labels(grafo_visual, posiciones, font_size=10, font_weight="bold")
        nx.draw_networkx_edges(grafo_visual, posiciones, arrowstyle="-|>", arrowsize=35, width=2.0, edge_color="dimgray", connectionstyle="arc3,rad=0.2")
        propiedades_caja = dict(boxstyle="round,pad=0.3", ec="white", fc="white", alpha=0.8)
        nx.draw_networkx_edge_labels(grafo_visual, posiciones, edge_labels=etiquetas_aristas, font_color="red", font_size=9, label_pos=0.3, bbox=propiedades_caja, rotate=False)
        plt.title("Mapa Visual Disperso de la Red de Distribución", fontsize=14, fontweight="bold")
        plt.axis("off") 
        plt.margins(0.1) 
        plt.show()

# =========================================================================
# 2. CEREBRO MATEMÁTICO: BELLMAN-FORD EN DOS DIMENSIONES (SIN ALTERACIONES)
# =========================================================================

class AlgoritmoBellmanFord:
    def __init__(self, red):
        self.red = red

    def _calcular_costo_ciclo(self, ciclo_nodos, caudal_requerido):
        costo_total = 0
        for i in range(len(ciclo_nodos) - 1):
            u = ciclo_nodos[i]
            v = ciclo_nodos[i+1]
            mejor_costo = float('inf')
            for tub in self.red.tuberias:
                if tub[0] == u and tub[1] == v and tub[3] >= caudal_requerido:
                    if tub[2] < mejor_costo:
                        mejor_costo = tub[2]
            if mejor_costo != float('inf'):
                costo_total += mejor_costo
        return costo_total

    def calcular_rutas(self, origen, caudal_requerido):
        rutas_simples = {est: {'costo': float('inf'), 'camino': []} for est in self.red.estaciones}
        rutas_ciclo = {est: {'costo': float('inf'), 'camino': []} for est in self.red.estaciones}
        if origen not in rutas_simples:
            return rutas_simples, rutas_ciclo
        rutas_simples[origen] = {'costo': 0, 'camino': [origen]}
        total_estaciones = len(self.red.estaciones)
        
        for _ in range(total_estaciones * 2):
            for tuberia in self.red.tuberias:
                u, v, costo, capacidad = tuberia
                if capacidad < caudal_requerido:
                    continue
                if rutas_simples[u]['costo'] != float('inf'):
                    if v not in rutas_simples[u]['camino']:
                        nuevo_costo = rutas_simples[u]['costo'] + costo
                        if nuevo_costo < rutas_simples[v]['costo']:
                            rutas_simples[v] = {'costo': nuevo_costo, 'camino': rutas_simples[u]['camino'] + [v]}
                    else:
                        indice_v = rutas_simples[u]['camino'].index(v)
                        ciclo = rutas_simples[u]['camino'][indice_v:] + [v]
                        costo_ciclo = self._calcular_costo_ciclo(ciclo, caudal_requerido)
                        if costo_ciclo < 0:
                            nuevo_costo = rutas_simples[u]['costo'] + costo
                            if nuevo_costo < rutas_ciclo[v]['costo']:
                                rutas_ciclo[v] = {'costo': nuevo_costo, 'camino': rutas_simples[u]['camino'] + [v]}
                if rutas_ciclo[u]['costo'] != float('inf'):
                    if v not in rutas_ciclo[u]['camino']:
                        nuevo_costo = rutas_ciclo[u]['costo'] + costo
                        if nuevo_costo < rutas_ciclo[v]['costo']:
                            rutas_ciclo[v] = {'costo': nuevo_costo, 'camino': rutas_ciclo[u]['camino'] + [v]}
        return rutas_simples, rutas_ciclo

# =========================================================================
# 3. INTERFAZ GRÁFICA INTERACTIVA EN PYGAME (AQUÍ SE MODIFICÓ LA ELIMINACIÓN)
# =========================================================================

class InterfazGraficaPygame:
    def __init__(self, red, analizador):
        pygame.init()
        self.red = red
        self.analizador = analizador
        self.red.cargar_desde_sqlite()

        # Configuración de dimensiones
        self.ANCHO, self.ALTO = 1100, 650
        self.pantalla = pygame.display.set_mode((self.ANCHO, self.ALTO))
        pygame.display.set_caption("💧 Dashboard de Control: Red de Aguas")
        
        # Colores
        self.BG_COLOR = (240, 244, 248)
        self.PANEL_COLOR = (255, 255, 255)
        self.PRIMARY = (41, 128, 185)
        self.ACCENT = (39, 174, 96)
        self.TEXT_COLOR = (44, 62, 80)
        self.ALERT = (192, 57, 43)

        self.fuente = pygame.font.SysFont("Arial", 13, bold=True)
        self.fuente_estaciones = pygame.font.SysFont("Arial", 13, bold=True)
        self.fuente_titulos = pygame.font.SysFont("Arial", 16, bold=True)

        self.vista_actual = "mapa"

        # Inputs de formulario (Añadido "Estación a Borrar")
        self.inputs = {
            "Estación Origen": "", "Estación Destino": "", "Caudal (L/s)": "",
            "Nueva Estación": "", "Estación a Borrar": "", 
            "Origen Tubería": "", "Destino Tubería": "", "Costo Tubería": "", "Capacidad Tubería": "", 
            "Origen a Borrar": "", "Destino a Borrar": "", "Costo a Borrar": ""
        }
        self.input_activo = None
        self.mensajes_consola_gui = ["Sistema inicializado correctamente.", "Base de datos SQLite sincronizada y cargada."]

        self.posiciones_nodos = {}
        self.actualizar_coordenadas_nodos()

    def actualizar_coordenadas_nodos(self):
        num_nodos = len(self.red.estaciones)
        centro_x, centro_y = 850, 330
        radio = 190
        for i, est in enumerate(self.red.estaciones):
            angulo = 2 * math.pi * i / (num_nodos if num_nodos > 0 else 1)
            self.posiciones_nodos[est] = (centro_x + int(radio * math.cos(angulo)), centro_y + int(radio * math.sin(angulo)))

    def agregar_log(self, texto):
        self.mensajes_consola_gui.append(texto)
        if len(self.mensajes_consola_gui) > 8:
            self.mensajes_consola_gui.pop(0)

    def dibujar_boton(self, rect, texto, color):
        pygame.draw.rect(self.pantalla, color, rect, border_radius=6)
        tx = self.fuente.render(texto, True, (255, 255, 255))
        self.pantalla.blit(tx, tx.get_rect(center=rect.center))

    def dibujar_input(self, rect, label, valor, activo):
        pygame.draw.rect(self.pantalla, (245, 247, 250) if not activo else (230, 240, 250), rect, border_radius=4)
        pygame.draw.rect(self.pantalla, self.PRIMARY if activo else (200, 200, 200), rect, 1, border_radius=4)
        lbl = self.fuente.render(label + ":", True, self.TEXT_COLOR)
        self.pantalla.blit(lbl, (rect.x, rect.y - 18))
        val = self.fuente.render(valor, True, (0, 0, 0))
        self.pantalla.blit(val, (rect.x + 8, rect.y + 8))

    def procesar_calculo(self):
        orig, dest = self.inputs["Estación Origen"].strip(), self.inputs["Estación Destino"].strip()
        if orig not in self.red.estaciones or dest not in self.red.estaciones:
            self.agregar_log("❌ Error: Estaciones inválidas o inexistentes en BD.")
            return
        try:
            caudal = int(self.inputs["Caudal (L/s)"])
        except ValueError:
            self.agregar_log("❌ Error: Caudal debe ser entero numérico.")
            return

        simples, ciclos = self.analizador.calcular_rutas(orig, caudal)
        self.agregar_log(f"📊 Análisis de {orig} a {dest} (Demanda: {caudal} L/s)")
        
        if simples[dest]['costo'] == float('inf'):
            self.agregar_log("R1 Estándar Simple: Físicamente inalcanzable.")
        else:
            self.agregar_log(f"R1 Estándar: {' -> '.join(simples[dest]['camino'])} (Costo: {simples[dest]['costo']})")
            
        if ciclos[dest]['costo'] != float('inf'):
            self.agregar_log(f"R2 Ciclo Explotado: {' -> '.join(ciclos[dest]['camino'])} (Costo: {ciclos[dest]['costo']})")
            
        self.vista_actual = "mapa" 

    def bucle_principal(self):
        reloj = pygame.time.Clock()
        ejecutando = True

        # Geometría reorganizada para acomodar "Eliminar Estación" en la fila 2
        rects_inputs = {
            "Estación Origen": pygame.Rect(30, 50, 130, 30), "Estación Destino": pygame.Rect(180, 50, 130, 30), "Caudal (L/s)": pygame.Rect(330, 50, 110, 30),
            
            # FILA 2: Añadir y Borrar Estación
            "Nueva Estación": pygame.Rect(30, 140, 130, 30),
            "Estación a Borrar": pygame.Rect(310, 140, 130, 30),
            
            "Origen Tubería": pygame.Rect(30, 230, 100, 30), "Destino Tubería": pygame.Rect(140, 230, 100, 30), "Costo Tubería": pygame.Rect(250, 230, 90, 30), "Capacidad Tubería": pygame.Rect(350, 230, 90, 30),
            "Origen a Borrar": pygame.Rect(30, 320, 100, 30), "Destino a Borrar": pygame.Rect(140, 320, 100, 30), "Costo a Borrar": pygame.Rect(250, 320, 90, 30)
        }

        # Botones reubicados para la Fila 2
        btn_calcular = pygame.Rect(460, 50, 110, 30)
        btn_add_estacion = pygame.Rect(170, 140, 120, 30)
        btn_del_estacion = pygame.Rect(450, 140, 120, 30) # NUEVO BOTON
        
        btn_add_tuberia = pygame.Rect(460, 230, 110, 30)
        btn_del_tuberia = pygame.Rect(360, 320, 140, 30) 
        
        # Botones de Vista (Pestañas)
        btn_ver_mapa = pygame.Rect(30, 380, 110, 30)
        btn_ver_estaciones = pygame.Rect(150, 380, 130, 30)
        btn_ver_tuberias = pygame.Rect(290, 380, 130, 30)
        btn_nx_grafo = pygame.Rect(430, 380, 140, 30)

        while ejecutando:
            self.pantalla.fill(self.BG_COLOR)

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False

                elif evento.type == pygame.MOUSEBUTTONDOWN:
                    pos_mouse = evento.pos
                    self.input_activo = None
                    
                    for nombre, rect in rects_inputs.items():
                        if rect.collidepoint(pos_mouse):
                            self.input_activo = nombre

                    if btn_calcular.collidepoint(pos_mouse):
                        self.procesar_calculo()
                    
                    elif btn_add_estacion.collidepoint(pos_mouse):
                        nom = self.inputs["Nueva Estación"].strip()
                        if nom:
                            self.red.agregar_estacion(nom)
                            self.actualizar_coordenadas_nodos()
                            self.agregar_log(f"✅ Estación '{nom}' sincronizada en SQLite.")
                            self.inputs["Nueva Estación"] = ""
                            
                    # ==========================================================
                    # NUEVA LÓGICA DE EVENTO: ELIMINAR ESTACIÓN DESDE LA INTERFAZ
                    # ==========================================================
                    elif btn_del_estacion.collidepoint(pos_mouse):
                        nom = self.inputs["Estación a Borrar"].strip()
                        if nom in self.red.estaciones:
                            self.red.estaciones.remove(nom)
                            # Eliminamos las tuberías conectadas a esta estación limpiando la lista
                            self.red.tuberias = [t for t in self.red.tuberias if t[0] != nom and t[1] != nom]
                            
                            # Usamos la función de guardado existente para refrescar SQLite
                            self.red.guardar_en_sqlite()
                            self.actualizar_coordenadas_nodos()
                            self.agregar_log(f"✅ Estación '{nom}' y sus tuberías eliminadas.")
                        else:
                            if nom:
                                self.agregar_log(f"❌ Error: La estación '{nom}' no existe.")
                        self.inputs["Estación a Borrar"] = ""
                    # ==========================================================

                    elif btn_add_tuberia.collidepoint(pos_mouse):
                        try:
                            o, d = self.inputs["Origen Tubería"].strip(), self.inputs["Destino Tubería"].strip()
                            cos = int(self.inputs["Costo Tubería"])
                            cap = int(self.inputs["Capacidad Tubería"])
                            if o and d:
                                self.red.agregar_tuberia(o, d, cos, cap)
                                self.actualizar_coordenadas_nodos()
                                self.agregar_log(f"✅ Tubería {o} -> {d} guardada con éxito.")
                                self.inputs["Origen Tubería"], self.inputs["Destino Tubería"], self.inputs["Costo Tubería"], self.inputs["Capacidad Tubería"] = "", "", "", ""
                        except ValueError:
                            self.agregar_log("❌ Error: El costo o la capacidad deben ser números.")
                    
                    elif btn_del_tuberia.collidepoint(pos_mouse):
                        try:
                            o_borrar = self.inputs["Origen a Borrar"].strip()
                            d_borrar = self.inputs["Destino a Borrar"].strip()
                            c_borrar = int(self.inputs["Costo a Borrar"].strip())
                            
                            if o_borrar and d_borrar:
                                borrada = self.red.eliminar_tuberia(o_borrar, d_borrar, c_borrar)
                                if borrada:
                                    self.agregar_log(f"✅ Tubería {o_borrar}->{d_borrar} eliminada.")
                                else:
                                    self.agregar_log(f"❌ Error: La tubería no existe en la red.")
                                    
                                self.inputs["Origen a Borrar"] = ""
                                self.inputs["Destino a Borrar"] = ""
                                self.inputs["Costo a Borrar"] = ""
                        except ValueError:
                            self.agregar_log("❌ Error: Introduce un costo numérico válido.")
                    
                    elif btn_ver_mapa.collidepoint(pos_mouse):
                        self.vista_actual = "mapa"
                    elif btn_ver_estaciones.collidepoint(pos_mouse):
                        self.vista_actual = "estaciones"
                    elif btn_ver_tuberias.collidepoint(pos_mouse):
                        self.vista_actual = "tuberias"
                    elif btn_nx_grafo.collidepoint(pos_mouse):
                        self.red.dibujar_grafo_visual()

                elif evento.type == pygame.KEYDOWN and self.input_activo:
                    if evento.key == pygame.K_BACKSPACE:
                        self.inputs[self.input_activo] = self.inputs[self.input_activo][:-1]
                    elif evento.key == pygame.K_ESCAPE:
                        self.input_activo = None
                    else:
                        if len(self.inputs[self.input_activo]) < 18:
                            self.inputs[self.input_activo] += evento.unicode

            # --- RENDERIZADO PANEL CONTROL DE ENTRADA (IZQUIERDA) ---
            pygame.draw.rect(self.pantalla, self.PANEL_COLOR, pygame.Rect(15, 15, 575, 430), border_radius=8)
            for nombre, rect in rects_inputs.items():
                self.dibujar_input(rect, nombre, self.inputs[nombre], self.input_activo == nombre)

            self.dibujar_boton(btn_calcular, "Calcular", self.PRIMARY)
            self.dibujar_boton(btn_add_estacion, "Añadir Est.", self.ACCENT)
            self.dibujar_boton(btn_del_estacion, "Eliminar Est.", self.ALERT) # Dibujado del nuevo botón
            self.dibujar_boton(btn_add_tuberia, "Añadir Conexión", self.ACCENT)
            self.dibujar_boton(btn_del_tuberia, "Eliminar Tubería", self.ALERT)
            
            color_mapa = self.TEXT_COLOR if self.vista_actual == "mapa" else (149, 165, 166)
            color_est = self.TEXT_COLOR if self.vista_actual == "estaciones" else (149, 165, 166)
            color_tub = self.TEXT_COLOR if self.vista_actual == "tuberias" else (149, 165, 166)
            
            self.dibujar_boton(btn_ver_mapa, "🗺️ Ver Mapa", color_mapa)
            self.dibujar_boton(btn_ver_estaciones, "📋 Ver Estaciones", color_est)
            self.dibujar_boton(btn_ver_tuberias, "📋 Ver Tuberías", color_tub)
            self.dibujar_boton(btn_nx_grafo, "📊 Grafo Nx", (52, 73, 94))

            # --- RENDERIZADO CONSOLA DE REGISTROS DE EVENTOS (ABAJO) ---
            pygame.draw.rect(self.pantalla, (44, 62, 80), pygame.Rect(15, 460, 575, 175), border_radius=8)
            t_log = self.fuente_titulos.render("📟 Terminal Visual de Registros de Salida:", True, (189, 195, 199))
            self.pantalla.blit(t_log, (25, 468))
            for index, msg in enumerate(self.mensajes_consola_gui):
                color_texto = (231, 76, 60) if "❌" in msg or "⚠️" in msg else ((46, 204, 113) if "✅" in msg else (236, 240, 241))
                linea = self.fuente.render(msg, True, color_texto)
                self.pantalla.blit(linea, (25, 495 + (index * 17)))

            # --- RENDERIZADO DEL PANEL DERECHO (DINÁMICO SEGÚN LA VISTA) ---
            pygame.draw.rect(self.pantalla, self.PANEL_COLOR, pygame.Rect(605, 15, 480, 620), border_radius=8)

            if self.vista_actual == "mapa":
                t_mapa = self.fuente_titulos.render("🗺️ Topología Hidráulica Dinámica", True, self.TEXT_COLOR)
                self.pantalla.blit(t_mapa, (625, 25))

                for tuberia in self.red.tuberias:
                    u, v, costo, cap = tuberia
                    if u in self.posiciones_nodos and v in self.posiciones_nodos:
                        x1, y1 = self.posiciones_nodos[u]
                        x2, y2 = self.posiciones_nodos[v]
                        dx = x2 - x1
                        dy = y2 - y1
                        dist = math.sqrt(dx*dx + dy*dy)
                        
                        if dist > 0:
                            nx_vec = -dy / dist
                            ny_vec = dx / dist
                            offset = 12
                            
                            x1_final = x1 + nx_vec * offset + (dx / dist) * 24
                            y1_final = y1 + ny_vec * offset + (dy / dist) * 24
                            x2_final = x2 + nx_vec * offset - (dx / dist) * 24
                            y2_final = y2 + ny_vec * offset - (dy / dist) * 24
                            
                            pygame.draw.line(self.pantalla, (149, 165, 166), (x1_final, y1_final), (x2_final, y2_final), 2)
                            
                            angulo_linea = math.atan2(dy, dx)
                            tamano_flecha = 12
                            p1 = (x2_final - tamano_flecha * math.cos(angulo_linea - math.pi/6), y2_final - tamano_flecha * math.sin(angulo_linea - math.pi/6))
                            p2 = (x2_final - tamano_flecha * math.cos(angulo_linea + math.pi/6), y2_final - tamano_flecha * math.sin(angulo_linea + math.pi/6))
                            pygame.draw.polygon(self.pantalla, (127, 140, 141), [(x2_final, y2_final), p1, p2])
                            
                            mx, my = (x1_final + x2_final) // 2, (y1_final + y2_final) // 2
                            texto_x = mx + nx_vec * 10
                            texto_y = my + ny_vec * 10
                            
                            lbl_tub = self.fuente.render(f"C:{costo}|{cap}L", True, self.ALERT)
                            rect_lbl = lbl_tub.get_rect(center=(texto_x, texto_y))
                            pygame.draw.rect(self.pantalla, self.PANEL_COLOR, rect_lbl.inflate(4, 2))
                            self.pantalla.blit(lbl_tub, rect_lbl)

                for est, (x, y) in self.posiciones_nodos.items():
                    pygame.draw.circle(self.pantalla, (174, 214, 241), (x, y), 24)
                    pygame.draw.circle(self.pantalla, self.TEXT_COLOR, (x, y), 24, 2)
                    lbl_est = self.fuente_estaciones.render(est[:5], True, self.TEXT_COLOR)
                    self.pantalla.blit(lbl_est, lbl_est.get_rect(center=(x, y)))

            elif self.vista_actual == "estaciones":
                t_tit = self.fuente_titulos.render("📋 Registro de Estaciones (Base de Datos)", True, self.TEXT_COLOR)
                self.pantalla.blit(t_tit, (625, 25))
                pygame.draw.line(self.pantalla, self.PRIMARY, (625, 55), (1060, 55), 2)
                
                self.pantalla.blit(self.fuente_titulos.render("N°", True, self.PRIMARY), (635, 65))
                self.pantalla.blit(self.fuente_titulos.render("Nombre de la Estación", True, self.PRIMARY), (680, 65))
                pygame.draw.line(self.pantalla, (200, 200, 200), (625, 88), (1060, 88), 1)
                
                for i, est in enumerate(self.red.estaciones):
                    if i > 18: 
                        self.pantalla.blit(self.fuente.render(f"... y {len(self.red.estaciones)-18} más.", True, self.TEXT_COLOR), (635, 100 + i*26))
                        break
                    
                    self.pantalla.blit(self.fuente.render(f"{i+1:02d}", True, self.TEXT_COLOR), (635, 100 + i*26))
                    self.pantalla.blit(self.fuente.render(est, True, self.TEXT_COLOR), (680, 100 + i*26))
                    
                    pygame.draw.line(self.pantalla, (235, 240, 245), (630, 120 + i*26), (1060, 120 + i*26), 1)

            elif self.vista_actual == "tuberias":
                t_tit = self.fuente_titulos.render("📋 Registro de Tuberías (Base de Datos)", True, self.TEXT_COLOR)
                self.pantalla.blit(t_tit, (625, 25))
                pygame.draw.line(self.pantalla, self.PRIMARY, (625, 55), (1060, 55), 2)
                
                self.pantalla.blit(self.fuente_titulos.render("ID", True, self.PRIMARY), (630, 65))
                self.pantalla.blit(self.fuente_titulos.render("Origen", True, self.PRIMARY), (670, 65))
                self.pantalla.blit(self.fuente_titulos.render("Destino", True, self.PRIMARY), (780, 65))
                self.pantalla.blit(self.fuente_titulos.render("Costo", True, self.PRIMARY), (895, 65))
                self.pantalla.blit(self.fuente_titulos.render("Capacidad", True, self.PRIMARY), (975, 65))
                pygame.draw.line(self.pantalla, (200, 200, 200), (625, 88), (1060, 88), 1)
                
                for i, tub in enumerate(self.red.tuberias):
                    if i > 18: 
                        self.pantalla.blit(self.fuente.render(f"... y {len(self.red.tuberias)-18} más.", True, self.TEXT_COLOR), (630, 100 + i*26))
                        break
                    
                    o, d, c, cap = tub
                    
                    self.pantalla.blit(self.fuente.render(f"[{i+1:02d}]", True, self.TEXT_COLOR), (630, 100 + i*26))
                    self.pantalla.blit(self.fuente.render(o[:10], True, self.TEXT_COLOR), (670, 100 + i*26))
                    self.pantalla.blit(self.fuente.render("->", True, (189, 195, 199)), (750, 100 + i*26))
                    self.pantalla.blit(self.fuente.render(d[:10], True, self.TEXT_COLOR), (780, 100 + i*26))
                    self.pantalla.blit(self.fuente.render(f"{c} ud", True, self.TEXT_COLOR), (895, 100 + i*26))
                    self.pantalla.blit(self.fuente.render(f"{cap} L/s", True, self.TEXT_COLOR), (975, 100 + i*26))
                    
                    pygame.draw.line(self.pantalla, (235, 240, 245), (625, 120 + i*26), (1060, 120 + i*26), 1)

            pygame.display.flip()
            reloj.tick(30)

        pygame.quit()

# =========================================================================
# 4. ENTRY POINT DE EJECUCIÓN DIRECTA
# =========================================================================

if __name__ == "__main__":
    red_datos = RedDistribucion()
    motor_calculo = AlgoritmoBellmanFord(red_datos)
    
    app_grafica = InterfazGraficaPygame(red_datos, motor_calculo)
    app_grafica.bucle_principal()