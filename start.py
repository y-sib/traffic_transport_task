import tkinter as tk


def show_start_window():

    def map_on_click():
        base_root.destroy()
        from osm_transport import run_map_app
        run_map_app()

    def table_on_click():
        base_root.destroy()
        from table_module import start_table_app
        start_table_app()

    base_root = tk.Tk()
    base_root.title("Выбор режима")
    window_width = 280
    window_height = 180
    screen_width = base_root.winfo_screenwidth()
    screen_height = base_root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    base_root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    frame = tk.Frame(base_root)
    frame.pack(expand=True)
    btn_map = tk.Button(frame, text="Интерактивная карта", width=30, height=2, command=map_on_click)
    btn_map.pack(pady=15)
    btn_table = tk.Button(frame, text="Табличное представление", width=30, height=2, command=table_on_click)
    btn_table.pack(pady=15)
    base_root.mainloop()


if __name__ == "__main__":
    show_start_window()


