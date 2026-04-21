import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import psycopg2
from psycopg2.extras import RealDictCursor
from prettytable import PrettyTable
import sys

class DatabaseManager:
    def __init__(self, dbname, user, password, host="localhost", port="5432"):
        try:
            self.conn = psycopg2.connect(
                dbname=dbname, user=user, password=password, host=host, port=port
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Критическая ошибка подключения к БД:\n{e}")
            sys.exit(1)

    def close(self):
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def get_employees(self, limit=20):
        query = """
            SELECT e.employee_id, e.full_name, e.position, e.phone, b.adress AS branch_address 
            FROM employees e
            JOIN branches b ON e.branch_id = b.branch_id
            ORDER BY e.employee_id DESC LIMIT %s;
        """
        self.cursor.execute(query, (limit,))
        return self.cursor.fetchall()

    def add_employee(self, full_name, position, address, phone, branch_id):
        query = """
            INSERT INTO employees (full_name, position, address, phone, branch_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING employee_id;
        """
        self.cursor.execute(query, (full_name, position, address, phone, branch_id))
        return self.cursor.fetchone()['employee_id']

    def update_employee_position(self, employee_id, new_position):
        query = "UPDATE employees SET position = %s WHERE employee_id = %s"
        self.cursor.execute(query, (new_position, employee_id))
        return self.cursor.rowcount

    def delete_employee(self, employee_id):
        query = "DELETE FROM employees WHERE employee_id = %s"
        self.cursor.execute(query, (employee_id,))
        return self.cursor.rowcount

    def get_branches(self):
        self.cursor.execute("SELECT branch_id, adress FROM branches ORDER BY branch_id;")
        return self.cursor.fetchall()

    def analytics_transfers_by_date(self, start_date, end_date):
        query = """
            SELECT cr.card_number, t.amount, t.operation_time 
            FROM cards cr JOIN transactions t ON cr.card_id = t.card_id 
            WHERE t.operation_time BETWEEN %s AND %s
            ORDER BY t.operation_time DESC LIMIT 20;
        """
        self.cursor.execute(query, (start_date, end_date))
        return self.cursor.fetchall()

    def analytics_top_loans(self, min_rate):
        query = """
            SELECT l.contract_number, e.full_name AS manager, l.debt_amount, l.interest_rate
            FROM loans l JOIN employees e ON l.employee_id = e.employee_id 
            WHERE REPLACE(l.interest_rate, '%%', '')::numeric > %s
            ORDER BY l.debt_amount DESC LIMIT 15;
        """
        self.cursor.execute(query, (min_rate,))
        return self.cursor.fetchall()

class AppGUI:

    def __init__(self, root, db_manager):
        self.root = root
        self.db = db_manager
        self.root.title("Банковская БД ")
        self.root.geometry("900x650")
        self.root.configure(bg="#f0f0f0")

        # Верхняя область (80%) для вывода
        self.top_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Используем моноширинный шрифт чтобы таблички не ехали
        self.text_output = tk.Text(self.top_frame, font=("Consolas", 10), bg="#1e1e1e", fg="#00ff00", wrap=tk.NONE)
        self.text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Скроллбары для текстового поля
        v_scroll = ttk.Scrollbar(self.top_frame, orient=tk.VERTICAL, command=self.text_output.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.text_output.xview)
        h_scroll.pack(side=tk.TOP, fill=tk.X, padx=10)
        self.text_output.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        #  Нижняя область (20%) для кнопок
        self.bottom_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.create_buttons()
        self.out_msg("Добро пожаловать в систему управления банковской БД!\nВыберите действие на панели ниже.")

    def create_buttons(self):
        # Настройка стиля кнопок
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 10), padding=5)

        # Сетка кнопок
        btn_read = ttk.Button(self.bottom_frame, text="Список сотрудников (READ)", command=self.action_read)
        btn_create = ttk.Button(self.bottom_frame, text="Добавить сотрудника (CREATE)", command=self.action_create)
        btn_update = ttk.Button(self.bottom_frame, text="Изменить должность (UPDATE)", command=self.action_update)
        btn_delete = ttk.Button(self.bottom_frame, text="Уволить сотрудника (DELETE)", command=self.action_delete)

        btn_analytics1 = ttk.Button(self.bottom_frame, text="Аналитика: Переводы", command=self.action_analytics_1)
        btn_analytics2 = ttk.Button(self.bottom_frame, text="Аналитика: Кредиты", command=self.action_analytics_2)
        btn_clear = ttk.Button(self.bottom_frame, text="Clear (Очистить вывод)", command=self.clear_output)

        # Размещение кнопок
        btn_read.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        btn_create.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        btn_update.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        btn_delete.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        btn_analytics1.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        btn_analytics2.grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="ew")

        btn_clear.grid(row=2, column=0, columnspan=4, padx=5, pady=10, sticky="ew")

        # Растягиваем колонки равномерно
        for i in range(4):
            self.bottom_frame.columnconfigure(i, weight=1)

    # --- Функции вывода ---
    def clear_output(self):
        self.text_output.delete(1.0, tk.END)

    def out_msg(self, msg):
        self.text_output.insert(tk.END, msg + "\n")
        self.text_output.see(1.0)  # Автоскролл вверх

    def format_and_print_table(self, data, columns, headers, title=""):
        self.clear_output()
        if not data:
            self.out_msg(f">>> {title}\nДанные не найдены.")
            return

        table = PrettyTable(headers)
        table.align = "l"
        for row in data:
            table.add_row([row[col] for col in columns])

        if title:
            self.out_msg(f"=== {title} ===\n")
        self.out_msg(table.get_string())

    # --- Экшены для кнопок ---
    def action_read(self):
        data = self.db.get_employees()
        self.format_and_print_table(
            data,
            ['employee_id', 'full_name', 'position', 'phone', 'branch_address'],
            ['ID', 'ФИО', 'Должность', 'Телефон', 'Адрес отделения'],
            "Последние 20 добавленных сотрудников"
        )

    def action_create(self):
        # Показываем справочник отделений в фоне
        branches = self.db.get_branches()
        self.format_and_print_table(branches, ['branch_id', 'adress'], ['ID', 'Адрес'], "Справочник отделений")

        name = simpledialog.askstring("Добавление", "Введите ФИО:", parent=self.root)
        if not name: return
        pos = simpledialog.askstring("Добавление", "Введите должность:", parent=self.root)
        addr = simpledialog.askstring("Добавление", "Введите домашний адрес:", parent=self.root)
        phone = simpledialog.askstring("Добавление", "Введите телефон (+7...):", parent=self.root)
        branch_id = simpledialog.askinteger("Добавление", "Введите ID отделения (список в главном окне):",
                                            parent=self.root)

        if all([name, pos, addr, phone, branch_id]):
            try:
                new_id = self.db.add_employee(name, pos, addr, phone, branch_id)
                messagebox.showinfo("Успех", f"Сотрудник добавлен!\nПрисвоен ID: {new_id}")
                self.action_read()  # Сразу обновляем таблицу
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def action_update(self):
        emp_id = simpledialog.askinteger("Обновление", "Введите ID сотрудника:", parent=self.root)
        if emp_id:
            new_pos = simpledialog.askstring("Обновление", "Введите новую должность:", parent=self.root)
            if new_pos:
                rows = self.db.update_employee_position(emp_id, new_pos)
                if rows > 0:
                    messagebox.showinfo("Успех", "Должность успешно обновлена!")
                    self.action_read()
                else:
                    messagebox.showwarning("Внимание", "Сотрудник с таким ID не найден.")

    def action_delete(self):
        emp_id = simpledialog.askinteger("Увольнение", "Введите ID сотрудника для увольнения:", parent=self.root)
        if emp_id:
            confirm = messagebox.askyesno("Подтверждение", f"Вы точно хотите удалить сотрудника с ID {emp_id}?")
            if confirm:
                rows = self.db.delete_employee(emp_id)
                if rows > 0:
                    messagebox.showinfo("Успех", "Сотрудник удален из базы.")
                    self.action_read()
                else:
                    messagebox.showwarning("Внимание", "Сотрудник с таким ID не найден.")

    def action_analytics_1(self):
        start = simpledialog.askstring("Аналитика 1", "Начальная дата (ГГГГ-ММ-ДД):", parent=self.root)
        if not start: return
        end = simpledialog.askstring("Аналитика 1", "Конечная дата (ГГГГ-ММ-ДД):", parent=self.root)
        if not end: return

        data = self.db.analytics_transfers_by_date(start, end)
        self.format_and_print_table(
            data,
            ['card_number', 'amount', 'operation_time'],
            ['Номер карты', 'Сумма', 'Дата и время'],
            f"Переводы с {start} по {end}"
        )

    def action_analytics_2(self):
        rate = simpledialog.askfloat("Аналитика 2", "Минимальная процентная ставка (например, 15.5):", parent=self.root)
        if rate:
            data = self.db.analytics_top_loans(rate)
            self.format_and_print_table(
                data,
                ['contract_number', 'manager', 'debt_amount', 'interest_rate'],
                ['Номер договора', 'Выдавший менеджер', 'Сумма долга', 'Ставка'],
                f"Крупные кредиты со ставкой выше {rate}%"
            )


if __name__ == "__main__":
    # НАСТРОЙКИ БД
    db = DatabaseManager(
        dbname="Sber",
        user="postgres",
        password="555666",
        host="localhost",
        port="5432"
    )

    root = tk.Tk()
    app = AppGUI(root, db)

    # Закрываем соединение с БД при закрытии окна на крестик
    root.protocol("WM_DELETE_WINDOW", lambda: (db.close(), root.destroy()))

    root.mainloop()