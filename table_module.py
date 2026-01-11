from tkinter import *
from tkinter import ttk
import tkinter as tk
from tkinter.messagebox import showinfo
from matrix_generation import generate
from start import show_start_window

time_param = 100
c_param = 0.5
t_param = 0.5


def start_table_app():
    root = Tk()
    root.title("Настройка транспортной таблицы")
    root.geometry("390x265+550+250")
    label = Label(text="Параметры:")
    label.place(x=15, y=20)

    param_list = ['стоимость', 'стоимость с ограничениями на количество', 'время', 'стоимость и время']

    res = StringVar(value=param_list[0])
    for i in range(len(param_list)):
        Radiobutton(text=param_list[i], value=param_list[i], variable=res).place(x=20, y=45 + i * 25)

    numbers_list = [str(i + 2) for i in range(7)]
    label_list = ['Количество потребителей (столбцов)', 'Количество поставщиков (строк)']
    combo_list = []

    for i in range(2):
        l = Label(text=label_list[i])
        l.place(x=15, y=155 + i * 30)
        combobox = ttk.Combobox(values=numbers_list, state='readonly')
        combobox.place(x=230, y=155 + i * 30)
        combobox.current(0)
        combo_list.append(combobox)

    def return_on_click():
        root.destroy()
        show_start_window()

    def next_on_click():
        status = res.get()
        cb1 = int(combo_list[0].get())
        cb2 = int(combo_list[1].get())
        root.destroy()
        main_window(status, cb1, cb2)

    btn1 = Button(text='Меню', command=return_on_click)
    btn1.place(x=15, y=220)
    btn2 = Button(text='Создать', command=next_on_click)
    btn2.place(x=165, y=220)
    root.mainloop()


class TransportTask:
    def __init__(self, m, n, price_list, count_list, sum_list):
        self.m = m
        self.n = n
        self.price_list = price_list
        self.count_list = count_list
        self.sum_list = sum_list
        self.restriction_list = []
        self.insert_lists = [self.price_list]

    @staticmethod
    def run_a_loop(loop_list, i, j, a, b, count_of_cycle, m):
        loop_list[i + j * m] += count_of_cycle
        loop_list[a + j * m] -= count_of_cycle
        loop_list[a + b * m] += count_of_cycle
        loop_list[i + b * m] -= count_of_cycle
        return loop_list

    def insert_data(self, data_insert, sum_insert):
        lists = self.insert_lists
        for i in range(len(lists)):
            for j in range(len(lists[i])):
                lists[i][j].delete(0, 'end')
                lists[i][j].insert(0, str(data_insert[i][j]))
        for i in range(len(self.sum_list)):
            self.sum_list[i].delete(0, 'end')
            self.sum_list[i].insert(0, str(sum_insert[i]))

    def set_plan(self):
        m, n = self.m, self.n
        c_int = [int(i.get()) for i in self.count_list]
        s_int = [int(i.get()) for i in self.sum_list]
        if sum(s_int[:m]) != sum(s_int[m:]):
            showinfo(title="Ошибка", message="Данная задача открыта.")
            return False

    def optimize(self):
        m, n = self.m, self.n
        c_int = [int(i.get()) for i in self.count_list]
        s_int = [int(i.get()) for i in self.sum_list]
        if sum(s_int[:m]) != sum(s_int[m:]):
            showinfo(title="Ошибка", message="Данная задача открыта.")
            return False
        for i in range(m):
            sum_el = 0
            for j in range(n):
                try:
                    sum_el += c_int[i + j * m]
                except ValueError:
                    sum_el += 0
            if s_int[i] < sum_el:
                showinfo(title="Ошибка", message="Присутствуют значения больше необходимого.")
                return False
            elif s_int[i] > sum_el:
                showinfo(title="Ошибка", message="Присутствуют значения меньше необходимого.")
                return False


