import random


def generate(m, n, interval_lists, printing=False):
    count_list = [0 for _ in range(m * n)]
    sum_list = [random.randint(1, 100) for _ in range(m)]
    sum_list_2 = []
    j = 0
    while j != n - 1:
        try:
            sum_list_2.append(random.randint(1, min(100, sum(sum_list) - sum(sum_list_2) - (n - 1 - j))))
            j += 1
        except ValueError:
            sum_list_2.append(1)
            j += 1
    sum_list_2.append(sum(sum_list) - sum(sum_list_2))
    sum_list = sum_list + sum_list_2

    matrix_list = []
    for i in range(len(interval_lists)):
        if len(interval_lists[i]) == 2:
            matrix_list.append([random.randint(interval_lists[i][0], interval_lists[i][1]) for _ in range(m * n)])
        elif len(interval_lists[i]) == 3 and interval_lists[i][2] is True:
            res_list = [0 for _ in range(m * n)]
            for k in range(n):
                for j in range(m):
                    if m * k + j == n * m - 1:
                        for_column = sum_list[j] - sum([min(res_list[z * m + j], sum_list[m + k]) for z in range(n)])
                        for_row = sum_list[m + k] - sum([min(res_list[k * m + z], sum_list[j]) for z in range(m)])
                        res_list[j + m * k] = random.randint(max(interval_lists[i][0], for_row, for_column), interval_lists[i][1])
                    elif (m * k + j) % m == m - 1:
                        for_row = sum_list[m + k] - sum([min(res_list[k * m + z], sum_list[j]) for z in range(m)])
                        res_list[j + m * k] = random.randint(max(interval_lists[i][0], for_row), interval_lists[i][1])
                    elif (m * k + j) >= m * (n - 1):
                        for_column = sum_list[j] - sum([min(res_list[z * m + j], sum_list[m + k]) for z in range(n)])
                        res_list[j + m * k] = random.randint(max(interval_lists[i][0], for_column), interval_lists[i][1])
                    else:
                        res_list[j + m * k] = random.randint(interval_lists[i][0], interval_lists[i][1])
            matrix_list.append(res_list)

    if printing:
        print("Размерность: ", m, n)
        print("Потребности и запасы: ", sum_list)
        for i in matrix_list:
            print(f"Матрица {matrix_list.index(i) + 1}: ", i)
        print("Количество: ", count_list)
    return matrix_list, sum_list


if __name__ == "__main__":
    m, s, = generate(4, 3, [(0, 100), (5, 100, True)], True)
    print(m, s)
