import time
import tkinter as tk
from tkinter import messagebox
from tkintermapview import TkinterMapView
import osmnx as ox
import networkx as nx
import json
import os
import subprocess
import socket
import glob
from shapely.geometry import LineString, shape
from table_module import main_window
from start import show_start_window
from osm_edit import run_edit, run_edit_days
from tkinter import ttk


class MapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Графическая модель")
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill="both", expand=True)
        self.table_frame = tk.Frame(self.main_frame, width=250)
        self.table_frame.pack_propagate(False)
        self.table_frame.pack(side="left", fill="y", padx=5, pady=5)
        btn_menu = tk.Button(self.table_frame, text="Меню", command=lambda: self.menu_action(show_start_window))
        btn_menu.pack(fill="x", padx=5, pady=5)
        tk.Label(self.table_frame, text="Список точек", font=('Arial', 10, 'bold')).pack()
        header_frame = tk.Frame(self.table_frame)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="№", width=15, relief="ridge").pack(side="left")
        tk.Label(header_frame, text="Количество", width=10, relief="ridge").pack(side="left")
        tk.Label(header_frame, text="Удалить", width=8, relief="ridge").pack(side="left")
        self.table_canvas = tk.Canvas(self.table_frame, width=250)
        self.table_rows_frame = tk.Frame(self.table_canvas)
        self.table_canvas.create_window((0, 0), window=self.table_rows_frame, anchor="nw")
        self.table_canvas.pack(side="left", fill="y")
        self.map_frame = tk.Frame(self.main_frame)
        self.map_frame.pack(side="left", fill="both", expand=True)
        self.map_widget = TkinterMapView(self.map_frame, width=850, height=600)
        self.map_widget.pack(fill="both", expand=True)
        self.button_frame = tk.Frame(self.main_frame, width=150)
        self.button_frame.pack(side="right", fill="y", padx=5, pady=5)
        center_x, center_y = 59.9343, 30.3351
        self.map_widget.set_tile_server("http://localhost:8080/styles/basic-preview/{z}/{x}/{y}.png")
        self.map_widget.set_position(center_x, center_y)
        self.map_widget.set_zoom(12)
        self.G = ox.graph_from_point((center_x, center_y), dist=10000, network_type="drive")  # 5 км вокруг точки
        print("Дорожная сеть загружена")
        self.markers_type1 = []
        self.markers_type2 = []
        self.marker_objects = []
        self.table_entries = []
        self.current_marker_type = tk.IntVar(value=1)
        self.route_calculation_mode = tk.StringVar(value="speed")
        self.selected_weekday = tk.StringVar(value="Пн")
        self.selected_hour = tk.IntVar(value=0)
        self.route_ids = []
        self.polygons_ids = []
        self.add_time_attribute()

        self.create_widgets()
        self.load_polygons_for_current_time()
        self.draw_city_border()

    def add_time_attribute(self):
        polygons = load_zones(f"zones/zones_{self.selected_weekday.get()}_{self.selected_hour.get()}.geojson")
        for u, v, data in self.G.edges(data=True):
            coords = [
                (self.G.nodes[u]['x'], self.G.nodes[u]['y']),
                (self.G.nodes[v]['x'], self.G.nodes[v]['y'])
            ]
            zone_id, zone_color = get_zone_for_edge(coords, polygons)
            data['zone_id'] = zone_id
            data['zone_color'] = zone_color

            # Базовая скорость по типу дороги
            speed_coef = 0.2  # по умолчанию
            if "highway" in data:
                if data["highway"] == "motorway":
                    speed_coef = 1
                elif data["highway"] == "primary":
                    speed_coef = 0.6

            # Корректируем скорость по цвету зоны
            if zone_color == "green":
                speed = 110  # без изменений
            elif zone_color == "yellow":
                speed = 50  # замедление
            elif zone_color == "red":
                speed = 20  # сильное замедление
            else:
                speed = 110  # если цвет неизвестен

            speed *= speed_coef

            speed_mps = speed * 1000 / 3600
            data["time"] = data["length"] / speed_mps

    def create_widgets(self):
        # Заголовок для панели управления
        tk.Label(self.button_frame, text="Управление", font=('Arial', 10, 'bold')).pack(pady=5)

        type_frame = tk.LabelFrame(self.button_frame, text="Тип метки", padx=5, pady=5)
        type_frame.pack(fill="x", padx=5, pady=5)
        self.radio_type1 = tk.Radiobutton(type_frame, text="Поставщик", variable=self.current_marker_type, value=1)
        self.radio_type1.pack(anchor="w", padx=5, pady=2)
        self.radio_type2 = tk.Radiobutton(type_frame, text="Потребитель", variable=self.current_marker_type, value=2)
        self.radio_type2.pack(anchor="w", padx=5, pady=2)

        time_frame = tk.LabelFrame(self.button_frame, text="Пробки", padx=5, pady=5)
        time_frame.pack(fill="x", padx=5, pady=5)
        tk.Label(time_frame, text="День недели:").pack(anchor="w")
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        self.day_menu = tk.OptionMenu(time_frame, self.selected_weekday, *days, command=lambda _: self.on_time_change())
        self.day_menu.pack(fill="x", pady=2)

        tk.Label(time_frame, text="Час (0-23):").pack(anchor="w")
        self.hour_spinbox = tk.Spinbox(time_frame, from_=0, to=23, textvariable=self.selected_hour, width=5,
                                       command=self.on_time_change)
        self.hour_spinbox.pack(fill="x", pady=2)

        tk.Label(time_frame, text="Другое:").pack(anchor="w")
        self.btn_user_file = tk.Button(time_frame, text="Пользовательский файл", command=self.open_user_zones_window)
        self.btn_user_file.pack(fill="x", pady=2)
        self.btn_edit = tk.Button(time_frame, text="Редактор зонирования по дням", command=run_edit_days)
        self.btn_edit.pack(fill="x", pady=2)

        mode_frame = tk.LabelFrame(self.button_frame, text="Режим расчета", padx=5, pady=5)
        mode_frame.pack(fill="x", padx=5, pady=5)
        self.radio_speed = tk.Radiobutton(mode_frame, text="С учетом пробок", variable=self.route_calculation_mode, value="speed")
        self.radio_speed.pack(anchor="w", padx=5, pady=2)
        self.radio_distance = tk.Radiobutton(mode_frame, text="Без учета пробок", variable=self.route_calculation_mode, value="distance")
        self.radio_distance.pack(anchor="w", padx=5, pady=2)

        self.route_frame = tk.LabelFrame(self.button_frame, text="Тип визуализации", padx=5, pady=5)
        self.route_frame.pack(fill="x", padx=5, pady=5)
        self.btn_connect = tk.Button(self.route_frame, text="Все маршруты", command=self.connect_points)
        self.btn_connect.pack(fill="x", padx=5, pady=5)
        self.btn_optimal = tk.Button(self.route_frame, text="Оптимальные маршруты", command=self.show_optimal_routes)
        self.btn_optimal.pack(fill="x", padx=5, pady=5)

        self.btn_best_time = tk.Button(self.button_frame, text="Поиск оптимального времени", command=self.open_time_range_window)
        self.btn_best_time.pack(fill="x", padx=5, pady=5)
        self.btn_export = tk.Button(self.button_frame, text="Экспорт в таблицу", command=self.open_export_window)
        self.btn_export.pack(fill="x", padx=5, pady=5)

        self.map_widget.add_left_click_map_command(self.on_map_click)

    def is_within_bounds(self, lat, lon):
        return 30.103357141113293 <= lon <= 30.534957482910168 and 59.81592382663946 <= lat <= 60.06630618497946

    def draw_city_border(self):
        # Новые координаты рамки города
        border_coords = [
            (59.81592382663946, 30.103357141113293),
            (59.81592382663946, 30.534957482910168),
            (60.06630618497946, 30.534957482910168),
            (60.06630618497946, 30.103357141113293),
            (59.81592382663946, 30.103357141113293)
        ]
        self.map_widget.set_polygon(border_coords, outline_color="black", fill_color=None, border_width=3)

    def on_map_click(self, coords):
        lat, lon = coords
        if not self.is_within_bounds(lat, lon):
            return
        marker_type = self.current_marker_type.get()

        # Проверка на максимальное количество точек
        if (marker_type == 1 and len(self.markers_type1) >= 8) or marker_type == 2 and len(self.markers_type2) >= 8:
            messagebox.showinfo("Максимум точек", "На карте максимальное количество точек данного типа")
            return

        if marker_type == 1:
            point_num = len(self.markers_type1) + 1
            self.markers_type1.append((lat, lon))
            marker = self.map_widget.set_marker(lat, lon, text=f"Поставщик-{point_num}", marker_color_circle="red")
            self.marker_objects.append(("type1", marker, (lat, lon), point_num))
        else:
            point_num = len(self.markers_type2) + 1
            self.markers_type2.append((lat, lon))
            marker = self.map_widget.set_marker(lat, lon, text=f"Потребитель-{point_num}", marker_color_circle="blue")
            self.marker_objects.append(("type2", marker, (lat, lon), point_num))

        # Добавляем строку в таблицу
        self.add_table_row(marker_type, point_num, (lat, lon))

    def add_table_row(self, marker_type, point_num, coords):
        def callback(symbol):
            if not symbol.isdigit() and symbol != "":
                return False
            return True
        # Создаем фрейм для строки таблицы
        row_frame = tk.Frame(self.table_rows_frame)
        row_frame.pack(fill="x")

        # Номер точки
        num_label = tk.Label(row_frame, text=f"{'Поставщик' if marker_type == 1 else 'Потребитель'}-{point_num}",
                             width=15, relief="ridge")
        num_label.pack(side="left")

        # Поле для ввода описания
        entry = tk.Entry(row_frame, width=12)

        entry.insert(0, '0')
        entry.config(validate="key", validatecommand=(entry.register(callback), "%P"))
        entry.pack(side="left")

        # Кнопка удаления
        btn_remove = tk.Button(row_frame, text="×", width=7,
                               command=lambda: self.remove_marker(row_frame, marker_type, point_num, coords))
        btn_remove.pack(side="left")

        # Сохраняем элементы строки
        self.table_entries.append((row_frame, num_label, entry, btn_remove, marker_type, point_num, coords))


    def remove_marker(self, row_frame, marker_type, point_num, coords):
        # Удаляем маркер с карты
        for i, (m_type, marker, m_coords, m_num) in enumerate(self.marker_objects):
            if m_type == ("type1" if marker_type == 1 else "type2") and m_num == point_num and m_coords == coords:
                self.map_widget.delete(marker)
                self.marker_objects.pop(i)
                break

        # Удаляем координаты из соответствующего списка
        if marker_type == 1:
            if coords in self.markers_type1:
                self.markers_type1.remove(coords)
        else:
            if coords in self.markers_type2:
                self.markers_type2.remove(coords)

        # Удаляем строку из таблицы
        for i, entry in enumerate(self.table_entries):
            if entry[4] == marker_type and entry[5] == point_num and entry[6] == coords:
                row_frame, num_label, entry, btn_remove, m_type, m_num, m_coords = self.table_entries.pop(i)
                row_frame.destroy()
                break

        # Обновляем нумерацию оставшихся точек
        self.renumber_markers()

        # Очищаем все маршруты при удалении точки
        self.clear_old_routes()

    def renumber_markers(self):
        # Обновляем нумерацию меток и таблицы
        type1_count = 0
        type2_count = 0

        # Сначала обновляем маркеры на карте
        for i, (m_type, marker, coords, old_num) in enumerate(self.marker_objects):
            if m_type == "type1":
                type1_count += 1
                new_num = type1_count
                marker.set_text(f"Поставщик-{new_num}")
                self.marker_objects[i] = (m_type, marker, coords, new_num)
            else:
                type2_count += 1
                new_num = type2_count
                marker.set_text(f"Потребитель-{new_num}")
                self.marker_objects[i] = (m_type, marker, coords, new_num)

        # Затем обновляем таблицу
        type1_count = 0
        type2_count = 0
        for i, (row_frame, num_label, entry, btn_remove, m_type, old_num, coords) in enumerate(self.table_entries):
            # Удаляем старую кнопку
            btn_remove.destroy()
            if m_type == 1:
                type1_count += 1
                new_num = type1_count
                num_label.config(text=f"Поставщик-{new_num}")
                # Создаем новую кнопку удаления с актуальными аргументами
                new_btn_remove = tk.Button(row_frame, text="×", width=7,
                    command=lambda rf=row_frame, mt=m_type, pn=new_num, c=coords: self.remove_marker(rf, mt, pn, c))
                new_btn_remove.pack(side="left")
                self.table_entries[i] = (row_frame, num_label, entry, new_btn_remove, m_type, new_num, coords)
            else:
                type2_count += 1
                new_num = type2_count
                num_label.config(text=f"Потребитель-{new_num}")
                # Создаем новую кнопку удаления с актуальными аргументами
                new_btn_remove = tk.Button(row_frame, text="×", width=7,
                    command=lambda rf=row_frame, mt=m_type, pn=new_num, c=coords: self.remove_marker(rf, mt, pn, c))
                new_btn_remove.pack(side="left")
                self.table_entries[i] = (row_frame, num_label, entry, new_btn_remove, m_type, new_num, coords)

    def get_supply_demand_sums(self):
        suppliers = [int(entry[2].get()) for entry in self.table_entries if entry[4] == 1]
        consumers = [int(entry[2].get()) for entry in self.table_entries if entry[4] == 2]
        return sum(suppliers), sum(consumers), suppliers, consumers

    def connect_points(self):
        self.clear_old_routes()
        if not self.markers_type1 or not self.markers_type2:
            print("Ошибка: Необходимо добавить хотя бы одну метку каждого типа")
            return
        for point1 in self.markers_type1:
            for point2 in self.markers_type2:
                self.draw_route(point1, point2)
        print("Маршруты построены: Все точки соединены")

    def show_optimal_routes(self):

        def show_with_zero():
            optimal_pairs = []
            for point1 in self.markers_type1:
                closest_point2 = None
                min_cost = float('inf')
                for point2 in self.markers_type2:
                    cost = self.calculate_route_cost(point1, point2, weight)
                    if cost is not None and cost < min_cost:
                        min_cost = cost
                        closest_point2 = point2
                if closest_point2:
                    optimal_pairs.append((point1, closest_point2, min_cost))
            for point2 in self.markers_type2:
                has_route = any(p2 == point2 for (p1, p2, cost) in optimal_pairs)
                if not has_route:
                    closest_point1 = None
                    min_cost = float('inf')
                    for point1 in self.markers_type1:
                        cost = self.calculate_route_cost(point1, point2, weight)
                        if cost is not None and cost < min_cost:
                            min_cost = cost
                            closest_point1 = point1
                    if closest_point1:
                        optimal_pairs.append((closest_point1, point2, min_cost))
            unique_pairs = {}
            for p1, p2, cost in optimal_pairs:
                pair_key = (p1, p2) if p1 < p2 else (p2, p1)
                if pair_key not in unique_pairs or cost < unique_pairs[pair_key][1]:
                    unique_pairs[pair_key] = ((p1, p2), cost)
            for (p1, p2), cost in unique_pairs.values():
                self.draw_route(p1, p2)
            print(f"Визуализировано {len(unique_pairs)} оптимальных маршрутов (количества = 0)")
            return
        self.clear_old_routes()
        if not self.markers_type1 or not self.markers_type2:
            print("Ошибка: Необходимо добавить хотя бы одну метку каждого типа")
            return
        supply_sum, demand_sum, suppliers, consumers = self.get_supply_demand_sums()
        all_zero = all(x == 0 for x in suppliers + consumers)
        weight = "time" if self.route_calculation_mode.get() == "speed" else "length"
        if all_zero:
            show_with_zero()
        if supply_sum != demand_sum:
            messagebox.showwarning("Несовпадение количеств", "Суммы количеств поставщиков и потребителей не совпадают. Оптимальные маршруты построены без учета количеств.")
            show_with_zero()
        # Жадное распределение количеств для оптимальных маршрутов
        suppliers_left = suppliers[:]
        consumers_left = consumers[:]
        supplier_idx = 0
        consumer_idx = 0
        while supplier_idx < len(self.markers_type1) and consumer_idx < len(self.markers_type2):
            s_left = suppliers_left[supplier_idx]
            c_left = consumers_left[consumer_idx]
            if s_left == 0:
                supplier_idx += 1
                continue
            if c_left == 0:
                consumer_idx += 1
                continue
            count = min(s_left, c_left)
            for _ in range(count):
                self.draw_route(self.markers_type1[supplier_idx], self.markers_type2[consumer_idx])
            suppliers_left[supplier_idx] -= count
            consumers_left[consumer_idx] -= count
        print("Визуализировано оптимальных маршрутов с учетом количеств")

    def calculate_route_cost(self, start, end, weight):
        try:
            start_node = ox.distance.nearest_nodes(self.G, start[1], start[0])
            end_node = ox.distance.nearest_nodes(self.G, end[1], end[0])
            return nx.shortest_path_length(self.G, start_node, end_node, weight=weight)
        except Exception as e:
            print(f"Ошибка при расчете маршрута: {e}")
            return None

    def clear_old_routes(self):
        print(f"Удаляю {len(self.route_ids)} маршрутов")
        for route_id in self.route_ids:
            self.map_widget.delete(route_id)
        self.route_ids.clear()

    def clear_old_polygons(self):
        print(f"Удаляю {len(self.polygons_ids)} полигонов")
        for poligon_id in self.polygons_ids:
            self.map_widget.delete(poligon_id)
        self.polygons_ids.clear()

    def draw_route(self, start, end):
        # Находим ближайшие узлы дорожной сети для начальной и конечной точек
        start_node = ox.distance.nearest_nodes(self.G, start[1], start[0])
        end_node = ox.distance.nearest_nodes(self.G, end[1], end[0])

        # Выбираем вес для построения маршрута в зависимости от выбранного режима
        weight = "time" if self.route_calculation_mode.get() == "speed" else "length"

        try:
            route = nx.shortest_path(self.G, start_node, end_node, weight=weight)
            # Получаем координаты маршрута
            route_coords = [(self.G.nodes[node]["y"], self.G.nodes[node]["x"]) for node in route]
            # Отображаем маршрут на карте и сохраняем его ID
            route_id = self.map_widget.set_path(route_coords, color="green", width=3)
            self.route_ids.append(route_id)  # Сохраняем ID маршрута

            # Вычисляем длину и время маршрута
            route_length = self.calculate_route_length(route)
            route_time = self.calculate_route_time(route)
            print(f"Маршрут от {start} до {end}: длина {route_length:.2f} м, время {route_time:.2f} сек")
        except Exception as e:
            print(f"Ошибка при построении маршрута: {e}")

    def calculate_route_length(self, route):
        # Вычисляем длину маршрута на основе данных графа
        route_length = 0
        for u, v in zip(route[:-1], route[1:]):
            edge_data = self.G.get_edge_data(u, v)
            route_length += edge_data[0]["length"]
        return route_length

    def calculate_route_time(self, route):
        # Вычисляем время маршрута на основе данных графа
        route_time = 0
        for u, v in zip(route[:-1], route[1:]):
            edge_data = self.G.get_edge_data(u, v)
            route_time += edge_data[0]["time"]
        return route_time

    def load_polygons_for_current_time(self):
        self.clear_old_polygons()
        weekday = self.selected_weekday.get()
        hour = self.selected_hour.get()
        filename = f"zones/zones_{weekday}_{hour}.geojson"
        city_border = [
            (59.81592382663946, 30.103357141113293),
            (59.81592382663946, 30.534957482910168),
            (60.06630618497946, 30.534957482910168),
            (60.06630618497946, 30.103357141113293),
            (59.81592382663946, 30.103357141113293)
        ]
        green_poly_id = self.map_widget.set_polygon(city_border, outline_color=None, fill_color="green", border_width=0)
        self.polygons_ids.append(green_poly_id)
        if not os.path.exists(filename):
            return
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            for i, feature in enumerate(data["features"]):
                coords = feature["geometry"]["coordinates"][0]
                color = feature["properties"].get("congestion", "gray")
                poly_id = self.map_widget.set_polygon([(lat, lon) for lon, lat in coords], outline_color=None,
                                                      fill_color=color, border_width=0)
                self.polygons_ids.append(poly_id)

    def on_time_change(self):
        self.load_polygons_for_current_time()

    def open_time_range_window(self):
        window = tk.Toplevel(self.root)
        window.title("Выбор диапазона времени")
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        tk.Label(window, text="Начальный день:").grid(row=0, column=0, padx=5, pady=5)
        start_day_var = tk.StringVar(value=days[0])
        tk.OptionMenu(window, start_day_var, *days).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(window, text="Начальный час:").grid(row=0, column=2, padx=5, pady=5)
        start_hour_var = tk.IntVar(value=0)
        tk.Spinbox(window, from_=0, to=23, textvariable=start_hour_var, width=5).grid(row=0, column=3, padx=5, pady=5)
        tk.Label(window, text="Конечный день:").grid(row=1, column=0, padx=5, pady=5)
        end_day_var = tk.StringVar(value=days[0])
        tk.OptionMenu(window, end_day_var, *days).grid(row=1, column=1, padx=5, pady=5)
        tk.Label(window, text="Конечный час:").grid(row=1, column=2, padx=5, pady=5)
        end_hour_var = tk.IntVar(value=0)
        tk.Spinbox(window, from_=0, to=23, textvariable=end_hour_var, width=5).grid(row=1, column=3, padx=5, pady=5)

        def on_calculate():
            # Считаем количество шагов для прогрессбара
            days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            start_idx = days_list.index(start_day_var.get())
            end_idx = days_list.index(end_day_var.get())
            idx = start_idx
            hour = start_hour_var.get()
            steps = 0
            while True:
                steps += 1
                if idx == end_idx and hour == end_hour_var.get():
                    break
                hour += 1
                if hour > 23:
                    hour = 0
                    idx = (idx + 1) % 7
            progress_win, progress = self.show_progress_window(steps)
            import threading
            threading.Thread(target=self.calculate_best_day_time_range_with_progress, args=(
                start_day_var.get(), start_hour_var.get(),
                end_day_var.get(), end_hour_var.get(),
                window, progress_win, progress, steps
            ), daemon=True).start()

        tk.Button(window, text="Рассчитать", command=on_calculate).grid(row=2, column=0, columnspan=4, pady=10)

    def calculate_best_day_time_range_with_progress(self, start_day, start_hour, end_day, end_hour, parent_window=None, progress_win=None, progress=None, steps=0):
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        start_idx = days.index(start_day)
        end_idx = days.index(end_day)
        time_points = []
        idx = start_idx
        hour = start_hour
        while True:
            time_points.append((days[idx], hour))
            if idx == end_idx and hour == end_hour:
                break
            hour += 1
            if hour > 23:
                hour = 0
                idx = (idx + 1) % 7
        results = []
        for i, (day, hour) in enumerate(time_points):
            self.selected_weekday.set(day)
            self.selected_hour.set(hour)
            self.add_time_attribute()
            max_time = self.get_max_time_for_current_optimal_routes() / 60
            results.append((day, hour, max_time))
            if progress is not None:
                progress.step(1)
                progress_win.update()
        best = min(results, key=lambda x: x[2] if x[2] is not None else float('inf'))
        if progress_win is not None:
            progress_win.destroy()
        self.root.after(0, lambda: self.show_best_time_window(best, results, parent_window))

    def get_max_time_for_current_optimal_routes(self):
        if not self.markers_type1 or not self.markers_type2:
            return None
        weight = "time" if self.route_calculation_mode.get() == "speed" else "length"
        optimal_pairs = []
        for point1 in self.markers_type1:
            closest_point2 = None
            min_cost = float('inf')
            for point2 in self.markers_type2:
                cost = self.calculate_route_cost(point1, point2, weight)
                if cost is not None and cost < min_cost:
                    min_cost = cost
                    closest_point2 = point2
            if closest_point2:
                optimal_pairs.append((point1, closest_point2, min_cost))
        for point2 in self.markers_type2:
            has_route = any(p2 == point2 for (p1, p2, cost) in optimal_pairs)
            if not has_route:
                closest_point1 = None
                min_cost = float('inf')
                for point1 in self.markers_type1:
                    cost = self.calculate_route_cost(point1, point2, weight)
                    if cost is not None and cost < min_cost:
                        min_cost = cost
                        closest_point1 = point1
                if closest_point1:
                    optimal_pairs.append((closest_point1, point2, min_cost))
        unique_pairs = {}
        for p1, p2, cost in optimal_pairs:
            pair_key = (p1, p2) if p1 < p2 else (p2, p1)
            if pair_key not in unique_pairs or cost < unique_pairs[pair_key][1]:
                unique_pairs[pair_key] = ((p1, p2), cost)
        # Для всех уникальных маршрутов получить время
        max_time = 0
        for (p1, p2), _ in unique_pairs.values():
            try:
                start_node = ox.distance.nearest_nodes(self.G, p1[1], p1[0])
                end_node = ox.distance.nearest_nodes(self.G, p2[1], p2[0])
                route = nx.shortest_path(self.G, start_node, end_node, weight=weight)
                route_time = self.calculate_route_time(route)
                if route_time > max_time:
                    max_time = route_time
            except Exception:
                continue
        return max_time if max_time > 0 else None

    def show_best_time_window(self, best, results, parent_window=None):
        window = tk.Toplevel(self.root)
        window.title("Лучшее время для маршрутов")
        tk.Label(window, text=f"Лучшее время: {best[0]} {best[1]}:00\nВремя маршрута: {best[2]:.2f} минут").pack(pady=10)
        btn = tk.Button(window, text="Подробнее", command=lambda: self.show_full_time_table_window(results, window))
        btn.pack(pady=10)
        if parent_window:
            parent_window.destroy()

    def show_full_time_table_window(self, results, parent_window=None):
        window = tk.Toplevel(self.root)
        window.title("Результаты по диапазону")
        frame = tk.Frame(window)
        frame.pack(padx=10, pady=10)
        tk.Label(frame, text="День").grid(row=0, column=0)
        tk.Label(frame, text="Час").grid(row=0, column=1)
        tk.Label(frame, text="Время (минуты)").grid(row=0, column=2)
        for i, (day, hour, max_time) in enumerate(results, start=1):
            tk.Label(frame, text=day).grid(row=i, column=0)
            tk.Label(frame, text=str(hour)).grid(row=i, column=1)
            tk.Label(frame, text=f"{max_time:.2f}" if max_time is not None else "нет маршрута").grid(row=i, column=2)
        if parent_window:
            parent_window.lift()

    def open_export_window(self):
        window = tk.Toplevel(self.root)
        window.title("Экспорт")
        for i, label in enumerate(["Расстояние", "Расстояние с ограничениями", "Время", "Расстояние и время"]):
            btn = tk.Button(window, text=label, width=30, command=lambda idx=i: self.export_to_table_model(idx))
            btn.grid(row=i, column=0, padx=10, pady=8, sticky="ew")

    def export_to_table_model(self, mode):
        if len(self.markers_type1) < 2 or len(self.markers_type2) < 2:
            messagebox.showwarning("Недостаточно точек", "Для экспорта необходимо добавить минимум 2 точки каждого типа (поставщик и потребитель) на карту.")
            return
        supply_sum, demand_sum, suppliers, consumers = self.get_supply_demand_sums()
        all_zero = all(x == 0 for x in suppliers + consumers)
        if not all_zero and supply_sum != demand_sum:
            messagebox.showwarning("Несовпадение количеств", "Суммы количеств поставщиков и потребителей не совпадают. Экспорт производится по количествам, но они не сходятся.")
        distances = []
        times = []
        consumers_values = []
        suppliers_values = []
        for entry in self.table_entries:
            value = entry[2].get()
            if entry[4] == 2:
                consumers_values.append(value)
            else:
                suppliers_values.append(value)
        quantities = suppliers_values + consumers_values
        num_suppliers = len(self.markers_type1)
        num_consumers = len(self.markers_type2)
        weight = "time" if self.route_calculation_mode.get() == "speed" else "length"
        if all_zero:
            for supplier in self.markers_type1:
                for consumer in self.markers_type2:
                    try:
                        start_node = ox.distance.nearest_nodes(self.G, supplier[1], supplier[0])
                        end_node = ox.distance.nearest_nodes(self.G, consumer[1], consumer[0])
                        route = nx.shortest_path(self.G, start_node, end_node, weight=weight)
                        route_length = self.calculate_route_length(route)
                        route_time = self.calculate_route_time(route)
                        distances.append(route_length)
                        times.append(route_time)
                    except Exception as e:
                        distances.append(None)
                        times.append(None)
        else:
            for i, supplier in enumerate(self.markers_type1):
                for j, consumer in enumerate(self.markers_type2):
                    count = min(suppliers[i], consumers[j])
                    for _ in range(count):
                        try:
                            start_node = ox.distance.nearest_nodes(self.G, supplier[1], supplier[0])
                            end_node = ox.distance.nearest_nodes(self.G, consumer[1], consumer[0])
                            route = nx.shortest_path(self.G, start_node, end_node, weight=weight)
                            route_length = self.calculate_route_length(route)
                            route_time = self.calculate_route_time(route)
                            distances.append(route_length)
                            times.append(route_time)
                        except Exception as e:
                            distances.append(None)
                            times.append(None)
        param_list = ['стоимость', 'стоимость с ограничениями на количество', 'время', 'стоимость и время']
        distances = [str(int(round(i, 0))) for i in distances]
        times = [str(int(round(i, 0))) for i in times]
        list_of_var = [[distances], [[0 for _ in range(num_consumers * num_suppliers)], distances], [times], [times, distances]]
        list_to_export = list_of_var[mode]
        main_window(param_list[mode], num_suppliers, num_consumers, [list_to_export, quantities])

    def open_edit_params(self):
        def check_filename_valid(filename):
            if not filename.strip():
                return False, "Имя файла не может быть пустым"
            path = os.path.join("coding", "zones", f"{filename}.geojson")
            if os.path.exists(path):
                return False, "Файл с таким именем уже существует"
            return True, ""

        def set_optionmenu_state(optionmenu, state="normal"):
            menu = optionmenu["menu"]
            for i in range(menu.index("end") + 1):
                menu.entryconfig(i, state=state)

        def on_mode_change():
            if mode_var.get() == "base":
                hour_spin.configure(state="normal")
                set_optionmenu_state(day_menu, "normal")
                day_menu.config(fg="black")
            else:
                hour_spin.configure(state="disabled")
                set_optionmenu_state(day_menu, "disabled")
                day_menu.config(fg="gray")

        def on_confirm():
            user_zones_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_zones")
            if not os.path.exists(user_zones_dir):
                os.makedirs(user_zones_dir)
            filename = filename_var.get().strip()
            valid, msg = check_filename_valid(filename)
            if not valid:
                messagebox.showerror("Ошибка", msg)
                return
            mode = mode_var.get()
            weekday = day_var.get()
            hour = hour_var.get()
            edit_window.destroy()
            file_path = os.path.join(user_zones_dir, filename)
            if mode == "base":
                template_path = os.path.join("zones", f"zones_{weekday}_{hour}.geojson")
                run_edit(filename=file_path, weekday=weekday, hour=hour, template_path=template_path)
            else:
                run_edit(filename=file_path, weekday=weekday, hour=hour)

        edit_window = tk.Toplevel(self.root)
        edit_window.title("Создание карты")
        mode_var = tk.StringVar(value="base")
        filename_var = tk.StringVar()

        mode_frame = tk.LabelFrame(edit_window, text="Режим создания", padx=5, pady=5)
        mode_frame.pack(fill="x", padx=10, pady=5)

        tk.Radiobutton(mode_frame, text="Создать на основе", variable=mode_var, value="base", command=on_mode_change).grid(row=0, column=0, sticky="w")
        tk.Radiobutton(mode_frame, text="Создать новую карту", variable=mode_var, value="new", command=on_mode_change).grid(row=0, column=1, sticky="w")

        # Новый фрейм для grid
        content_frame = tk.Frame(edit_window)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # День и час (только для режима base)
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_var = tk.StringVar(value=days[0])
        hour_var = tk.IntVar(value=0)
        # Фиксируем ширину для Label и OptionMenu
        day_label = tk.Label(content_frame, text="День:", width=8, anchor="w")
        day_menu = tk.OptionMenu(content_frame, day_var, *days)
        day_menu.config(width=16)  # Фиксированная ширина для OptionMenu
        hour_label = tk.Label(content_frame, text="Час:", width=8, anchor="w")
        hour_spin = tk.Spinbox(content_frame, from_=0, to=23, textvariable=hour_var, width=5)

        day_label.grid(row=1, column=0, padx=5, pady=5)
        day_menu.grid(row=1, column=1, padx=5, pady=5)
        hour_label.grid(row=1, column=2, padx=5, pady=5)
        hour_spin.grid(row=1, column=3, padx=5, pady=5)

        # Поле для имени файла
        filename_label = tk.Label(content_frame, text="Название:", width=8, anchor="w")
        filename_label.grid(row=2, column=0, padx=5, pady=5)
        filename_entry = tk.Entry(content_frame, textvariable=filename_var, width=20)
        filename_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # Кнопка подтверждения
        confirm_btn = tk.Button(content_frame, text="Подтвердить", command=on_confirm)
        confirm_btn.grid(row=3, column=0, columnspan=4, pady=10)

        edit_window.grab_set()
        edit_window.focus_set()
        edit_window.transient(self.root)

    def open_user_zones_window(self):
        window = tk.Toplevel(self.root)
        window.title("Выбор файла")
        user_zones_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_zones")
        if not os.path.exists(user_zones_dir):
            os.makedirs(user_zones_dir)
        files = [os.path.basename(f) for f in glob.glob(os.path.join(user_zones_dir, "*.geojson"))]
        if not files:
            files = ["Нет файлов"]
        selected_file = tk.StringVar(value=files[0])

        main_frame = tk.Frame(window)
        main_frame.pack(padx=10, pady=10, fill="x")

        file_menu = tk.OptionMenu(main_frame, selected_file, *files)
        file_menu.config(width=14)
        file_menu.grid(row=0, column=0, padx=(5,2), pady=(10,2), sticky="ew")

        btn_edit = tk.Button(main_frame, text="Редактировать", width=12, height=1, command=lambda: self.edit_user_zone(selected_file.get()))
        btn_edit.grid(row=0, column=1, padx=(2,5), pady=(10,2), sticky="ew")

        btns_frame = tk.Frame(main_frame)
        btns_frame.grid(row=1, column=0, columnspan=2, pady=(10,5))
        btn_create = tk.Button(btns_frame, text="Создать", width=10, command=self.open_edit_params)
        def on_ok():
            fname = selected_file.get()
            if fname != "Нет файлов":
                self.user_zones_file = os.path.join(user_zones_dir, fname)
                self.load_user_zones_file()
            window.destroy()
        ok_btn = tk.Button(btns_frame, text="ОК", width=10, command=on_ok)
        btn_create.pack(side="left", padx=10)
        ok_btn.pack(side="left", padx=10)

    def edit_user_zone(self, filename):
        if filename == "Нет файлов":
            messagebox.showwarning("Нет файлов", "Нет доступных файлов для редактирования.")
            return
        user_zones_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_zones")
        file_path = os.path.join(user_zones_dir, filename)
        run_edit(file_path)

    def load_user_zones_file(self):
        # Загружает выбранный пользовательский файл зонирования на карту
        if not hasattr(self, 'user_zones_file') or not os.path.exists(self.user_zones_file):
            return
        self.clear_old_polygons()
        city_border = [
            (59.81592382663946, 30.103357141113293),
            (59.81592382663946, 30.534957482910168),
            (60.06630618497946, 30.534957482910168),
            (60.06630618497946, 30.103357141113293),
            (59.81592382663946, 30.103357141113293)
        ]
        green_poly_id = self.map_widget.set_polygon(city_border, outline_color=None, fill_color="green", border_width=0)
        self.polygons_ids.append(green_poly_id)
        with open(self.user_zones_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for i, feature in enumerate(data["features"]):
                coords = feature["geometry"]["coordinates"][0]
                color = feature["properties"].get("congestion", "gray")
                poly_id = self.map_widget.set_polygon([(lat, lon) for lon, lat in coords], outline_color=None,
                                                      fill_color=color, border_width=0, name="")
                self.polygons_ids.append(poly_id)

    def menu_action(self, show_start_window):
        self.root.destroy()
        show_start_window()

    def show_progress_window(self, max_value):
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Выполнение расчёта")
        progress_win.geometry("350x80")
        tk.Label(progress_win, text="Пожалуйста, подождите. Идёт расчёт...").pack(pady=8)
        progress = ttk.Progressbar(progress_win, orient="horizontal", length=300, mode="determinate", maximum=max_value)
        progress.pack(pady=8)
        progress_win.transient(self.root)
        progress_win.grab_set()
        progress_win.focus_set()
        return progress_win, progress


# Загрузка полигонов из GeoJSON
def load_zones(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            polygons = []
            for i, feature in enumerate(data["features"]):
                poly = shape(feature["geometry"])
                color = feature["properties"].get("congestion", "gray")
                polygons.append((i, poly, color))
            return polygons
    except Exception as e:
        return []


# Проверка принадлежности ребра к области
def get_zone_for_edge(edge_coords, polygons):
    line = LineString(edge_coords)
    center = line.centroid
    for zone_id, poly, color in polygons:
        if poly.contains(line) or poly.contains(center):
            return zone_id, color
    return None, "green"


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def start_tileserver():
    bat_path = r'osm.bat'
    subprocess.Popen(bat_path, shell=True)
    time.sleep(3)


def run_map_app():
    root = tk.Tk()
    app = MapApp(root)
    root.after(200, start_tileserver)
    try:
        root.mainloop()
    finally:
        root.destroy()


if __name__ == "__main__":
    run_map_app()