class UnrestrictedTask(TransportTask):
    def set_plan(self):
        super().set_plan()
        m, n = self.m, self.n
        c_int = [0 for _ in range(m * n)]
        s_int = [int(i.get()) for i in self.sum_list]
        i, j = 0, 0
        while i < m or j < n:
            c_int[i + j * m] = min(s_int[i], s_int[m + j])
            s_int[i] -= c_int[i + j * m]
            s_int[m + j] -= c_int[i + j * m]
            if sum(s_int) == 0:
                break
            if s_int[i] == 0:
                i += 1
            if s_int[m + j] == 0:
                j += 1
        for k in range(len(self.count_list)):
            self.count_list[k].delete(0, 'end')
            self.count_list[k].insert(0, str(c_int[k]))

    def optimize(self):
        super().optimize()
        m, n = self.m, self.n
        p_int = [int(i.get()) for i in self.price_list]
        c_int = [int(i.get()) for i in self.count_list]
        s_int = [int(i.get()) for i in self.sum_list]

        def set_max_counter(c_int, s_int):
            max_counter = [0 for _ in range(m * n)]
            for i in range(m):
                for j in range(n):
                    if c_int[i + j * m] == s_int[i] or c_int[i + j * m] == s_int[m + j]:
                        max_counter[i + j * m] = 1
            return max_counter

        def make_step(cost, c_int, t, i, j, a, b):
            count_of_cycle = 0
            max_counter = set_max_counter(c_int, s_int)
            if cost < 0 and max_counter[i + j * m] != 1 and max_counter[a + b * m] != 1 and c_int[a + j * m] > 0 and c_int[i + b * m] > 0:
                count_of_cycle = min(c_int[a + j * m], c_int[i + b * m])
                if count_of_cycle > 0:
                    c_int = self.run_a_loop(c_int, i, j, a, b, count_of_cycle, m)
                    t = True
            return c_int, t
        t = True
        while t:
            t = False
            for i in range(m - 1):
                for j in range(n - 1):
                    for a in range(i + 1, m):
                        for b in range(j + 1, n):
                            cost = p_int[i + j * m] - p_int[a + j * m] + p_int[a + b * m] - p_int[i + b * m]
                            c_int, t = make_step(cost, c_int, t, i, j, a, b)
                            c_int, t = make_step(-cost, c_int, t, a, j, i, b)
        for k in range(len(self.count_list)):
            self.count_list[k].delete(0, 'end')
            self.count_list[k].insert(0, str(c_int[k]))

    def generate_and_insert(self):
        generated_data = generate(self.m, self.n, [[5, 100]])
        self.insert_data(generated_data[0], generated_data[1])


