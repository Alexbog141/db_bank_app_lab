import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import psycopg2
from psycopg2.extras import RealDictCursor
from prettytable import PrettyTable
import sys
import re


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

    # --- CRUD для Сотрудников ---
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

    # --- CRUD для Отделений ---
    def get_branches(self):
        self.cursor.execute("SELECT branch_id, adress, phone FROM branches ORDER BY branch_id;")
        return self.cursor.fetchall()

    def add_branch(self, address, phone):
        query = "INSERT INTO branches (adress, phone) VALUES (%s, %s) RETURNING branch_id;"
        self.cursor.execute(query, (address, phone))
        return self.cursor.fetchone()['branch_id']

    def update_branch(self, branch_id, address):
        query = "UPDATE branches SET adress = %s WHERE branch_id = %s;"
        self.cursor.execute(query, (address, branch_id))
        return self.cursor.rowcount

    def delete_branch(self, branch_id):
        query = "DELETE FROM branches WHERE branch_id = %s;"
        self.cursor.execute(query, (branch_id,))
        return self.cursor.rowcount

    # --- Аналитика ---
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
        self.root.title("Банковская БД (Папсуев А.А. IVT-261)")
        self.root.geometry("1000x750")
        self.root.configure(bg="#f0f0f0")

        self.top_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.text_output = tk.Text(self.top_frame, font=("Consolas", 10), bg="#1e1e1e", fg="#00ff00", wrap=tk.NONE)
        self.text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        v_scroll = ttk.Scrollbar(self.top_frame, orient=tk.VERTICAL, command=self.text_output.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.text_output.xview)
        h_scroll.pack(side=tk.TOP, fill=tk.X, padx=10)
        self.text_output.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.bottom_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.create_buttons()
        self.out_msg("Система управления банковской БД готова к работе.")

    def create_buttons(self):
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 9), padding=5)

        # Ряд 0: Сотрудники
        ttk.Button(self.bottom_frame, text="Сотрудники (R)", command=self.action_read).grid(row=0, column=0, padx=5,
                                                                                            pady=5, sticky="ew")
        ttk.Button(self.bottom_frame, text="Нанять (C)", command=self.action_create).grid(row=0, column=1, padx=5,
                                                                                          pady=5, sticky="ew")
        ttk.Button(self.bottom_frame, text="Должность (U)", command=self.action_update).grid(row=0, column=2, padx=5,
                                                                                             pady=5, sticky="ew")
        ttk.Button(self.bottom_frame, text="Уволить (D)", command=self.action_delete).grid(row=0, column=3, padx=5,
                                                                                           pady=5, sticky="ew")

        # Ряд 1: Отделения
        ttk.Button(self.bottom_frame, text="Отделения (R)", command=self.action_read_branches).grid(row=1, column=0,
                                                                                                    padx=5, pady=5,
                                                                                                    sticky="ew")
        ttk.Button(self.bottom_frame, text="Открыть филиал (C)", command=self.action_create_branch).grid(row=1,
                                                                                                         column=1,
                                                                                                         padx=5, pady=5,
                                                                                                         sticky="ew")
        ttk.Button(self.bottom_frame, text="Сменить адрес (U)", command=self.action_update_branch).grid(row=1, column=2,
                                                                                                        padx=5, pady=5,
                                                                                                        sticky="ew")
        ttk.Button(self.bottom_frame, text="Закрыть филиал (D)", command=self.action_delete_branch).grid(row=1,
                                                                                                         column=3,
                                                                                                         padx=5, pady=5,
                                                                                                         sticky="ew")

        # Ряд 2: Аналитика
        ttk.Button(self.bottom_frame, text="Аналитика: Переводы", command=self.action_analytics_1).grid(row=2, column=0,
                                                                                                        columnspan=2,
                                                                                                        padx=5, pady=5,
                                                                                                        sticky="ew")
        ttk.Button(self.bottom_frame, text="Аналитика: Топ кредитов", command=self.action_analytics_2).grid(row=2,
                                                                                                            column=2,
                                                                                                            columnspan=2,
                                                                                                            padx=5,
                                                                                                            pady=5,
                                                                                                            sticky="ew")

        # Ряд 3: Очистка
        ttk.Button(self.bottom_frame, text="Очистить экран", command=self.clear_output).grid(row=3, column=0,
                                                                                             columnspan=4, padx=5,
                                                                                             pady=10, sticky="ew")

        for i in range(4):
            self.bottom_frame.columnconfigure(i, weight=1)

    def clear_output(self):
        self.text_output.delete(1.0, tk.END)

    def out_msg(self, msg, scroll_to="1.0"):
        self.text_output.insert(tk.END, msg + "\n")
        self.text_output.see(scroll_to)

    def format_and_print_table(self, data, columns, headers, title="", scroll_to="1.0"):
        self.clear_output()
        if not data:
            self.out_msg(f">>> {title}\nДанные отсутствуют.")
            return

        table = PrettyTable(headers)
        table.align = "l"
        for row in data:
            table.add_row([row[col] for col in columns])

        if title:
            self.out_msg(f"=== {title} ===\n", scroll_to=scroll_to)
        self.out_msg(table.get_string(), scroll_to=scroll_to)

    # --- Методы Сотрудников ---
    def action_read(self):
        data = self.db.get_employees()
        self.format_and_print_table(data, ['employee_id', 'full_name', 'position', 'phone', 'branch_address'],
                                    ['ID', 'ФИО', 'Должность', 'Телефон', 'Адрес филиала'], "Штатное расписание")

    def action_create(self):
        branches = self.db.get_branches()
        if not branches:
            messagebox.showwarning("Внимание", "Нет доступных отделений! Сначала откройте филиал.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Прием на работу")
        dialog.geometry("400x450")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="ФИО (Иванов Иван Иванович):").pack(pady=(15, 2))
        e_name = ttk.Entry(dialog, width=45)
        e_name.pack()

        ttk.Label(dialog, text="Должность:").pack(pady=(10, 2))
        e_pos = ttk.Entry(dialog, width=45)
        e_pos.pack()

        ttk.Label(dialog, text="Адрес проживания:").pack(pady=(10, 2))
        e_addr = ttk.Entry(dialog, width=45)
        e_addr.pack()

        ttk.Label(dialog, text="Телефон (+7XXXXXXXXXX):").pack(pady=(10, 2))
        e_phone = ttk.Entry(dialog, width=45)
        e_phone.pack()

        ttk.Label(dialog, text="Выберите отделение:").pack(pady=(10, 2))
        combo = ttk.Combobox(dialog, values=[f"{b['branch_id']} - {b['adress']}" for b in branches], state="readonly",
                             width=42)
        combo.pack()

        def save():
            name, pos, addr, phone, br = e_name.get().strip(), e_pos.get().strip(), e_addr.get().strip(), e_phone.get().strip(), combo.get()

            if not re.match(r"^[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?$", name):
                messagebox.showerror("Ошибка", "Неверный формат ФИО (Кириллица, с заглавной буквы)", parent=dialog)
                return

            if not re.match(r"^[А-Яа-яЁё0-9\s\.,\-\/]+$", addr) or not re.search(r"\d", addr) or len(addr) < 10:
                messagebox.showerror("Ошибка",
                                     "Некорректный формат адреса!\nПример: г. Волгоград, пр. Ленина, д. 28\n(Обязателен номер дома)",
                                     parent=dialog)
                return

            if not re.match(r"^\+7\d{10}$", phone):
                messagebox.showerror("Ошибка", "Формат телефона: +7XXXXXXXXXX", parent=dialog)
                return

            if not all([pos, br]):
                messagebox.showerror("Ошибка", "Заполните все поля!", parent=dialog)
                return

            try:
                self.db.add_employee(name, pos, addr, phone, int(br.split(" - ")[0]))
                messagebox.showinfo("Успех", "Сотрудник принят!", parent=dialog)
                dialog.destroy()
                self.action_read()
            except Exception as e:
                messagebox.showerror("БД Ошибка", str(e), parent=dialog)

        ttk.Button(dialog, text="Сохранить", command=save).pack(pady=20)

    def action_update(self):
        # Выводим таблицу на фон и обновляем UI перед открытием диалога
        self.action_read()
        self.root.update()

        eid = simpledialog.askinteger("U", "ID сотрудника:", parent=self.root)
        if eid:
            pos = simpledialog.askstring("U", "Новая должность:", parent=self.root)
            if pos and self.db.update_employee_position(eid, pos) > 0:
                messagebox.showinfo("OK", "Обновлено")
                self.action_read()

    def action_delete(self):
        # Выводим таблицу на фон и обновляем UI перед открытием диалога
        self.action_read()
        self.root.update()

        eid = simpledialog.askinteger("D", "ID сотрудника для увольнения:", parent=self.root)
        if eid and messagebox.askyesno("Подтверждение", f"Уволить сотрудника с ID {eid}?"):
            if self.db.delete_employee(eid) > 0:
                messagebox.showinfo("OK", "Сотрудник уволен")
                self.action_read()

    # --- Методы Отделений ---
    def action_read_branches(self):
        data = self.db.get_branches()
        self.format_and_print_table(data, ['branch_id', 'adress', 'phone'],
                                    ['ID', 'Адрес филиала', 'Контактный телефон'], "Реестр отделений банка",
                                    scroll_to=tk.END)

    def action_create_branch(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Открыть новое отделение")
        dialog.geometry("450x320")
        dialog.transient(self.root)
        dialog.grab_set()

        instr = "📌 Укажите адрес филиала и контактный телефон.\nОба поля обязательны для заполнения."
        ttk.Label(dialog, text=instr, justify=tk.LEFT, foreground="#444444").pack(pady=15)

        ttk.Label(dialog, text="Фактический адрес:").pack(pady=(5, 2))
        e_addr = ttk.Entry(dialog, width=55)
        e_addr.pack()

        ttk.Label(dialog, text="Телефон отделения (+7XXXXXXXXXX):").pack(pady=(10, 2))
        e_phone = ttk.Entry(dialog, width=55)
        e_phone.pack()

        def save():
            addr, phone = e_addr.get().strip(), e_phone.get().strip()

            if not re.match(r"^[А-Яа-яЁё0-9\s\.,\-\/]+$", addr) or not re.search(r"\d", addr) or len(addr) < 10:
                messagebox.showerror("Ошибка валидации", "Адрес введен неверно!\nПример: г. Волгоград, ул. Мира, 10",
                                     parent=dialog)
                return

            if not re.match(r"^\+7\d{10}$", phone):
                messagebox.showerror("Ошибка", "Проверьте корректность телефона (+7XXXXXXXXXX)", parent=dialog)
                return

            try:
                self.db.add_branch(addr, phone)
                messagebox.showinfo("Успех", "Отделение создано!", parent=dialog)
                dialog.destroy()
                self.action_read_branches()
            except Exception as e:
                messagebox.showerror("БД Ошибка", str(e), parent=dialog)

        ttk.Button(dialog, text="Создать запись", command=save).pack(pady=15)

    def action_update_branch(self):
        branches = self.db.get_branches()
        if not branches:
            messagebox.showwarning("Внимание", "Нет доступных отделений для изменения.")
            return

        # Выводим таблицу отделений на фон
        self.action_read_branches()
        self.root.update()

        dialog = tk.Toplevel(self.root)
        dialog.title("Сменить адрес отделения")
        dialog.geometry("400x220")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Выберите отделение из списка:").pack(pady=(15, 5))
        combo = ttk.Combobox(dialog, values=[f"{b['branch_id']} - {b['adress']}" for b in branches], state="readonly",
                             width=50)
        combo.pack()

        ttk.Label(dialog, text="Новый адрес:").pack(pady=(10, 5))
        e_addr = ttk.Entry(dialog, width=53)
        e_addr.pack()

        def update():
            selected = combo.get()
            new_addr = e_addr.get().strip()

            if not selected:
                messagebox.showerror("Ошибка", "Выберите филиал из списка!", parent=dialog)
                return

            # Валидация нового адреса
            if not re.match(r"^[А-Яа-яЁё0-9\s\.,\-\/]+$", new_addr) or not re.search(r"\d", new_addr) or len(
                    new_addr) < 10:
                messagebox.showerror("Ошибка валидации", "Адрес введен неверно!\nПример: г. Волгоград, ул. Мира, 10",
                                     parent=dialog)
                return

            bid = int(selected.split(" - ")[0])
            try:
                if self.db.update_branch(bid, new_addr) > 0:
                    messagebox.showinfo("Успех", "Адрес отделения обновлен!", parent=dialog)
                    dialog.destroy()
                    self.action_read_branches()
            except Exception as e:
                messagebox.showerror("Ошибка БД", str(e), parent=dialog)

        ttk.Button(dialog, text="Обновить", command=update).pack(pady=15)

    def action_delete_branch(self):
        branches = self.db.get_branches()
        if not branches:
            messagebox.showwarning("Внимание", "Нет доступных отделений для удаления.")
            return

        # Выводим таблицу отделений на фон
        self.action_read_branches()
        self.root.update()

        dialog = tk.Toplevel(self.root)
        dialog.title("Закрыть отделение")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Выберите отделение для закрытия:").pack(pady=(15, 5))
        combo = ttk.Combobox(dialog, values=[f"{b['branch_id']} - {b['adress']}" for b in branches], state="readonly",
                             width=50)
        combo.pack()

        def confirm_delete():
            selected = combo.get()
            if not selected:
                messagebox.showerror("Ошибка", "Выберите филиал из списка!", parent=dialog)
                return

            bid = int(selected.split(" - ")[0])
            if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите закрыть отделение ID {bid}?",
                                   parent=dialog):
                try:
                    if self.db.delete_branch(bid) > 0:
                        messagebox.showinfo("Успех", "Отделение закрыто", parent=dialog)
                        dialog.destroy()
                        self.action_read_branches()
                except Exception as e:
                    messagebox.showerror("Ошибка БД",
                                         f"Нельзя закрыть отделение с персоналом или банкоматами!\n\nДетали: {e}",
                                         parent=dialog)

        ttk.Button(dialog, text="Удалить отделение", command=confirm_delete).pack(pady=15)

    # --- Аналитика ---
    def action_analytics_1(self):
        s = simpledialog.askstring("Даты", "Начало (ГГГГ-ММ-ДД):")
        e = simpledialog.askstring("Даты", "Конец (ГГГГ-ММ-ДД):")
        if s and e:
            self.format_and_print_table(self.db.analytics_transfers_by_date(s, e),
                                        ['card_number', 'amount', 'operation_time'], ['Карта', 'Сумма', 'Дата'],
                                        "Журнал транзакций")

    def action_analytics_2(self):
        r = simpledialog.askfloat("Ставка", "Мин. процент (%):")
        if r:
            self.format_and_print_table(self.db.analytics_top_loans(r),
                                        ['contract_number', 'manager', 'debt_amount', 'interest_rate'],
                                        ['Договор', 'Менеджер', 'Сумма', 'Ставка'], "Портфель крупных займов")


if __name__ == "__main__":
    db_conn = DatabaseManager(dbname="Sber", user="postgres", password="555666")
    root_win = tk.Tk()
    AppGUI(root_win, db_conn)
    root_win.protocol("WM_DELETE_WINDOW", lambda: (db_conn.close(), root_win.destroy()))
    root_win.mainloop()