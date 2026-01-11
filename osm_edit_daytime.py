import tkinter as tk
from tkinter import messagebox
from tkintermapview import TkinterMapView
import json
import os


class MapEditApp:
    def __init__(self, e_root):
        self.edit_root = e_root
        self.edit_root.title("Редактор")

        # Главный контейнер
        self.main_frame = tk.Frame(e_root)
        self.main_frame.pack(fill="both", expand=True)

        # Фрейм для таблицы (слева)
        self.table_frame = tk.Frame(self.main_frame, width=180)
        self.table_frame.pack_propagate(False)
        self.table_frame.pack(side="left", fill="y", padx=5, pady=5)

        # Заголовок таблицы
        tk.Label(self.table_frame, text="Список точек", font=('Arial', 10, 'bold')).pack()

        # Фрейм для заголовков столбцов
        header_frame = tk.Frame(self.table_frame)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="№", width=5, relief="ridge").pack(side="left")
        tk.Label(header_frame, text="Удалить", width=8, relief="ridge").pack(side="left")

        self.table_canvas = tk.Canvas(self.table_frame, width=100)
        self.table_rows_frame = tk.Frame(self.table_canvas)
        self.table_canvas.create_window((0, 0), window=self.table_rows_frame, anchor="nw")

        self.table_canvas.pack(side="left", fill="y")

        # Фрейм для карты (центр)
        self.map_frame = tk.Frame(self.main_frame)
        self.map_frame.pack(side="left", fill="both", expand=True)

        self.map_widget = TkinterMapView(self.map_frame, width=800, height=600)
        self.map_widget.pack(fill="both", expand=True)

        # Фрейм для кнопок (справа)
        self.button_frame = tk.Frame(self.main_frame, width=180)
        self.button_frame.pack(side="right", fill="y", padx=5, pady=5)

        # Подключаем локальный сервер тайлов
        self.map_widget.set_tile_server("http://localhost:8080/styles/basic-preview/{z}/{x}/{y}.png")

        # Устанавливаем начальную позицию карты (Санкт-Петербург)
        self.map_widget.set_position(59.9343, 30.3351)  # Координаты Санкт-Петербурга
        self.map_widget.set_zoom(12)  # Масштаб карты

        # Списки для хранения точек и маркеров
        self.markers = []  # [(lat, lon, color)]
        self.marker_objects = []  # [(marker, (lat, lon, color), num)]
        self.table_entries = []  # [(row_frame, num_label, color_label, btn_remove, num, coords, color)]

        # Переменные для управления
        self.selected_color = tk.StringVar(value="yellow")
        self.selected_weekday = tk.StringVar(value="Пн")
        self.selected_hour = tk.IntVar(value=0)

        # Список для хранения ID полигонов
        self.poligons_ids = []

        # Создаем интерфейс
        self.create_widgets()
        self.selected_polygon_index = None  # Индекс выделенного полигона
        self.load_polygons_for_current_time()  # Показываем полигоны при запуске

    def create_widgets(self):
        # Заголовок для панели управления
        tk.Label(self.button_frame, text="Управление", font=('Arial', 10, 'bold')).pack(pady=5)

        # Группа для выбора цвета маркера
        color_frame = tk.LabelFrame(self.button_frame, text="Цвет маркера", padx=5, pady=5)
        color_frame.pack(fill="x", padx=5, pady=5)
        tk.Radiobutton(color_frame, text="Желтый", variable=self.selected_color, value="yellow", command=self.update_all_marker_colors).pack(anchor="w", padx=5, pady=2)
        tk.Radiobutton(color_frame, text="Красный", variable=self.selected_color, value="red", command=self.update_all_marker_colors).pack(anchor="w", padx=5, pady=2)

        # Группа для выбора дня недели
        weekday_frame = tk.LabelFrame(self.button_frame, text="День недели", padx=5, pady=5)
        weekday_frame.pack(fill="x", padx=5, pady=5)
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        tk.OptionMenu(weekday_frame, self.selected_weekday, *weekdays).pack(fill="x", padx=5, pady=2)

        # Группа для выбора часа
        hour_frame = tk.LabelFrame(self.button_frame, text="Час", padx=5, pady=5)
        hour_frame.pack(fill="x", padx=5, pady=5)
        tk.Spinbox(hour_frame, from_=0, to=23, textvariable=self.selected_hour, width=5).pack(fill="x", padx=5, pady=2)

        # Кнопка "Добавить"
        tk.Button(self.button_frame, text="Добавить", command=self.save_polygon).pack(fill="x", padx=5, pady=10)

        # --- Левая панель: две таблицы ---
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        # Заголовок
        tk.Label(self.table_frame, text="Точки", font=('Arial', 10, 'bold')).pack()
        # Таблица точек (фиксированная высота для 8 строк + заголовок)
        self.points_table_frame = tk.Frame(self.table_frame, width=180, height=225)
        self.points_table_frame.pack(fill="x")
        self.points_table_frame.pack_propagate(False)
        header_points = tk.Frame(self.points_table_frame)
        header_points.pack(fill="x")
        tk.Label(header_points, text="№", width=5, relief="ridge").pack(side="left")
        tk.Label(header_points, text="Удалить", width=8, relief="ridge").pack(side="left")
        self.points_rows_frame = tk.Frame(self.points_table_frame)
        self.points_rows_frame.pack(fill="x")
        tk.Label(self.table_frame, text="Полигоны", font=('Arial', 10, 'bold')).pack(pady=(5, 0))
        polygons_scroll_container = tk.Frame(self.table_frame, width=180)
        polygons_scroll_container.pack(side="top", fill="both", expand=True)
        self.polygons_table_canvas = tk.Canvas(polygons_scroll_container, width=180)
        self.polygons_table_canvas.grid(row=0, column=0, sticky="nsew")
        self.polygons_scrollbar = tk.Scrollbar(polygons_scroll_container, orient="vertical", command=self.polygons_table_canvas.yview)
        self.polygons_scrollbar.grid(row=0, column=1, sticky="ns")
        polygons_scroll_container.grid_rowconfigure(0, weight=1)
        polygons_scroll_container.grid_columnconfigure(0, weight=1)
        self.polygons_table_canvas.configure(yscrollcommand=self.polygons_scrollbar.set)
        self.polygons_table_inner = tk.Frame(self.polygons_table_canvas, width=180)
        self.polygons_table_canvas.create_window((0, 0), window=self.polygons_table_inner, anchor="nw")
        self.polygons_table_inner.bind("<Configure>", lambda e: self.polygons_table_canvas.configure(scrollregion=self.polygons_table_canvas.bbox("all")))
        self.polygons_header = tk.Frame(self.polygons_table_inner, width=180)
        self.polygons_header.pack(fill="x")
        tk.Label(self.polygons_header, text="№", width=5, relief="ridge").pack(side="left")
        tk.Label(self.polygons_header, text="Показать", width=8, relief="ridge").pack(side="left")
        tk.Label(self.polygons_header, text="Удалить", width=8, relief="ridge").pack(side="left")
        self.polygons_rows_frame = tk.Frame(self.polygons_table_inner, width=180)
        self.polygons_rows_frame.pack(fill="x")

        # Привязываем обработчик клика на карте
        self.map_widget.add_left_click_map_command(self.on_map_click)

        # Очищаем точки при смене дня/часа
        self.selected_weekday.trace_add("write", lambda *args: (self.clear_markers(), self.load_polygons_for_current_time()))
        self.selected_hour.trace_add("write", lambda *args: (self.clear_markers(), self.load_polygons_for_current_time()))

    def get_all_existing_polygon_points(self):
        points = set()
        zones_dir = "zones"
        if not os.path.exists(zones_dir):
            return points

        for file in os.listdir(zones_dir):
            if file.endswith(".geojson"):
                with open(os.path.join(zones_dir, file), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for feature in data.get("features", []):
                        coords = feature["geometry"]["coordinates"][0]
                        for lon, lat in coords:
                            points.add((lat, lon))
        return points

    def snap_point(self, lat, lon, existing_points, threshold=0.001):
        for ex_lat, ex_lon in existing_points:
            if abs(ex_lat - lat) < threshold and abs(ex_lon - lon) < threshold:
                return ex_lat, ex_lon
        return lat, lon

    def on_map_click(self, coords):
        lat, lon = coords
        print(lat, lon)
        existing_points = self.get_all_existing_polygon_points()
        lat, lon = self.snap_point(lat, lon, existing_points)
        if len(self.markers) >= 8:
            messagebox.showinfo("Максимум точек", "На карте максимальное количество точек (8)")
            return
        color = self.selected_color.get()
        point_num = len(self.markers) + 1
        self.markers.append((lat, lon, color))
        marker = self.map_widget.set_marker(lat, lon, text=f"Точка-{point_num}", marker_color_circle=color)
        self.marker_objects.append((marker, (lat, lon, color), point_num))
        self.update_table()

    def add_table_row(self, point_num, coords, color):
        row_frame = tk.Frame(self.table_rows_frame)
        row_frame.pack(fill="x")
        num_label = tk.Label(row_frame, text=f"{point_num}", width=5, relief="ridge")
        num_label.pack(side="left")
        btn_remove = tk.Button(row_frame, text="×", width=7,
                               command=lambda: self.remove_marker(row_frame, point_num, coords, color))
        btn_remove.pack(side="left")
        self.table_entries.append((row_frame, num_label, btn_remove, point_num, coords, color))

    def remove_marker(self, row_frame, point_num, coords, color):
        for i, (marker, m_coords, m_num) in enumerate(self.marker_objects):
            if m_coords == coords and m_num == point_num:
                self.map_widget.delete(marker)
                self.marker_objects.pop(i)
                break
        for i, (lat, lon, c) in enumerate(self.markers):
            if (lat, lon, c) == coords:
                self.markers.pop(i)
                break
        for i, entry in enumerate(self.table_entries):
            if entry[4] == point_num and entry[5] == coords and entry[6] == color:
                row_frame, num_label, btn_remove, old_num, coords, color = self.table_entries.pop(i)
                row_frame.destroy()
                break
        self.renumber_markers()
        self.load_polygons_for_current_time()

    def renumber_markers(self):
        # Обновляем нумерацию маркеров и таблицы
        for i, (marker, coords, old_num) in enumerate(self.marker_objects):
            new_num = i + 1
            marker.set_text(f"Точка-{new_num}")
            self.marker_objects[i] = (marker, coords, new_num)
        for i, (row_frame, num_label, btn_remove, old_num, coords, color) in enumerate(self.table_entries):
            new_num = i + 1
            num_label.config(text=f"{new_num}")
            # Пересоздаем кнопку удаления с актуальными аргументами
            btn_remove.destroy()
            new_btn_remove = tk.Button(row_frame, text="×", width=7,
                command=lambda rf=row_frame, pn=new_num, c=coords, col=color: self.remove_marker(rf, pn, c, col))
            new_btn_remove.pack(side="left")
            self.table_entries[i] = (row_frame, num_label, new_btn_remove, new_num, coords, color)

    def clear_old_poligons(self):
        for poligon_id in self.poligons_ids:
            self.map_widget.delete(poligon_id)
        self.poligons_ids.clear()

    def update_all_marker_colors(self):
        new_color = self.selected_color.get()
        # Удаляем все маркеры с карты
        for marker, coords, num in self.marker_objects:
            self.map_widget.delete(marker)
        # Пересоздаём маркеры с новым цветом
        self.marker_objects.clear()
        for i, (lat, lon, _) in enumerate(self.markers):
            self.markers[i] = (lat, lon, new_color)
            marker = self.map_widget.set_marker(lat, lon, text=f"Точка-{i+1}", marker_color_circle=new_color)
            self.marker_objects.append((marker, (lat, lon, new_color), i+1))

    def save_polygon(self):
        if len(self.markers) < 3:
            messagebox.showwarning("Недостаточно точек", "Для полигона нужно минимум 3 точки.")
            return
        coords = [(lon, lat) for lat, lon, _ in self.markers]
        weekday = self.selected_weekday.get()
        hour = self.selected_hour.get()
        congestion = self.selected_color.get()
        zone = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            },
            "properties": {
                "congestion": congestion
            }
        }
        os.makedirs("zones", exist_ok=True)
        filename = f"zones/zones_{weekday}_{hour}.geojson"
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"type": "FeatureCollection", "features": []}
        data["features"].append(zone)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Сохранено {filename}.")
        self.clear_markers()
        self.load_polygons_for_current_time()
        self.update_table()

    def clear_markers(self):
        for marker, _, _ in self.marker_objects:
            self.map_widget.delete(marker)
        self.markers.clear()
        self.marker_objects.clear()
        for row_frame, *_ in self.table_entries:
            row_frame.destroy()
        self.table_entries.clear()
        self.load_polygons_for_current_time()

    def load_polygons_for_current_time(self):
        self.clear_old_poligons()
        weekday = self.selected_weekday.get()
        hour = self.selected_hour.get()
        filename = f"zones/zones_{weekday}_{hour}.geojson"
        if not os.path.exists(filename):
            self.show_polygons_table()
            return
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            for i, feature in enumerate(data["features"]):
                coords = feature["geometry"]["coordinates"][0]
                color = feature["properties"].get("congestion", "gray")
                outline = "red" if self.selected_polygon_index == i else color
                width = 4 if self.selected_polygon_index == i else 2
                poly_id = self.map_widget.set_polygon([(lat, lon) for lon, lat in coords], outline_color=outline,
                                                      fill_color=color, border_width=width, name="")
                self.poligons_ids.append(poly_id)
        self.show_polygons_table()

    def clear_table(self):
        for row_frame, *_ in self.table_entries:
            row_frame.destroy()
        self.table_entries.clear()

    def show_points_table(self):
        # Очищаем только таблицу точек
        for widget in self.points_rows_frame.winfo_children():
            widget.destroy()
        for i, (lat, lon, color) in enumerate(self.markers):
            row_frame = tk.Frame(self.points_rows_frame)
            row_frame.pack(fill="x")
            num_label = tk.Label(row_frame, text=f"{i+1}", width=5, relief="ridge")
            num_label.pack(side="left")
            btn_remove = tk.Button(row_frame, text="×", width=7,
                                   command=lambda rf=row_frame, pn=i+1, c=(lat, lon, color), col=color: self.remove_marker(rf, pn, c, col))
            btn_remove.pack(side="left")

    def show_polygons_table(self):
        for widget in self.polygons_rows_frame.winfo_children():
            widget.destroy()
        weekday = self.selected_weekday.get()
        hour = self.selected_hour.get()
        filename = f"zones/zones_{weekday}_{hour}.geojson"
        polygons = []
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                polygons = data.get("features", [])
        for i, feature in enumerate(polygons):
            row_frame = tk.Frame(self.polygons_rows_frame)
            row_frame.pack(fill="x")
            num_label = tk.Label(row_frame, text=f"{i+1}", width=5, relief="ridge")
            num_label.pack(side="left")
            btn_show = tk.Button(row_frame, text="v", width=7,
                                 command=lambda idx=i: self.highlight_polygon(idx))
            btn_show.pack(side="left")
            btn_remove = tk.Button(row_frame, text="×", width=7,
                                   command=lambda idx=i: self.delete_polygon(idx))
            btn_remove.pack(side="left")

    def delete_polygon(self, idx):
        weekday = self.selected_weekday.get()
        hour = self.selected_hour.get()
        filename = f"zones/zones_{weekday}_{hour}.geojson"
        if not os.path.exists(filename):
            return
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        features = data.get("features", [])
        if 0 <= idx < len(features):
            features.pop(idx)
        data["features"] = features
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.show_polygons_table()
        self.load_polygons_for_current_time()

    def highlight_polygon(self, idx):
        if self.selected_polygon_index == idx:
            self.selected_polygon_index = None
        else:
            self.selected_polygon_index = idx
        self.load_polygons_for_current_time()

    def update_table(self):
        self.show_points_table()
        self.show_polygons_table()


def run_edit_days():
    edit_window = tk.Toplevel()
    app = MapEditApp(edit_window)


if __name__ == "__main__":
    root = tk.Tk()
    app = MapEditApp(root)
    root.mainloop()