class SupplyRestrictedTask(TransportTask):
    def __init__(self, m, n, restriction_list, price_list, count_list, sum_list):
        super().__init__(m, n, price_list, count_list, sum_list)
        self.restriction_list = restriction_list
        self.insert_lists = [self.restriction_list, self.price_list]

    def set_plan(self):
        super().set_plan()
        m, n = self.m, self.n
        r_int = [int(i.get()) for i in self.restriction_list]
        c_int = [0 for _ in range(m * n)]
        s_int = [int(i.get()) for i in self.sum_list]

        i, j = 0, 0
        while i < m or j < n:
            c_int[i + j * m] = min(s_int[i], s_int[m + j], r_int[i + j * m])
            s_int[i] -= c_int[i + j * m]
            s_int[m + j] -= c_int[i + j * m]
            if sum(s_int) == 0:
                break
            i += 1
            if i == m:
                i = 0
                j += 1
            if j == n:
                break

        if sum(s_int) != 0:
            s_int2 = [int(i.get()) for i in self.sum_list]
            max_counter = [0 for _ in range(m * n)]
            for i in range(m):
                for j in range(n):
                    if (c_int[i + j * m] == s_int2[i] or
                            c_int[i + j * m] == s_int2[m + j] or
                            c_int[i + j * m] == r_int[i + j * m]):
                        max_counter[i + j * m] = 1
            for x in range(n - 1):
                for y in range(m - 1):
                    for j in range(1, n):
                        for i in range(1, m):
                            if c_int[i + j * m] > 0 and max_counter[y + j * m] != 1 and max_counter[i + x * m] != 1 and s_int[y] != 0 and s_int[m + x] != 0:
                                count_of_cycle = min(
                                    c_int[i + j * m],
                                    s_int[y], s_int[m + x],
                                    r_int[y + j * m] - c_int[y + j * m],
                                    r_int[i + x * m] - c_int[i + x * m]
                                )
                                if count_of_cycle > 0:
                                    c_int = self.run_a_loop(c_int, i, j, x, y, count_of_cycle, m)
                                    s_int[y] -= count_of_cycle
                                    s_int[m + j] -= count_of_cycle

        for k in range(len(self.count_list)):
            self.count_list[k].delete(0, 'end')
            self.count_list[k].insert(0, str(c_int[k]))

    def optimize(self):
        super().optimize()
        m, n = self.m, self.n
        r_int = [int(i.get()) for i in self.restriction_list]
        p_int = [int(i.get()) for i in self.price_list]
        c_int = [int(i.get()) for i in self.count_list]
        s_int = [int(i.get()) for i in self.sum_list]

        for i in range(len(r_int)):
            if r_int[i] < c_int[i]:
                showinfo(title="Ошибка", message="Присутствуют значения, превышающие ограничения.")
                return False

        def set_max_counter(c_int, s_int, r_int):
            max_counter = [0 for _ in range(m * n)]
            for i in range(m):
                for j in range(n):
                    if c_int[i + j * m] == s_int[i] or c_int[i + j * m] == s_int[m + j] or c_int[i + j * m] == r_int[i + j * m]:
                        max_counter[i + j * m] = 1
            return max_counter

        def make_step(cost, c_int, t, i, j, a, b):
            max_counter = set_max_counter(c_int, s_int, r_int)
            if cost < 0 and max_counter[i + j * m] != 1 and max_counter[a + b * m] != 1 and c_int[a + j * m] > 0 and c_int[i + b * m] > 0:
                count_of_cycle = min(c_int[a + j * m], c_int[i + b * m],
                                     r_int[i + j * m] - c_int[i + j * m],
                                     r_int[a + b * m] - c_int[a + b * m])
                if count_of_cycle > 0:
                    c_int = self.run_a_loop(c_int, i, j, a, b, count_of_cycle, m)
                    t = True
            return c_int, t
        t = True
        while t:
            t = False
            for i in range(m - 1):
                for j in range(n - 1):
                    for a in range(i + 1, m):
                        for b in range(j + 1, n):
                            cost = p_int[i + j * m] - p_int[a + j * m] + p_int[a + b * m] - p_int[i + b * m]
                            c_int, t = make_step(cost, c_int, t, i, j, a, b)
                            c_int, t = make_step(-cost, c_int, t, a, j, i, b)
        for k in range(len(self.count_list)):
            self.count_list[k].delete(0, 'end')
            self.count_list[k].insert(0, str(c_int[k]))

    def generate_and_insert(self):
        generated_data = generate(self.m, self.n, [[5, 100], [0, 100, True]])
        self.insert_data(generated_data[0], generated_data[1])


