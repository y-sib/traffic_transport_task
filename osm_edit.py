import tkinter as tk
from tkinter import messagebox
from tkintermapview import TkinterMapView
import json
import os
import shutil
import sys

# --- Базовый класс с общим функционалом ---
class MapEditAppBase:
    def __init__(self, e_root, filepath=None):
        self.edit_root = e_root
        self.filepath = filepath
        self.edit_root.title("Редактор")
        self.selected_color = tk.StringVar(value="yellow")
        self.selected_weekday = tk.StringVar(value="Пн")
        self.selected_hour = tk.IntVar(value=0)
        self.main_frame = tk.Frame(e_root)
        self.main_frame.pack(fill="both", expand=True)
        self.table_frame = tk.Frame(self.main_frame, width=180)
        self.table_frame.pack_propagate(False)
        self.table_frame.pack(side="left", fill="y", padx=5, pady=5)
        tk.Label(self.table_frame, text="Список точек", font=('Arial', 10, 'bold')).pack()
        header_frame = tk.Frame(self.table_frame)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="№", width=5, relief="ridge").pack(side="left")
        tk.Label(header_frame, text="Удалить", width=8, relief="ridge").pack(side="left")
        self.table_canvas = tk.Canvas(self.table_frame, width=100)
        self.table_rows_frame = tk.Frame(self.table_canvas)
        self.table_canvas.create_window((0, 0), window=self.table_rows_frame, anchor="nw")
        self.table_canvas.pack(side="left", fill="y")
        self.map_frame = tk.Frame(self.main_frame)
        self.map_frame.pack(side="left", fill="both", expand=True)
        self.map_widget = TkinterMapView(self.map_frame, width=800, height=600)
        self.map_widget.pack(fill="both", expand=True)
        self.button_frame = tk.Frame(self.main_frame, width=180)
        self.button_frame.pack(side="right", fill="y", padx=5, pady=5)
        self.map_widget.set_tile_server("http://localhost:8080/styles/basic-preview/{z}/{x}/{y}.png")
        self.map_widget.set_position(59.9343, 30.3351)
        self.map_widget.set_zoom(12)
        self.markers = []
        self.marker_objects = []
        self.table_entries = []
        self.poligons_ids = []
        self.selected_polygon_index = None
        self.create_widgets()
        self.load_polygons_for_current_time()

    def create_widgets(self):
        tk.Label(self.button_frame, text="Управление", font=('Arial', 10, 'bold')).pack(pady=5)
        color_frame = tk.LabelFrame(self.button_frame, text="Цвет маркера", padx=5, pady=5)
        color_frame.pack(fill="x", padx=5, pady=5)
        tk.Radiobutton(color_frame, text="Желтый", variable=self.selected_color, value="yellow", command=self.update_all_marker_colors).pack(anchor="w", padx=5, pady=2)
        tk.Radiobutton(color_frame, text="Красный", variable=self.selected_color, value="red", command=self.update_all_marker_colors).pack(anchor="w", padx=5, pady=2)
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        tk.Label(self.table_frame, text="Точки", font=('Arial', 10, 'bold')).pack()
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
        self.map_widget.add_left_click_map_command(self.on_map_click)

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
        # Удаляем маркер с карты
        for i, (marker, m_coords, m_num) in enumerate(self.marker_objects):
            if m_coords == coords:
                self.map_widget.delete(marker)
                self.marker_objects.pop(i)
                break
        # Удаляем координаты из списка маркеров
        for i, (lat, lon, c) in enumerate(self.markers):
            if (lat, lon, c) == coords:
                self.markers.pop(i)
                break
        # Удаляем строку из таблицы по координатам и цвету
        for i, entry in enumerate(self.table_entries):
            if entry[4] == coords and entry[5] == color:
                row_frame, num_label, btn_remove, old_num, coords, color = self.table_entries.pop(i)
                row_frame.destroy()
                break
        self.renumber_markers()
        self.update_table()

    def renumber_markers(self):
        for i, (marker, coords, old_num) in enumerate(self.marker_objects):
            new_num = i + 1
            marker.set_text(f"Точка-{new_num}")
            self.marker_objects[i] = (marker, coords, new_num)
        for i, (row_frame, num_label, btn_remove, old_num, coords, color) in enumerate(self.table_entries):
            new_num = i + 1
            num_label.config(text=f"{new_num}")
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
        for marker, coords, num in self.marker_objects:
            self.map_widget.delete(marker)
        self.marker_objects.clear()
        for i, (lat, lon, _) in enumerate(self.markers):
            self.markers[i] = (lat, lon, new_color)
            marker = self.map_widget.set_marker(lat, lon, text=f"Точка-{i+1}", marker_color_circle=new_color)
            self.marker_objects.append((marker, (lat, lon, new_color), i+1))

    def clear_markers(self):
        for marker, _, _ in self.marker_objects:
            self.map_widget.delete(marker)
        self.markers.clear()
        self.marker_objects.clear()
        for row_frame, *_ in self.table_entries:
            row_frame.destroy()
        self.table_entries.clear()
        self.load_polygons_for_current_time()

    def clear_table(self):
        for row_frame, *_ in self.table_entries:
            row_frame.destroy()
        self.table_entries.clear()

    def show_points_table(self):
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

    def update_table(self):
        self.show_points_table()
        self.show_polygons_table()

    # --- Универсальные методы для работы с полигонами ---
    def save_polygon(self):
        if len(self.markers) < 3:
            messagebox.showwarning("Недостаточно точек", "Для полигона нужно минимум 3 точки.")
            return
        coords = [(lon, lat) for lat, lon, _ in self.markers]  # для GeoJSON
        zone = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            },
            "properties": self.get_polygon_properties()
        }
        filename = self.get_polygon_filename()
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"type": "FeatureCollection", "features": []}
            data["features"].append(zone)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Сохранено {filename}.")
        except Exception as e:
            print("Ошибка при сохранении полигона:", e)
            messagebox.showerror("Ошибка", f"Не удалось сохранить полигон: {e}")
        self.clear_markers()
        self.load_polygons_for_current_time()
        self.update_table()

    def load_polygons_for_current_time(self):
        self.clear_old_poligons()
        filename = self.get_polygon_filename()
        if not os.path.exists(filename):
            self.show_polygons_table()
            return
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            for i, feature in enumerate(data.get("features", [])):
                coords = feature["geometry"]["coordinates"][0]
                color = feature["properties"].get("congestion", "gray")
                outline = "red" if self.selected_polygon_index == i else color
                width = 4 if self.selected_polygon_index == i else 2
                poly_id = self.map_widget.set_polygon([(lat, lon) for lon, lat in coords], outline_color=outline,
                                                      fill_color=color, border_width=width, name="")
                self.poligons_ids.append(poly_id)
        self.show_polygons_table()

    def show_polygons_table(self):
        for widget in self.polygons_rows_frame.winfo_children():
            widget.destroy()
        polygons = []
        filename = self.get_polygon_filename()
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
        filename = self.get_polygon_filename()
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

    # --- Абстрактные методы для наследников ---
    def get_polygon_filename(self):
        raise NotImplementedError

    def get_polygon_properties(self):
        return {"congestion": self.selected_color.get()}