class TimeRestrictedTask(TransportTask):
    def __init__(self, m, n, restriction_list, price_list, count_list, sum_list):
        super().__init__(m, n, price_list, count_list, sum_list)
        self.restriction_list = restriction_list
        self.insert_lists = [self.restriction_list, self.price_list]

    def set_plan(self):
        super().set_plan()
        m, n = self.m, self.n
        r_int = [int(i.get()) for i in self.restriction_list]
        c_int = [0 for _ in range(m * n)]
        s_int = [int(i.get()) for i in self.sum_list]
        i, j = 0, 0
        while i < m or j < n:
            if r_int[i + j * m] > time_param:
                i += 1
                if i == m:
                    i = 0
                    j += 1
                if j == n:
                    break
            c_int[i + j * m] = min(s_int[i], s_int[m + j])
            s_int[i] -= c_int[i + j * m]
            s_int[m + j] -= c_int[i + j * m]
            i += 1
            if i == m:
                i = 0
                j += 1
            if j == n:
                break
        for k in range(len(self.count_list)):
            self.count_list[k].delete(0, 'end')
            self.count_list[k].insert(0, str(c_int[k]))

    def optimize(self):
        super().optimize()
        m, n = self.m, self.n
        r_int = [int(i.get()) for i in self.restriction_list]
        p_int = [int(i.get()) for i in self.price_list]
        c_int = [int(i.get()) for i in self.count_list]
        s_int = [int(i.get()) for i in self.sum_list]

        def set_max_counter(c_int2):
            max_counter = [0 for _ in range(m * n)]
            for i in range(m):
                for j in range(n):
                    if c_int2[i + j * m] == s_int[i] or c_int[i + j * m] == s_int[m + j]:
                        max_counter[i + j * m] = 1
            return max_counter

        def make_step(cost, c_int, t, i, j, a, b, type_list=None):
            max_counter = set_max_counter(c_int)
            global time_param
            max_time = max([r_int[i] if c_int[i] != 0 else 0 for i in range(len(r_int))])
            if not type_list:
                print(cost, max_counter[i + j * m], max_counter[a + b * m], c_int[a + j * m], c_int[i + b * m])
            if cost < 0 and max_counter[i + j * m] != 1 and max_counter[a + b * m] != 1 and c_int[a + j * m] > 0 and c_int[i + b * m] > 0:
                if r_int[i + j * m] > time_param or r_int[a + b * m] > time_param:
                    return c_int, max_time, t
                if type_list:
                    if 'время' in type_list:
                        count_of_cycle = min(r_int[a + j * m], r_int[i + b * m])
                    else:
                        count_of_cycle = min(c_int[a + j * m], c_int[i + b * m])
                else:
                    count_of_cycle = min(c_int[a + j * m], c_int[i + b * m])
                if count_of_cycle > 0:
                    c_int = self.run_a_loop(c_int, i, j, a, b, count_of_cycle, m)

                    if not type_list:
                        print(c_int)
                        t = True
            return c_int, max_time, t

        def find_best_plan_two(r_int, c_int, t, time_max, time_min, sum_max, sum_min):

            def find_target_f(c_int):
                global c_param, t_param
                current_sum, current_time = 0, 0
                if abs(sum_min - sum_max) != 0:
                    current_sum = (sum([p_int[i] * c_int[i] for i in range(len(p_int))]) - min(sum_min, sum_max)) / abs(sum_min - sum_max)
                if abs(time_min - time_max) != 0:
                    current_time = (max([r_int[i] for i in range(len(r_int)) if c_int[i] != 0]) - min(time_min, time_max)) / abs(time_min - time_max)
                print(c_param, current_sum, t_param, current_time)
                return c_param * current_sum + t_param * current_time

            print('Максимальное максимальное время:', max(time_min, time_max))
            print('Минимальное максимальное время:', min(time_min, time_max))
            print('Максимальная стоимость:', max(sum_min, sum_max))
            print('Минимальная стоимость:', min(sum_min, sum_max))

            for i in range(m - 1):
                for j in range(n - 1):
                    for a in range(i + 1, m):
                        for b in range(j + 1, n):
                            current_sum = find_target_f(c_int)
                            c_int_two = self.run_a_loop(c_int.copy(), i, j, a, b, 1, m)
                            c_int_three = self.run_a_loop(c_int.copy(), a, j, i, b, 1, m)
                            cost_p = p_int[i + j * m] - p_int[a + j * m] + p_int[a + b * m] - p_int[i + b * m]
                            cost_r = r_int[i + j * m] - r_int[a + j * m] + r_int[a + b * m] - r_int[i + b * m]
                            cost = min(cost_r, cost_p)
                            print(cost_p, cost_r)
                            print("target_f 1")
                            current_sum_two = find_target_f(c_int_two)
                            print("target_f 2")
                            current_sum_three = find_target_f(c_int_three)
                            print("sums", current_sum, current_sum_two, current_sum_three)
                            if current_sum_two >= current_sum_three and min(c_int_three) >= 0:
                                print(c_int_three)
                                if current_sum >= current_sum_three:
                                    c_int, max_time, t = make_step(cost, c_int, t, a, j, i, b)
                                    print(1.1, c_int)
                                    c_int, max_time, t = make_step(-cost, c_int, t, a, j, i, b)
                                    print(1.2, c_int)
                            elif current_sum_three >= current_sum_two and min(c_int_two) >= 0:
                                print(c_int_two)
                                if current_sum >= current_sum_two:
                                    c_int, max_time, t = make_step(cost, c_int, t, i, j, a, b)
                                    print(2.1, c_int)
                                    c_int, max_time, t = make_step(-cost, c_int, t, i, j, a, b)
                                    print(2.2, c_int)
            return c_int, t

        def for_find_best_plan():

            def find_max_time(cost, c_int_max_t, t, i, j, a, b):
                c_int_max_t, max_time, t = make_step(abs(cost), c_int_max_t, t, i, j, a, b, 'время')
                return c_int_max_t, t

            def find_min_time(cost, c_int_min_t, t, i, j, a, b):
                c_int_min_t, max_time, t = make_step(-abs(cost), c_int_min_t, t, i, j, a, b, 'время')
                return c_int_min_t, t

            def find_max_price_mul(cost, c_int_max_p, t, i, j, a, b):
                c_int_max_p, max_time, t = make_step(abs(cost), c_int_max_p, t, i, j, a, b, 'стоимость')
                return c_int_max_p, t

            def find_min_price_mul(cost, c_int_min_p, t, i, j, a, b):
                c_int_min_p, max_time, t = make_step(-abs(cost), c_int_min_p, t, i, j, a, b, 'стоимость')
                return c_int_min_p, t

            t = 1
            c_int_max_t, c_int_min_t, c_int_max_p, c_int_min_p = c_int.copy(), c_int.copy(), c_int.copy(), c_int.copy()

            while t:
                t = 0
                for i in range(m - 1):
                    for j in range(n - 1):
                        for a in range(i + 1, m):
                            for b in range(j + 1, n):
                                cost = p_int[i + j * m] - p_int[a + j * m] + p_int[a + b * m] - p_int[i + b * m]
                                c_int_max_t, t1 = find_max_time(cost, c_int_max_t, t, i, j, a, b)
                                c_int_max_t, t2 = find_max_time(cost, c_int_max_t, t, a, j, i, b)
                                c_int_max_p, t3 = find_max_price_mul(cost, c_int_max_p, t, i, j, a, b)
                                c_int_max_p, t4 = find_max_price_mul(cost, c_int_max_p, t, a, j, i, b)
                                c_int_min_t, t5 = find_min_time(cost, c_int_min_t, t, i, j, a, b)
                                c_int_min_t, t6 = find_min_time(cost, c_int_min_t, t, a, j, i, b)
                                c_int_min_p, t7 = find_min_price_mul(cost, c_int_min_p, t, i, j, a, b)
                                c_int_min_p, t8 = find_min_price_mul(cost, c_int_min_p, t, a, j, i, b)
                                t += t1 + t2 + t3 + t4 + t5 + t6 + t7 + t8
            return c_int_max_t, c_int_min_t, c_int_max_p, c_int_min_p

        def optimize_sums(c_int_max_t, c_int_min_t, c_int_max_p, c_int_min_p):
            global c_param, t_param
            time_max = max([r_int[i] for i in range(len(c_int_max_t)) if c_int_max_t[i] != 0])
            time_min = max([r_int[i] for i in range(len(c_int_min_t)) if c_int_min_t[i] != 0])
            sum_max = sum([p_int[i] * c_int_max_p[i] for i in range(len(c_int_max_p))])
            sum_min = sum([p_int[i] * c_int_min_p[i] for i in range(len(c_int_min_p))])
            return time_max, time_min, sum_max, sum_min

        time_max, time_min, sum_max, sum_min = 0, 0, 0, 0
        c_int_max_t, c_int_min_t, c_int_max_p, c_int_min_p = for_find_best_plan()
        time_max, time_min, sum_max, sum_min = optimize_sums(c_int_max_t, c_int_min_t, c_int_max_p, c_int_min_p)

        k = 0
        t = True
        while t or k != 2:
            t = False
            k += 1
            c_int, t = find_best_plan_two(r_int, c_int, t, time_max, time_min, sum_max, sum_min)
            print('Текущая сумма', sum([p_int[i] * c_int[i] for i in range(len(p_int))]))
            print('Текущее время', max([r_int[i] for i in range(len(r_int)) if c_int[i] != 0]))
            global c_param, t_param
            print('Коэффициент суммы:', c_param)
            print('Коэффициент времени:', t_param)
            print('Сум + Вр:', c_param * sum([p_int[i] * c_int[i] for i in range(len(p_int))]),
                  t_param * max([r_int[i] for i in range(len(r_int)) if c_int[i] != 0]))
            print('-------------------------')
        for k in range(len(self.count_list)):
            self.count_list[k].delete(0, 'end')
            self.count_list[k].insert(0, str(c_int[k]))

    def generate_and_insert(self):
        generated_data = generate(self.m, self.n, [[5, 100], [5, 100]])
        self.insert_data(generated_data[0], generated_data[1])