# --- Режим по дням/часам ---
class MapEditAppDays(MapEditAppBase):
    def create_widgets(self):
        super().create_widgets()
        # Группа для выбора дня недели
        weekday_frame = tk.LabelFrame(self.button_frame, text="День недели", padx=5, pady=5)
        weekday_frame.pack(fill="x", padx=5, pady=5)
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        tk.OptionMenu(weekday_frame, self.selected_weekday, *weekdays).pack(fill="x", padx=5, pady=2)
        # Группа для выбора часа
        hour_frame = tk.LabelFrame(self.button_frame, text="Час", padx=5, pady=5)
        hour_frame.pack(fill="x", padx=5, pady=5)
        tk.Spinbox(hour_frame, from_=0, to=23, textvariable=self.selected_hour, width=5).pack(fill="x", padx=5, pady=2)
        tk.Button(self.button_frame, text="Добавить", command=self.save_polygon).pack(fill="x", padx=5, pady=10)
        self.selected_weekday.trace_add("write", lambda *args: (self.clear_markers(), self.load_polygons_for_current_time()))
        self.selected_hour.trace_add("write", lambda *args: (self.clear_markers(), self.load_polygons_for_current_time()))

    def get_polygon_filename(self):
        weekday = self.selected_weekday.get()
        hour = self.selected_hour.get()
        return f"zones/zones_{weekday}_{hour}.geojson"

# --- Режим пользовательских файлов ---
class MapEditAppUser(MapEditAppBase):
    def create_widgets(self):
        super().create_widgets()
        tk.Button(self.button_frame, text="Добавить", command=self.save_polygon).pack(fill="x", padx=5, pady=10)

    def get_polygon_filename(self):
        if self.filepath:
            return self.filepath
        else:
            return os.path.join("user_zones", "user_zone.geojson")

def create_file_based_on_template(template_path, new_path):
    shutil.copyfile(template_path, new_path)

def run_edit(filename=None, weekday=None, hour=None, user_filepath=None, template_path=None):
    if filename and not filename.endswith('.geojson'):
        filename += '.geojson'
    # Если нужно создать на основе шаблона
    if template_path and template_path != filename:
        if not os.path.exists(filename):
            create_file_based_on_template(template_path, filename)
    # Если файл не существует и не указан шаблон — создаём пустой GeoJSON
    elif filename and not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f, ensure_ascii=False, indent=2)
    root = tk.Toplevel()
    if user_filepath:
        app = MapEditAppUser(root, filepath=user_filepath)
    else:
        app = MapEditAppUser(root, filepath=filename)


def run_edit_days():
    root = tk.Toplevel()
    app = MapEditAppDays(root)

if __name__ == "__main__":
    # Можно запускать с аргументами: python main.py user <filename> или python main.py days
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        filename = sys.argv[2] if len(sys.argv) > 2 else None
        run_edit(mode=mode, filename=filename)
        if tk._default_root:
            tk._default_root.mainloop()
    else:
        # По умолчанию режим days
        root = tk.Tk()
        app = MapEditAppDays(root)
        root.mainloop()