class FitInTimeTask(TransportTask):
    def __init__(self, m, n, restriction_list, price_list, count_list, sum_list):
        super().__init__(m, n, price_list, count_list, sum_list)
        self.restriction_list = restriction_list
        self.insert_lists = [self.restriction_list]

    def set_plan(self):
        super().set_plan()
        m, n = self.m, self.n
        r_int = [int(i.get()) for i in self.restriction_list]
        c_int = [0 for _ in range(m * n)]
        s_int = [int(i.get()) for i in self.sum_list]
        print(r_int)
        i, j = 0, 0
        while i < m or j < n:
            if r_int[i + j * m] > time_param:
                i += 1
                if i == m:
                    i = 0
                    j += 1
                if j == n:
                    break
            c_int[i + j * m] = min(s_int[i], s_int[m + j])
            s_int[i] -= c_int[i + j * m]
            s_int[m + j] -= c_int[i + j * m]
            if sum(s_int) == 0:
                break
            i += 1
            if i == m:
                i = 0
                j += 1
            if j == n:
                break
        for k in range(len(self.count_list)):
            self.count_list[k].delete(0, 'end')
            self.count_list[k].insert(0, str(c_int[k]))

    def optimize(self):
        super().optimize()
        m, n = self.m, self.n
        p_int = [int(i.get()) for i in self.restriction_list]
        c_int = [int(i.get()) for i in self.count_list]
        s_int = [int(i.get()) for i in self.sum_list]

        def set_max_counter(c_int, s_int):
            max_counter = [0 for _ in range(m * n)]
            for i in range(m):
                for j in range(n):
                    if c_int[i + j * m] == s_int[i] or c_int[i + j * m] == s_int[m + j]:
                        max_counter[i + j * m] = 1
            return max_counter

        def make_step(cost, c_int, t, i, j, a, b):
            max_counter = set_max_counter(c_int, s_int)
            if cost < 0 and max_counter[i + j * m] != 1 and max_counter[a + b * m] != 1 and c_int[a + j * m] > 0 and c_int[i + b * m] > 0:
                # Ограничение по времени
                if p_int[i + j * m] > time_param or p_int[a + b * m] > time_param:
                    return c_int, t
                count_of_cycle = min(c_int[a + j * m], c_int[i + b * m])
                if count_of_cycle > 0:
                    c_int = self.run_a_loop(c_int, i, j, a, b, count_of_cycle, m)
                    t = True
            return c_int, t
        t = True
        while t:
            t = False
            for i in range(m - 1):
                for j in range(n - 1):
                    for a in range(i + 1, m):
                        for b in range(j + 1, n):
                            cost = p_int[i + j * m] - p_int[a + j * m] + p_int[a + b * m] - p_int[i + b * m]
                            c_int, t = make_step(cost, c_int, t, i, j, a, b)
                            c_int, t = make_step(-cost, c_int, t, a, j, i, b)
        for k in range(len(self.count_list)):
            self.count_list[k].delete(0, 'end')
            self.count_list[k].insert(0, str(c_int[k]))

    def generate_and_insert(self):
        generated_data = generate(self.m, self.n, [[5, 100]])
        self.insert_data(generated_data[0], generated_data[1])


def main_window(status, m, n, data_to_insert=None):
    main = Tk()
    main.geometry(f'{240 + 152 * m}x{50 + 36 * n}+500+300')

    def make_form_of_table(main, m, n, status):
        global time_param
        # ширина ячеек
        w = 12
        # название окна
        if status in ['время', 'стоимость и время']:
            main.title(f"Таблица по параметру: {status} " + str(time_param))
        else:
            main.title(f"Таблица по параметру: {status}")
        param_l = Label(main, width=w + 10)
        if status in 'время':
            window_height = 6
        elif status == 'стоимость и время':
            window_height = 7
        else:
            window_height = 5
        calculate(param_l)
        param_l.grid(row=0, column=0)
        # создание окна действий с таблицей

        def make_param_window(status, window_height, param_l):
            main_o = Tk()
            main_o.title(f"")
            main_o.geometry(f'290x{window_height * 26}+200+300')

            if status == 'стоимость с ограничениями на количество':
                task = SupplyRestrictedTask(m, n, restriction_list, price_list, count_list, sum_list)
            elif status == 'стоимость и время':
                task = TimeRestrictedTask(m, n, restriction_list, price_list, count_list, sum_list)
            elif status == 'время':
                task = FitInTimeTask(m, n, restriction_list, price_list, count_list, sum_list)
            else:
                task = UnrestrictedTask(m, n, price_list, count_list, sum_list)

            Button(main_o, text='Рассчитать текущий план', command=lambda: calculate(param_l), width=40).grid(row=0, column=0)
            Button(main_o, text='Метод северо-западного угла', command=task.set_plan, width=40).grid(row=1, column=0)
            Button(main_o, text='Оптимизация методом циклов', command=task.optimize, width=40).grid(row=2, column=0)
            Button(main_o, text='Генерация данных', command=task.generate_and_insert, width=40).grid(row=3, column=0)
            row_n = 4
            if status in ['время', 'стоимость и время']:
                Button(main_o, text='Установить верхнюю границу времени', command=lambda: set_time(), width=40).grid(
                    row=4, column=0)
                row_n = 5
                if status == 'стоимость и время':
                    Button(main_o, text='Изменить соотношение параметров оптимизации', command=lambda: set_ratio(),
                           width=40).grid(
                        row=5, column=0)
                    row_n = 6

            def return_to_menu():
                main_o.destroy()
                main.destroy()
                show_start_window()

            Button(main_o, text='Меню', command=return_to_menu, width=40).grid(row=row_n, column=0)
            return task

        task = make_param_window(status, window_height, param_l)
        # создание первой строки
        for j in range(1, m + 1):
            l = Label(main, text=f'B{j}', width=w)
            l.grid(row=0, column=j * 2 - 1, columnspan=2)
            l.grid_configure(columnspan=2)
            l = Label(main, text="S", width=w)
            l.grid(row=n * 2 + 2, column=0)
            e = Entry(main, width=w * 2 + 1)
            e.insert(0, '0')
            e.grid(row=n * 2 + 2, column=j * 2 - 1, columnspan=2)
            e.config(validate="key", validatecommand=(e.register(callback), "%P"))
            sum_list.append(e)
        # создание первого столбца
        for i in range(1, n + 1):
            l = Label(main, text=f'A{i}', width=w)
            l.grid(row=i * 2 - 1, column=0, rowspan=2)
            l.grid_configure(rowspan=2)
            l = Label(main, text="S", width=w - 4)
            l.grid(row=0, column=m * 2 + 1)
            e = Entry(main, width=w)
            e.insert(0, '0')
            e.grid(row=i * 2 - 1, column=m * 2 + 1)
            e.config(validate="key", validatecommand=(e.register(callback), "%P"))
            sum_list.append(e)
        # создание основной части таблицы
        for j in range(1, n * 2 + 1):
            for i in range(1, m * 2 + 1):
                if (i + j) % 2 == 0:
                    if status in ['стоимость с ограничениями на количество', 'стоимость и время', 'время'] and i % 2 != 0:
                        e = Entry(main, width=w)
                        restriction_list.append(e)
                    else:
                        e = Entry(main, width=w, state='readonly')
                elif status == 'время':
                    if j % 2 == 0:
                        e = Entry(main, width=w)
                        count_list.append(e)
                    else:
                        e = Entry(main, width=w, state='readonly')
                else:
                    e = tk.Entry(main, width=w)
                    if i % 2 == 0:
                        price_list.append(e)
                    else:
                        count_list.append(e)
                e.insert(0, '0')
                e.config(validate="key", validatecommand=(e.register(callback), "%P"))
                if ((i - 1) // 2 + (j - 1) // 2) % 2 == 0:
                    e.configure(bg="#c5cce3", readonlybackground="#a5afd1")
                e.grid(row=j, column=i)
        return restriction_list, price_list, count_list, sum_list, task

    def calculate(param_l):
        max_time, sum_cost = 0, 0
        if status in ['стоимость и время', 'стоимость с ограничениями на количество', 'время']:
            first_counter = restriction_list
        else:
            first_counter = price_list
        if status == 'время':
            second_counter = restriction_list
        else:
            second_counter = price_list
        for i, j, o in zip(first_counter, second_counter, count_list):
            if status in ['время', 'стоимость и время']:
                if max_time < int(i.get()) and int(o.get()) != 0:
                    max_time = int(i.get())
            if status != 'время':
                sum_cost += int(j.get()) * int(o.get())
        if status == 'время':
            param_l.configure(text='Время: ' + str(max_time))
        elif status == 'стоимость и время':
            param_l.configure(text='Стоимость: ' + str(sum_cost) + ', Время: ' + str(max_time))
        else:
            param_l.configure(text='Стоимость: ' + str(sum_cost))

    def callback(symbol):
        if not symbol.isdigit() and symbol != "":
            return False
        return True

    def set_time():
        time_window = Tk()

        def time_button():
            global time_param
            time_param = int(e.get())
            main.title(f"Таблица по параметру: {status} " + str(time_param))
            time_window.destroy()

        Label(time_window, text='Верхняя граница времени', width=20).grid(row=0, column=0)
        global time_param
        e = Entry(time_window, width=24)
        e.insert(0, str(time_param))
        e.grid(row=1, column=0)
        e.config(validate="key", validatecommand=(e.register(callback), "%P"))

        b = Button(time_window, text='ОК', command=lambda: time_button(), width=20)
        b.grid(row=2, column=0)

        time_window.mainloop()

    def set_ratio():
        ratio_window = Tk()
        ratio_window.geometry("200x100")

        def update_values(event):
            value = scale.get()
            value2 = 100 - value
            value_label.config(text=f"Коэффициент стоимости: {round(value / 100, 2)}")
            value2_label.config(text=f"Коэффициент времени: {round(value2 / 100, 2)}")

        def set_values():
            value = scale.get()
            value2 = 100 - value
            global c_param, t_param
            c_param = round(value / 100, 2)
            t_param = round(value2 / 100, 2)
            ratio_window.destroy()

        global c_param, t_param

        value_label = tk.Label(ratio_window, text=f"Коэффициент стоимости: {c_param}")
        value_label.pack()
        value2_label = tk.Label(ratio_window, text=f"Коэффициент времени: {t_param}")
        value2_label.pack()

        scale = ttk.Scale(ratio_window, from_=0, to=100, orient=tk.HORIZONTAL, command=update_values)
        scale.pack()
        scale.set(c_param * 100)

        print_button = tk.Button(ratio_window, text="ОК", command=set_values)
        print_button.pack()
        ratio_window.mainloop()

    # списки: ограничения, цены, количество, суммы по столбцам и строкам
    restriction_list, price_list, count_list, sum_list = [], [], [], []
    restriction_list, price_list, count_list, sum_list, task = make_form_of_table(main, m, n, status)
    if data_to_insert is not None:
        task.insert_data(data_to_insert[0], data_to_insert[1])
    main.mainloop()


if __name__ == "__main__":
    show_start_window()


























