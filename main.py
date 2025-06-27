import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import psycopg2
from collections import defaultdict
import sys
import logging

logging.basicConfig(filename='app.log', level=logging.ERROR)


class RestaurantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ресторанная система управления")
        self.root.geometry("1200x800")
        
        # Глобальная обработка исключений
        sys.excepthook = lambda e, v, t: self.handle_exception(e, v, t)
        
        # Подключение к БД
        self.db_connection = self.connect_to_db()
        self.current_user = None
        self.current_order = None
        self.current_shift = None  # Текущая смена для официанта
        
        self.create_widgets()
        self.show_login_screen()
    
    def handle_exception(self, exc, val, tb):
        """Глобальный обработчик исключений"""
        error_msg = f"Произошла ошибка:\n{str(val)}\n\nПриложение продолжит работу."
        messagebox.showerror("Ошибка", error_msg)
        import traceback
        traceback.print_exception(exc, val, tb)

    def connect_to_db(self):
        """Устанавливает соединение с PostgreSQL"""
        try:
            conn = psycopg2.connect(
                dbname="restaurant_db",
                user="postgres",
                password="123",
                host="localhost",
                port="5432",
                client_encoding='WIN1251'  # Указываем кодировку соединения
            )
            return conn
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к БД: {str(e)}")
            logging.error(f"Database connection error: {str(e)}")
            return None
        
    def close_order(self):
        """Закрывает выбранный заказ (меняет статус на 'closed')"""
        selected_item = self.orders_tree.selection()
        if not selected_item:
            messagebox.showerror("Ошибка", "Выберите заказ для закрытия")
            return
        
        item = self.orders_tree.item(selected_item[0])
        order_id = item["values"][0]
        status = item["values"][2]  # Статус заказа
        
        if status == "closed":
            messagebox.showerror("Ошибка", "Заказ уже закрыт")
            return
        
        if status != "paid":
            if not messagebox.askyesno("Подтверждение", 
                                    "Закрыть заказ?"):
                return
        
        query = "UPDATE orders SET status = 'closed' WHERE id = %s"
        if self.execute_query(query, (order_id,)):
            messagebox.showinfo("Успех", f"Заказ №{order_id} успешно закрыт")
            self.show_orders_screen()
        else:
            messagebox.showerror("Ошибка", "Не удалось закрыть заказ")
    
    def execute_query(self, query, params=None, fetch=False):
        try:
            logging.info(f"Executing query: {query} with params: {params}")
            if not self.db_connection or self.db_connection.closed:
                self.db_connection = self.connect_to_db()
                if not self.db_connection:
                    return False
            
            cursor = self.db_connection.cursor()
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                cursor.close()
                return result
            else:
                self.db_connection.commit()
                cursor.close()
                return True
                
        except Exception as e:
            logging.error(f"Error executing query: {query}\nError: {str(e)}")
            if self.db_connection:
                self.db_connection.rollback()
            messagebox.showerror("Ошибка БД", f"Ошибка при выполнении запроса: {str(e)}")
            return False
    
    def create_widgets(self):
        """Создание интерфейса приложения"""
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Панель навигации
        self.nav_frame = ttk.Frame(self.main_container)
        
        self.tables_btn = ttk.Button(self.nav_frame, text="Столы", command=self.show_tables_screen)
        self.reserve_btn = ttk.Button(self.nav_frame, text="Бронирование", command=self.show_reservation_screen)
        self.orders_btn = ttk.Button(self.nav_frame, text="Заказы", command=self.show_orders_screen)
        self.menu_btn = ttk.Button(self.nav_frame, text="Меню", command=self.show_menu_screen)
        self.stats_btn = ttk.Button(self.nav_frame, text="Статистика", command=self.show_stats_screen)
        self.sessions_btn = ttk.Button(self.nav_frame, text="Сессии", command=self.show_sessions_screen)
        self.shift_btn = ttk.Button(self.nav_frame, text="Начать смену", command=self.start_shift)
        self.end_shift_btn = ttk.Button(self.nav_frame, text="Закончить смену", command=self.end_shift)
        self.login_btn = ttk.Button(self.nav_frame, text="Вход", command=self.show_login_screen)
        self.logout_btn = ttk.Button(self.nav_frame, text="Выход", command=self.logout)
        
        # Область контента
        self.content_area = ttk.Frame(self.main_container)
        self.content_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def hide_nav_buttons(self):
        """Скрывает кнопки навигации (до входа)"""
        for btn in [self.tables_btn, self.reserve_btn, self.orders_btn, 
                   self.menu_btn, self.stats_btn, self.sessions_btn,
                   self.shift_btn, self.end_shift_btn, self.logout_btn]:
            btn.pack_forget()
    
    def show_nav_buttons(self, role):
        """Показывает кнопки навигации в зависимости от роли"""
        self.hide_nav_buttons()
        self.login_btn.pack_forget()
        
        # Общие кнопки для всех ролей
        self.tables_btn.pack(side=tk.LEFT, padx=5)
        self.reserve_btn.pack(side=tk.LEFT, padx=5)
        
        # Специфичные кнопки
        if role in ["waiter", "admin", "client"]:
            self.orders_btn.pack(side=tk.LEFT, padx=5)
            self.menu_btn.pack(side=tk.LEFT, padx=5)
        
        if role == "admin":
            self.stats_btn.pack(side=tk.LEFT, padx=5)
            self.sessions_btn.pack(side=tk.LEFT, padx=5)
            
        if role == "waiter":
            self.shift_btn.pack(side=tk.LEFT, padx=5)
            self.end_shift_btn.pack(side=tk.LEFT, padx=5)
            
        self.logout_btn.pack(side=tk.RIGHT, padx=5)
        
        self.nav_frame.pack(fill=tk.X, padx=5, pady=5)
    
    def clear_content_area(self):
        """Очищает область контента"""
        for widget in self.content_area.winfo_children():
            widget.destroy()
    
    def show_login_screen(self):
        """Показывает экран входа"""
        self.clear_content_area()
        self.current_user = None
        self.current_shift = None
        self.hide_nav_buttons()
        self.login_btn.pack(side=tk.LEFT, padx=5)
        self.nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        login_frame = ttk.Frame(self.content_area)
        login_frame.pack(pady=50)
        
        # Вкладки для входа/регистрации
        notebook = ttk.Notebook(login_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладка входа
        login_tab = ttk.Frame(notebook)
        notebook.add(login_tab, text="Вход")
        
        ttk.Label(login_tab, text="Вход в систему", font=('Helvetica', 16)).pack(pady=10)
        
        ttk.Label(login_tab, text="Логин:").pack()
        self.login_entry = ttk.Entry(login_tab)
        self.login_entry.pack(pady=5)
        
        ttk.Label(login_tab, text="Пароль:").pack()
        self.password_entry = ttk.Entry(login_tab, show="*")
        self.password_entry.pack(pady=5)
        
        ttk.Button(login_tab, text="Войти", command=self.login).pack(pady=20)
        
        # Вкладка регистрации
        register_tab = ttk.Frame(notebook)
        notebook.add(register_tab, text="Регистрация")
        
        ttk.Label(register_tab, text="Регистрация", font=('Helvetica', 16)).pack(pady=10)
        
        ttk.Label(register_tab, text="ФИО:").pack()
        self.reg_name_entry = ttk.Entry(register_tab)
        self.reg_name_entry.pack(pady=5)
        
        ttk.Label(register_tab, text="Логин:").pack()
        self.reg_login_entry = ttk.Entry(register_tab)
        self.reg_login_entry.pack(pady=5)
        
        ttk.Label(register_tab, text="Пароль:").pack()
        self.reg_password_entry = ttk.Entry(register_tab, show="*")
        self.reg_password_entry.pack(pady=5)
        
        ttk.Label(register_tab, text="Подтвердите пароль:").pack()
        self.reg_confirm_entry = ttk.Entry(register_tab, show="*")
        self.reg_confirm_entry.pack(pady=5)
        
        ttk.Button(register_tab, text="Зарегистрироваться", command=self.register).pack(pady=20)
    
    def login(self):
        login = self.login_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not login or not password:
            messagebox.showerror("Ошибка", "Введите логин и пароль")
            return
        
        try:
            if not self.db_connection or self.db_connection.closed:
                self.db_connection = self.connect_to_db()
                if not self.db_connection:
                    messagebox.showerror("Ошибка", "Нет соединения с базой данных")
                    return
                
            query = """
                SELECT u.id, u.full_name, r.name as role 
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.login = %s AND u.password = %s
            """
            result = self.execute_query(query, (login, password), fetch=True)
            
            if result and len(result) > 0:
                user_data = result[0]
                self.current_user = {
                    "id": user_data[0],
                    "name": user_data[1],
                    "role": user_data[2]
                }
                self.show_nav_buttons(self.current_user["role"])
                self.show_tables_screen()
                messagebox.showinfo("Успех", f"Добро пожаловать, {self.current_user['name']}!")
            else:
                messagebox.showerror("Ошибка", "Неверный логин или пароль")
        except Exception as e:
            messagebox.showerror("Ошибка БД", f"Ошибка при входе: {str(e)}")
            logging.error(f"Login error: {str(e)}")
    
    def register(self):
        """Регистрация нового пользователя"""
        full_name = self.reg_name_entry.get()
        login = self.reg_login_entry.get()
        password = self.reg_password_entry.get()
        confirm = self.reg_confirm_entry.get()
        
        if not all([full_name, login, password, confirm]):
            messagebox.showerror("Ошибка", "Заполните все поля")
            return
        
        if password != confirm:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return
        
        # Проверяем, нет ли уже такого логина
        check_query = "SELECT id FROM users WHERE login = %s"
        if self.execute_query(check_query, (login,), fetch=True):
            messagebox.showerror("Ошибка", "Пользователь с таким логином уже существует")
            return
        
        # Регистрируем нового пользователя с ролью "client" (id=3)
        register_query = """
            INSERT INTO users (login, password, full_name, role_id) 
            VALUES (%s, %s, %s, 3)
        """
        if self.execute_query(register_query, (login, password, full_name)):
            messagebox.showinfo("Успех", "Регистрация прошла успешно! Теперь вы можете войти.")
            # Очищаем поля
            self.reg_name_entry.delete(0, tk.END)
            self.reg_login_entry.delete(0, tk.END)
            self.reg_password_entry.delete(0, tk.END)
            self.reg_confirm_entry.delete(0, tk.END)
    
    def logout(self):
        """Выход из системы"""
        # Если официант забыл завершить смену
        if self.current_user and self.current_user["role"] == "waiter" and self.current_shift:
            if messagebox.askyesno("Выход", "Вы не завершили смену. Завершить смену перед выходом?"):
                self.end_shift()
        
        self.current_user = None
        self.current_shift = None
        self.show_login_screen()
    
    def start_shift(self):
        """Начинает смену для официанта"""
        if not self.current_user or self.current_user["role"] != "waiter":
            messagebox.showerror("Ошибка", "Только официанты могут начинать смену")
            return
        
        if self.current_shift:
            messagebox.showerror("Ошибка", "У вас уже есть активная смена")
            return
        
        query = """
            INSERT INTO shifts (waiter_id, start_time) 
            VALUES (%s, NOW())
            RETURNING id
        """
        result = self.execute_query(query, (self.current_user["id"],), fetch=True)
        
        if result:
            self.current_shift = result[0][0]
            messagebox.showinfo("Успех", "Смена успешно начата")
            self.show_tables_screen()
    
    def end_shift(self):
        """Заканчивает смену для официанта"""
        if not self.current_user or self.current_user["role"] != "waiter":
            messagebox.showerror("Ошибка", "Только официанты могут завершать смену")
            return
        
        if not self.current_shift:
            messagebox.showerror("Ошибка", "У вас нет активной смены")
            return
        
        try:
            # Подсчитываем чаевые за смену (10% от суммы оплаченных заказов)
            tips_query = """
                SELECT COALESCE(SUM(total * 0.1), 0) as tips
                FROM orders
                WHERE waiter_id = %s 
                AND created_at BETWEEN 
                    (SELECT start_time FROM shifts WHERE id = %s) 
                    AND NOW()
                AND status = 'paid'
            """
            tips_result = self.execute_query(tips_query, (self.current_user["id"], self.current_shift), fetch=True)
            
            # Проверяем результат запроса
            if not tips_result or len(tips_result) == 0 or len(tips_result[0]) == 0:
                tips_amount = 0
            else:
                tips_amount = float(tips_result[0][0]) if tips_result[0][0] is not None else 0
            
            # Завершаем смену
            update_query = """
                UPDATE shifts 
                SET end_time = NOW(), tips = %s
                WHERE id = %s
                RETURNING id
            """
            result = self.execute_query(update_query, (tips_amount, self.current_shift), fetch=True)
            
            if result:
                messagebox.showinfo("Успех", f"Смена успешно завершена. Чаевые: {tips_amount:.2f} руб.")
                self.current_shift = None
                self.show_tables_screen()
            else:
                messagebox.showerror("Ошибка", "Не удалось завершить смену")
                
        except Exception as e:
            messagebox.showerror("Ошибка БД", f"Ошибка при завершении смены: {str(e)}")
            logging.error(f"Error ending shift: {str(e)}")
    
    def show_tables_screen(self):
        """Показывает экран со списком столов"""
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Столы", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Фильтры
        filter_frame = ttk.Frame(self.content_area)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Дата:").pack(side=tk.LEFT)
        self.table_date_entry = ttk.Entry(filter_frame)
        self.table_date_entry.pack(side=tk.LEFT, padx=5)
        self.table_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        ttk.Label(filter_frame, text="Время:").pack(side=tk.LEFT)
        self.table_time_entry = ttk.Entry(filter_frame)
        self.table_time_entry.pack(side=tk.LEFT, padx=5)
        self.table_time_entry.insert(0, datetime.now().strftime("%H:%M"))
        
        ttk.Button(filter_frame, text="Показать", command=self.update_tables_view).pack(side=tk.LEFT, padx=10)
        
        # Таблица столов
        columns = ("id", "capacity", "status", "reservation", "waiter")
        self.tables_tree = ttk.Treeview(self.content_area, columns=columns, show="headings")
        
        self.tables_tree.heading("id", text="№ стола")
        self.tables_tree.heading("capacity", text="Вместимость")
        self.tables_tree.heading("status", text="Статус")
        self.tables_tree.heading("reservation", text="Бронь")
        self.tables_tree.heading("waiter", text="Официант")
        
        self.tables_tree.column("id", width=80)
        self.tables_tree.column("capacity", width=100)
        self.tables_tree.column("status", width=100)
        self.tables_tree.column("reservation", width=200)
        self.tables_tree.column("waiter", width=150)
        
        self.tables_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.update_tables_view()
        
        # Кнопки действий
        if self.current_user and self.current_user["role"] in ["admin", "waiter"]:
            btn_frame = ttk.Frame(self.content_area)
            btn_frame.pack(pady=10)
            
            ttk.Button(btn_frame, text="Обновить", command=self.update_tables_view).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Забронировать", command=self.show_reservation_screen).pack(side=tk.LEFT, padx=5)
            if self.current_user["role"] == "admin":
                ttk.Button(btn_frame, text="Назначить официанта", command=self.assign_waiter).pack(side=tk.LEFT, padx=5)
    
    def assign_waiter(self):
        """Назначает официанта на стол"""
        selected_item = self.tables_tree.selection()
        if not selected_item:
            messagebox.showerror("Ошибка", "Выберите стол")
            return
        
        item = self.tables_tree.item(selected_item[0])
        table_id = item["values"][0]
        
        # Получаем список официантов
        waiters_query = """
            SELECT u.id, u.full_name 
            FROM users u
            WHERE u.role_id = 2  -- Официанты
            ORDER BY u.full_name
        """
        waiters = self.execute_query(waiters_query, fetch=True) or []
        
        if not waiters:
            messagebox.showerror("Ошибка", "Нет доступных официантов")
            return
        
        # Создаем окно выбора официанта
        assign_window = tk.Toplevel(self.root)
        assign_window.title(f"Назначение официанта на стол №{table_id}")
        
        ttk.Label(assign_window, text="Выберите официанта:").pack(pady=5)
        
        waiter_var = tk.StringVar()
        waiter_combobox = ttk.Combobox(assign_window, textvariable=waiter_var, state="readonly")
        waiter_combobox["values"] = [f"{w[1]} (ID: {w[0]})" for w in waiters]
        waiter_combobox.pack(pady=5)
        waiter_combobox.current(0)
        
        def save_assignment():
            waiter_str = waiter_var.get()
            if not waiter_str:
                return
            
            waiter_id = int(waiter_str.split("ID: ")[1].rstrip(")"))
            
            # Удаляем предыдущие назначения для этого стола
            delete_query = "DELETE FROM waiter_tables WHERE table_id = %s"
            self.execute_query(delete_query, (table_id,))
            
            # Добавляем новое назначение
            insert_query = "INSERT INTO waiter_tables (waiter_id, table_id) VALUES (%s, %s)"
            if self.execute_query(insert_query, (waiter_id, table_id)):
                messagebox.showinfo("Успех", "Официант успешно назначен")
                assign_window.destroy()
                self.update_tables_view()
        
        ttk.Button(assign_window, text="Назначить", command=save_assignment).pack(pady=10)
    
    def update_tables_view(self):
        """Обновляет отображение столов"""
        # Очищаем таблицу
        for item in self.tables_tree.get_children():
            self.tables_tree.delete(item)
        
        # Получаем дату и время для фильтрации
        date_str = self.table_date_entry.get()
        time_str = self.table_time_entry.get()
        
        try:
            # Парсим дату и время с учетом возможных секунд
            filter_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                # Если не получилось, пробуем с секундами
                filter_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Некорректный формат даты или времени: {str(e)}")
                return
        
        # Получаем список столов из БД
        tables_query = "SELECT id, capacity, status FROM tables"
        tables = self.execute_query(tables_query, fetch=True) or []
        
        # Получаем список бронирований на выбранную дату
        reservations_query = """
            SELECT id, table_id, date, start_time, end_time 
            FROM reservations 
            WHERE date = %s AND status = 'active'
        """
        reservations = self.execute_query(reservations_query, (date_str,), fetch=True) or []
        
        # Получаем информацию о назначенных официантах
        waiters_query = """
            SELECT wt.table_id, u.full_name 
            FROM waiter_tables wt
            JOIN users u ON wt.waiter_id = u.id
        """
        table_waiters = self.execute_query(waiters_query, fetch=True) or []
        waiter_dict = {table_id: name for table_id, name in table_waiters}
        
        # Получаем активные заказы для определения занятости столов
        active_orders_query = """
            SELECT table_id 
            FROM orders 
            WHERE status = 'active'
        """
        active_orders = self.execute_query(active_orders_query, fetch=True) or []
        busy_tables = {order[0] for order in active_orders}
        
        # Заполняем таблицу данными
        for table in tables:
            table_id, capacity, status = table
            reservation_info = ""
            waiter_name = waiter_dict.get(table_id, "")
            
            # Проверяем бронирования для этого стола
            for res in reservations:
                res_id, res_table_id, res_date, start_time, end_time = res
                if res_table_id == table_id:
                    try:
                        # Форматируем время начала
                        if isinstance(start_time, str):
                            start_time_str = start_time[:5]  # Берем только часы и минуты
                        else:
                            start_time_str = start_time.strftime("%H:%M")
                        
                        # Форматируем время окончания
                        if isinstance(end_time, str):
                            end_time_str = end_time[:5]  # Берем только часы и минуты
                        else:
                            end_time_str = end_time.strftime("%H:%M")
                        
                        start = datetime.strptime(f"{res_date} {start_time_str}", "%Y-%m-%d %H:%M")
                        end = datetime.strptime(f"{res_date} {end_time_str}", "%Y-%m-%d %H:%M")
                        
                        if start <= filter_datetime <= end:
                            reservation_info = f"Бронь #{res_id} до {end_time_str}"
                            break
                    except ValueError as e:
                        print(f"Ошибка при обработке времени бронирования: {e}")
                        continue
            
            # Определяем статус стола
            if table_id in busy_tables:
                status = "занят (заказ)"
            elif reservation_info:
                status = "занят (бронь)"
            else:
                status = "свободен"
            
            self.tables_tree.insert("", tk.END, values=(
                table_id,
                capacity,
                status,
                reservation_info,
                waiter_name
            ))
    
    def show_reservation_screen(self):
        """Показывает экран бронирования"""
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Бронирование стола", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Форма бронирования
        form_frame = ttk.Frame(self.content_area)
        form_frame.pack(fill=tk.X, pady=10)
        
        # Дата
        ttk.Label(form_frame, text="Дата:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.res_date_entry = ttk.Entry(form_frame)
        self.res_date_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.res_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # Время начала
        ttk.Label(form_frame, text="Время начала:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.res_start_time_entry = ttk.Entry(form_frame)
        self.res_start_time_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.res_start_time_entry.insert(0, (datetime.now() + timedelta(hours=1)).strftime("%H:%M"))
        
        # Время окончания
        ttk.Label(form_frame, text="Время окончания:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.res_end_time_entry = ttk.Entry(form_frame)
        self.res_end_time_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        self.res_end_time_entry.insert(0, (datetime.now() + timedelta(hours=2)).strftime("%H:%M"))
        
        # Количество гостей
        ttk.Label(form_frame, text="Количество гостей:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.res_guests_entry = ttk.Entry(form_frame)
        self.res_guests_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        self.res_guests_entry.insert(0, "2")
        
        # Выбор стола
        ttk.Label(form_frame, text="Стол:").grid(row=4, column=0, sticky=tk.E, padx=5, pady=5)
        self.res_table_combobox = ttk.Combobox(form_frame, state="readonly")
        self.res_table_combobox.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        self.update_available_tables()
        
        # Кнопки
        btn_frame = ttk.Frame(self.content_area)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Забронировать", command=self.make_reservation).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отменить", command=self.show_tables_screen).pack(side=tk.LEFT, padx=5)
    
    def update_available_tables(self):
        """Обновляет список доступных столов для бронирования"""
        try:
            date = self.res_date_entry.get()
            start_time = self.res_start_time_entry.get()
            end_time = self.res_end_time_entry.get()
            
            start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            
            # Получаем все столы
            tables_query = "SELECT id, capacity FROM tables"
            tables = self.execute_query(tables_query, fetch=True) or []
            
            # Получаем занятые столы на выбранное время
            busy_tables_query = """
                SELECT DISTINCT table_id 
                FROM reservations 
                WHERE date = %s AND status = 'active'
                AND NOT (end_time <= %s OR start_time >= %s)
            """
            busy_tables = self.execute_query(
                busy_tables_query, 
                (date, start_time, end_time), 
                fetch=True
            ) or []
            
            busy_table_ids = [table[0] for table in busy_tables]
            
            # Получаем столы с активными заказами
            active_orders_query = """
                SELECT DISTINCT table_id 
                FROM orders 
                WHERE status = 'active'
            """
            active_orders = self.execute_query(active_orders_query, fetch=True) or []
            busy_table_ids.extend([order[0] for order in active_orders])
            
            # Формируем список доступных столов
            available_tables = [
                table for table in tables 
                if table[0] not in busy_table_ids
            ]
            
            # Обновляем combobox
            table_options = [f"№{t[0]} (мест: {t[1]})" for t in available_tables]
            self.res_table_combobox["values"] = table_options
            if table_options:
                self.res_table_combobox.current(0)
        
        except ValueError:
            pass
    
    def make_reservation(self):
        """Создает бронирование с проверкой занятости стола"""
        try:
            date = self.res_date_entry.get()
            start_time = self.res_start_time_entry.get()
            end_time = self.res_end_time_entry.get()
            guests = int(self.res_guests_entry.get())
            table_str = self.res_table_combobox.get()
            
            if not all([date, start_time, end_time, table_str]):
                messagebox.showerror("Ошибка", "Заполните все поля")
                return
            
             
            if self.current_user and self.current_user["role"] == "waiter" and not self.current_shift:
                messagebox.showerror("Ошибка", "Вы должны начать смену перед бронированием")
                return
            
            # Извлекаем номер стола из строки (формат: "№1 (мест: 2)")
            table_id = int(table_str.split("№")[1].split(" ")[0])
            
            # Проверяем вместимость стола
            table_query = "SELECT capacity FROM tables WHERE id = %s"
            table = self.execute_query(table_query, (table_id,), fetch=True)
            
            if not table:
                messagebox.showerror("Ошибка", "Стол не найден")
                return
                
            capacity = table[0][0]
            if guests > capacity:
                messagebox.showerror("Ошибка", f"Стол №{table_id} вмещает только {capacity} гостей")
                return
            
            # Проверяем, не занят ли стол в это время
            check_query = """
                SELECT id FROM reservations 
                WHERE table_id = %s AND date = %s AND status = 'active'
                AND NOT (end_time <= %s OR start_time >= %s)
            """
            existing = self.execute_query(
                check_query, 
                (table_id, date, start_time, end_time), 
                fetch=True
            )
            
            if existing:
                messagebox.showerror("Ошибка", "Стол уже забронирован на это время")
                return
            
            # Проверяем, нет ли активного заказа на этот стол
            order_check = """
                SELECT id FROM orders 
                WHERE table_id = %s AND status = 'active'
            """
            active_order = self.execute_query(order_check, (table_id,), fetch=True)
            
            if active_order:
                messagebox.showerror("Ошибка", "Стол занят активным заказом")
                return
            
            # Создаем бронирование
            query = """
                INSERT INTO reservations 
                (date, start_time, end_time, guests, table_id, client_id, status) 
                VALUES (%s, %s, %s, %s, %s, %s, 'active')
                RETURNING id
            """
            result = self.execute_query(
                query, 
                (date, start_time, end_time, guests, table_id, self.current_user["id"]), 
                fetch=True
            )
            
            if result:
                messagebox.showinfo("Успех", f"Стол №{table_id} успешно забронирован")
                self.show_tables_screen()
        
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректные данные: {str(e)}")
    
    def show_orders_screen(self):
        """Показывает экран заказов"""
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Заказы", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Таблица заказов
        columns = ("id", "table", "status", "total", "created_at")
        self.orders_tree = ttk.Treeview(self.content_area, columns=columns, show="headings")
        
        self.orders_tree.heading("id", text="№ заказа")
        self.orders_tree.heading("table", text="Стол")
        self.orders_tree.heading("status", text="Статус")
        self.orders_tree.heading("total", text="Сумма")
        self.orders_tree.heading("created_at", text="Дата создания")
        
        self.orders_tree.column("id", width=80)
        self.orders_tree.column("table", width=100)
        self.orders_tree.column("status", width=100)
        self.orders_tree.column("total", width=100)
        self.orders_tree.column("created_at", width=150)
        
        self.orders_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Проверяем, не занят ли стол другим заказом
        order_check = """
            SELECT id, client_id FROM orders 
            WHERE table_id = %s AND status = 'active'
        """
        active_order = self.execute_query(order_check, (table_id,), fetch=True)

        if active_order:
            # Если заказ уже есть, проверяем, принадлежит ли он текущему клиенту
            if active_order[0][1] != self.current_user["id"]:
                messagebox.showerror("Ошибка", "Стол уже занят другим заказом")
                return
            else:
                # Если заказ принадлежит текущему клиенту, разрешаем добавить блюда к существующему заказу
                if not messagebox.askyesno("Подтверждение", 
                                        "У вас уже есть активный заказ на этот стол. Добавить блюда к существующему заказу?"):
                    return
                # Получаем ID существующего заказа
                existing_order_id = active_order[0][0]
                # Добавляем блюда к существующему заказу
                self.add_items_to_existing_order(existing_order_id)
                return

        # Заполняем таблицу данными из БД
        if self.current_user["role"] == "client":
            query = """
                SELECT o.id, t.id, o.status, o.total, o.created_at 
                FROM orders o
                JOIN tables t ON o.table_id = t.id
                WHERE o.client_id = %s 
                ORDER BY o.created_at DESC
            """
            orders = self.execute_query(query, (self.current_user["id"],), fetch=True) or []
        elif self.current_user["role"] == "waiter":
            query = """
                SELECT o.id, t.id, o.status, o.total, o.created_at 
                FROM orders o
                JOIN tables t ON o.table_id = t.id
                WHERE o.waiter_id = %s 
                ORDER BY o.created_at DESC
            """
            orders = self.execute_query(query, (self.current_user["id"],), fetch=True) or []
        else:
            query = """
                SELECT o.id, t.id, o.status, o.total, o.created_at 
                FROM orders o
                JOIN tables t ON o.table_id = t.id
                ORDER BY o.created_at DESC
            """
            orders = self.execute_query(query, fetch=True) or []
        
        for order in orders:
            order_id, table_id, status, total, created_at = order
            self.orders_tree.insert("", tk.END, values=(
                order_id,
                f"Стол №{table_id}",
                status,
                f"{total} руб.",
                created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime) else created_at
            ))
        
        # Кнопки действий
        btn_frame = ttk.Frame(self.content_area)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Создать заказ", command=self.show_create_order_screen).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Просмотреть", command=self.view_order_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Обновить", command=self.show_orders_screen).pack(side=tk.LEFT, padx=5)
        
        # Добавляем кнопки для просмотра чеков в зависимости от роли
        if self.current_user["role"] == "client":
            ttk.Button(btn_frame, text="Мои чеки", command=self.show_client_receipts_for_client).pack(side=tk.LEFT, padx=5)
        elif self.current_user["role"] in ["waiter", "admin"]:
            ttk.Button(btn_frame, text="Чеки клиентов", command=self.show_client_receipts).pack(side=tk.LEFT, padx=5)
        
        if self.current_user["role"] in ["admin", "waiter"]:
            ttk.Button(btn_frame, text="Закрыть заказ", command=self.close_order).pack(side=tk.LEFT, padx=5)
            
    

    def add_items_to_existing_order(self, order_id):
        """Добавляет блюда к существующему заказу"""
        try:
            # Получаем текущий заказ из БД для обновления общей суммы
            order_query = "SELECT total FROM orders WHERE id = %s"
            order = self.execute_query(order_query, (order_id,), fetch=True)
            
            if not order:
                messagebox.showerror("Ошибка", "Заказ не найден")
                return
                
            current_total = float(order[0][0]) if order[0][0] else 0
            new_total = current_total + self.current_order["total"]
            
            # Добавляем элементы заказа
            for item in self.current_order["items"]:
                # Проверяем, есть ли уже это блюдо в заказе
                item_check = """
                    SELECT id, quantity FROM order_items 
                    WHERE order_id = %s AND dish_id = %s
                """
                existing_item = self.execute_query(
                    item_check, 
                    (order_id, item["dish_id"]), 
                    fetch=True
                )
                
                if existing_item:
                    # Обновляем существующую позицию
                    update_query = """
                        UPDATE order_items 
                        SET quantity = quantity + %s 
                        WHERE id = %s
                    """
                    self.execute_query(
                        update_query, 
                        (item["quantity"], existing_item[0][0])
                    )
                else:
                    # Добавляем новую позицию
                    item_query = """
                        INSERT INTO order_items 
                        (order_id, dish_id, quantity, price) 
                        VALUES (%s, %s, %s, %s)
                    """
                    self.execute_query(
                        item_query,
                        (order_id, item["dish_id"], item["quantity"], item["price"])
                    )
                
                # Уменьшаем количество блюд на складе
                update_query = """
                    UPDATE dishes 
                    SET quantity = quantity - %s 
                    WHERE id = %s
                """
                self.execute_query(update_query, (item["quantity"], item["dish_id"]))
            
            # Обновляем общую сумму заказа
            update_total_query = "UPDATE orders SET total = %s WHERE id = %s"
            self.execute_query(update_total_query, (new_total, order_id))
            
            messagebox.showinfo("Успех", f"Блюда успешно добавлены к заказу №{order_id}")
            self.show_orders_screen()
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось добавить блюда: {str(e)}")

    def show_orders_screen(self):
        """Показывает экран заказов"""
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Заказы", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Таблица заказов
        columns = ("id", "table", "status", "total", "created_at")
        self.orders_tree = ttk.Treeview(self.content_area, columns=columns, show="headings")
        
        self.orders_tree.heading("id", text="№ заказа")
        self.orders_tree.heading("table", text="Стол")
        self.orders_tree.heading("status", text="Статус")
        self.orders_tree.heading("total", text="Сумма")
        self.orders_tree.heading("created_at", text="Дата создания")
        
        self.orders_tree.column("id", width=80)
        self.orders_tree.column("table", width=100)
        self.orders_tree.column("status", width=100)
        self.orders_tree.column("total", width=100)
        self.orders_tree.column("created_at", width=150)
        
        self.orders_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Заполняем таблицу данными из БД
        if self.current_user["role"] == "client":
            query = """
                SELECT o.id, t.id, o.status, o.total, o.created_at 
                FROM orders o
                JOIN tables t ON o.table_id = t.id
                WHERE o.client_id = %s 
                ORDER BY o.created_at DESC
            """
            orders = self.execute_query(query, (self.current_user["id"],), fetch=True) or []
        elif self.current_user["role"] == "waiter":
            query = """
                SELECT o.id, t.id, o.status, o.total, o.created_at 
                FROM orders o
                JOIN tables t ON o.table_id = t.id
                WHERE o.waiter_id = %s 
                ORDER BY o.created_at DESC
            """
            orders = self.execute_query(query, (self.current_user["id"],), fetch=True) or []
        else:
            query = """
                SELECT o.id, t.id, o.status, o.total, o.created_at 
                FROM orders o
                JOIN tables t ON o.table_id = t.id
                ORDER BY o.created_at DESC
            """
            orders = self.execute_query(query, fetch=True) or []
        
        for order in orders:
            order_id, table_id, status, total, created_at = order
            self.orders_tree.insert("", tk.END, values=(
                order_id,
                f"Стол №{table_id}",
                status,
                f"{total} руб.",
                created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime) else created_at
            ))
        
        # Кнопки действий
        btn_frame = ttk.Frame(self.content_area)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Создать заказ", command=self.show_create_order_screen).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Просмотреть", command=self.view_order_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Обновить", command=self.show_orders_screen).pack(side=tk.LEFT, padx=5)
        
        # Добавляем кнопки для просмотра чеков в зависимости от роли
        if self.current_user["role"] == "client":
            ttk.Button(btn_frame, text="Мои чеки", command=self.show_client_receipts_for_client).pack(side=tk.LEFT, padx=5)
        elif self.current_user["role"] in ["waiter", "admin"]:
            ttk.Button(btn_frame, text="Чеки клиентов", command=self.show_client_receipts).pack(side=tk.LEFT, padx=5)
        
        if self.current_user["role"] in ["admin", "waiter"]:
            ttk.Button(btn_frame, text="Закрыть заказ", command=self.close_order).pack(side=tk.LEFT, padx=5)
    
    def update_current_order_view(self):
        """Обновляет отображение текущего заказа"""
        # Очищаем список
        for item in self.current_order_items.get_children():
            self.current_order_items.delete(item)
        
        # Группируем одинаковые блюда
        grouped_items = {}
        for item in self.current_order["items"]:
            if item["dish_id"] in grouped_items:
                grouped_items[item["dish_id"]]["quantity"] += item["quantity"]
                grouped_items[item["dish_id"]]["total"] += item["total"]
            else:
                grouped_items[item["dish_id"]] = item.copy()
        
        # Заполняем новыми данными
        for item in grouped_items.values():
            self.current_order_items.insert("", tk.END, values=(
                item["name"],
                f"{item['price']:.2f} руб.",
                item["quantity"],
                f"{item['total']:.2f} руб."
            ))
        
        # Обновляем итоговую сумму
        self.order_total_label.config(text=f"Итого: {self.current_order['total']:.2f} руб.")

        def save_order(self):
            """Сохраняет заказ"""
            try:
                table_str = self.order_table_combobox.get()
                client_name = self.order_client_entry.get()
                
                if not table_str or not client_name or not self.current_order["items"]:
                    messagebox.showerror("Ошибка", "Заполните все поля и добавьте хотя бы одно блюдо")
                    return
                
                # Извлекаем номер стола из строки (формат: "№1 (мест: 2)")
                table_id = int(table_str.split("№")[1].split(" ")[0])
                
                # Проверяем вместимость стола
                table_query = "SELECT capacity FROM tables WHERE id = %s"
                table = self.execute_query(table_query, (table_id,), fetch=True)
                
                if not table:
                    messagebox.showerror("Ошибка", "Стол не найден")
                    return
                    
                # Проверяем, не занят ли стол другим заказом
                order_check = """
                    SELECT id FROM orders 
                    WHERE table_id = %s AND status = 'active'
                """
                active_order = self.execute_query(order_check, (table_id,), fetch=True)
                
                if active_order:
                    messagebox.showerror("Ошибка", "Стол уже занят другим заказом")
                    return
                
                # Проверяем, не забронирован ли стол
                reservation_check = """
                    SELECT id FROM reservations 
                    WHERE table_id = %s AND status = 'active'
                    AND date = CURRENT_DATE
                    AND start_time <= CURRENT_TIME AND end_time >= CURRENT_TIME
                """
                active_reservation = self.execute_query(reservation_check, (table_id,), fetch=True)
                
                if active_reservation and self.current_user["role"] == "client":
                    # Для клиента проверяем, его ли это бронь
                    reservation_owner_check = """
                        SELECT id FROM reservations 
                        WHERE table_id = %s AND status = 'active'
                        AND date = CURRENT_DATE
                        AND start_time <= CURRENT_TIME AND end_time >= CURRENT_TIME
                        AND client_id = %s
                    """
                    owner_reservation = self.execute_query(
                        reservation_owner_check, 
                        (table_id, self.current_user["id"]), 
                        fetch=True
                    )
                    
                    if not owner_reservation:
                        messagebox.showerror("Ошибка", "Стол забронирован другим клиентом")
                        return
                
                # Определяем waiter_id в зависимости от роли
                if self.current_user["role"] == "client":
                    # Для клиента находим официанта, закрепленного за столом
                    waiter_query = """
                        SELECT waiter_id FROM waiter_tables 
                        WHERE table_id = %s LIMIT 1
                    """
                    waiter = self.execute_query(waiter_query, (table_id,), fetch=True)
                    if not waiter:
                        messagebox.showerror("Ошибка", "Не найден официант для этого стола")
                        return
                    waiter_id = waiter[0][0]
                else:
                    # Для официанта/админа используем текущего пользователя
                    waiter_id = self.current_user["id"]
                
                # Создаем заказ в БД
                query = """
                    INSERT INTO orders 
                    (table_id, client_id, waiter_id, status, total) 
                    VALUES (%s, %s, %s, 'active', %s)
                    RETURNING id
                """
                result = self.execute_query(
                    query,
                    (
                        table_id,
                        self.current_user["id"],
                        waiter_id,
                        self.current_order["total"]
                    ),
                    fetch=True
                )
                
                if not result:
                    messagebox.showerror("Ошибка", "Не удалось создать заказ")
                    return
                    
                order_id = result[0][0]
                
                # Добавляем элементы заказа
                for item in self.current_order["items"]:
                    # Добавляем элемент заказа
                    item_query = """
                        INSERT INTO order_items 
                        (order_id, dish_id, quantity, price) 
                        VALUES (%s, %s, %s, %s)
                    """
                    self.execute_query(
                        item_query,
                        (order_id, item["dish_id"], item["quantity"], item["price"])
                    )
                    
                    # Уменьшаем количество блюд на складе
                    update_query = """
                        UPDATE dishes 
                        SET quantity = quantity - %s 
                        WHERE id = %s
                    """
                    self.execute_query(update_query, (item["quantity"], item["dish_id"]))
                
                messagebox.showinfo("Успех", f"Заказ №{order_id} успешно создан")
                self.show_orders_screen()
            
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Ошибка при создании заказа: {str(e)}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Неожиданная ошибка: {str(e)}")

    def add_dish_to_order(self):
        """Добавляет блюдо в текущий заказ"""
        try:
            dish_str = self.order_dish_combobox.get()
            quantity = int(self.order_quantity_entry.get())
            
            if not dish_str or quantity <= 0:
                messagebox.showerror("Ошибка", "Выберите блюдо и укажите количество")
                return
            
            # Находим блюдо в меню
            dish_name = dish_str.split(" (")[0]
            query = "SELECT id, name, price, quantity FROM dishes WHERE name = %s"
            dish = self.execute_query(query, (dish_name,), fetch=True)
            
            if not dish:
                messagebox.showerror("Ошибка", "Блюдо не найдено")
                return
                
            dish_id, name, price, available_quantity = dish[0]
            
            # Проверяем доступное количество
            if available_quantity < quantity:
                messagebox.showerror("Ошибка", 
                    f"Недостаточно порций блюда '{name}'. Доступно: {available_quantity}")
                return
            
            # Проверяем, есть ли уже это блюдо в заказе
            existing_item = next((item for item in self.current_order["items"] 
                            if item["dish_id"] == dish_id), None)
            
            if existing_item:
                # Проверяем, не превысит ли новое количество доступное
                if existing_item["quantity"] + quantity > available_quantity:
                    messagebox.showerror("Ошибка",
                        f"Общее количество превышает доступное ({available_quantity})")
                    return
                # Обновляем существующую позицию
                existing_item["quantity"] += quantity
                existing_item["total"] = existing_item["price"] * existing_item["quantity"]
            else:
                # Добавляем новую позицию
                item = {
                    "dish_id": dish_id,
                    "name": name,
                    "price": price,
                    "quantity": quantity,
                    "total": price * quantity
                }
                self.current_order["items"].append(item)
            
            self.current_order["total"] = sum(item["total"] for item in self.current_order["items"])
            self.update_current_order_view()
            
            messagebox.showinfo("Успех", 
                f"Блюдо '{name}' в количестве {quantity} порций добавлено в заказ")
            
            self.order_quantity_entry.delete(0, tk.END)
            self.order_quantity_entry.insert(0, "1")
        
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректное количество")
    
    def save_order(self):
        """Сохраняет заказ"""
        try:
            table_str = self.order_table_combobox.get()
            client_name = self.order_client_entry.get()
            
            if not table_str or not client_name or not self.current_order["items"]:
                messagebox.showerror("Ошибка", "Заполните все поля и добавьте хотя бы одно блюдо")
                return
            
            # Извлекаем номер стола из строки (формат: "№1 (мест: 2)")
            table_id = int(table_str.split("№")[1].split(" ")[0])
            
            # Проверяем вместимость стола
            table_query = "SELECT capacity FROM tables WHERE id = %s"
            table = self.execute_query(table_query, (table_id,), fetch=True)
            
            if not table:
                messagebox.showerror("Ошибка", "Стол не найден")
                return
                
            # Проверяем, не занят ли стол другим заказом
            order_check = """
                SELECT id FROM orders 
                WHERE table_id = %s AND status = 'active'
            """
            active_order = self.execute_query(order_check, (table_id,), fetch=True)
            
            if active_order:
                messagebox.showerror("Ошибка", "Стол уже занят другим заказом")
                return
            
            # Проверяем, не забронирован ли стол
            reservation_check = """
                SELECT id FROM reservations 
                WHERE table_id = %s AND status = 'active'
                AND date = CURRENT_DATE
                AND start_time <= CURRENT_TIME AND end_time >= CURRENT_TIME
            """
            active_reservation = self.execute_query(reservation_check, (table_id,), fetch=True)
            
            if active_reservation and self.current_user["role"] == "client":
                # Для клиента проверяем, его ли это бронь
                reservation_owner_check = """
                    SELECT id FROM reservations 
                    WHERE table_id = %s AND status = 'active'
                    AND date = CURRENT_DATE
                    AND start_time <= CURRENT_TIME AND end_time >= CURRENT_TIME
                    AND client_id = %s
                """
                owner_reservation = self.execute_query(
                    reservation_owner_check, 
                    (table_id, self.current_user["id"]), 
                    fetch=True
                )
                
                if not owner_reservation:
                    messagebox.showerror("Ошибка", "Стол забронирован другим клиентом")
                    return
            
            # Определяем waiter_id в зависимости от роли
            if self.current_user["role"] == "client":
                # Для клиента находим официанта, закрепленного за столом
                waiter_query = """
                    SELECT waiter_id FROM waiter_tables 
                    WHERE table_id = %s LIMIT 1
                """
                waiter = self.execute_query(waiter_query, (table_id,), fetch=True)
                if not waiter:
                    messagebox.showerror("Ошибка", "Не найден официант для этого стола")
                    return
                waiter_id = waiter[0][0]
            else:
                # Для официанта/админа используем текущего пользователя
                waiter_id = self.current_user["id"]
            
            # Создаем заказ в БД
            query = """
                INSERT INTO orders 
                (table_id, client_id, waiter_id, status, total) 
                VALUES (%s, %s, %s, 'active', %s)
                RETURNING id
            """
            result = self.execute_query(
                query,
                (
                    table_id,
                    self.current_user["id"],
                    waiter_id,
                    self.current_order["total"]
                ),
                fetch=True
            )
            
            if not result:
                messagebox.showerror("Ошибка", "Не удалось создать заказ")
                return
                
            order_id = result[0][0]
            
            # Добавляем элементы заказа
            for item in self.current_order["items"]:
                # Добавляем элемент заказа
                item_query = """
                    INSERT INTO order_items 
                    (order_id, dish_id, quantity, price) 
                    VALUES (%s, %s, %s, %s)
                """
                self.execute_query(
                    item_query,
                    (order_id, item["dish_id"], item["quantity"], item["price"])
                )
                
                # Уменьшаем количество блюд на складе
                update_query = """
                    UPDATE dishes 
                    SET quantity = quantity - %s 
                    WHERE id = %s
                """
                self.execute_query(update_query, (item["quantity"], item["dish_id"]))
            
            messagebox.showinfo("Успех", f"Заказ №{order_id} успешно создан")
            self.show_orders_screen()
        
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Ошибка при создании заказа: {str(e)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неожиданная ошибка: {str(e)}")
    
    def view_order_details(self):
        """Показывает детали выбранного заказа"""
        selected_item = self.orders_tree.selection()
        if not selected_item:
            messagebox.showerror("Ошибка", "Выберите заказ")
            return
        
        item = self.orders_tree.item(selected_item[0])
        order_id = item["values"][0]
        
        # Получаем информацию о заказе из БД
        query = """
            SELECT o.id, t.id, c.full_name, w.full_name, o.status, o.total, o.created_at
            FROM orders o
            JOIN tables t ON o.table_id = t.id
            JOIN users c ON o.client_id = c.id
            JOIN users w ON o.waiter_id = w.id
            WHERE o.id = %s
        """
        order = self.execute_query(query, (order_id,), fetch=True)
        
        if not order:
            messagebox.showerror("Ошибка", "Заказ не найден")
            return
            
        order = order[0]
        
        # Получаем элементы заказа
        items_query = """
            SELECT d.name, oi.price, oi.quantity, oi.price * oi.quantity as total
            FROM order_items oi
            JOIN dishes d ON oi.dish_id = d.id
            WHERE oi.order_id = %s
        """
        items = self.execute_query(items_query, (order_id,), fetch=True) or []
        
        # Показываем детали в новом окне
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Детали заказа №{order_id}")
        details_window.geometry("600x400")
        
        # Информация о заказе
        info_frame = ttk.Frame(details_window)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(info_frame, text=f"Заказ №{order[0]}", font=('Helvetica', 14)).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Стол: №{order[1]}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Клиент: {order[2]}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Официант: {order[3]}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Дата: {order[6].strftime('%Y-%m-%d %H:%M') if isinstance(order[6], datetime) else order[6]}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Статус: {order[4]}").pack(anchor=tk.W)
        
        # Список блюд
        ttk.Label(details_window, text="Состав заказа:").pack(anchor=tk.W, padx=10)
        
        items_tree = ttk.Treeview(details_window, columns=("dish", "price", "quantity", "total"), show="headings")
        items_tree.heading("dish", text="Блюдо")
        items_tree.heading("price", text="Цена")
        items_tree.heading("quantity", text="Количество")
        items_tree.heading("total", text="Сумма")
        
        items_tree.column("dish", width=200)
        items_tree.column("price", width=100)
        items_tree.column("quantity", width=100)
        items_tree.column("total", width=100)
        
        for item in items:
            items_tree.insert("", tk.END, values=item)
        
        items_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Итоговая сумма
        ttk.Label(details_window, text=f"Итого: {order[5]} руб.", font=('Helvetica', 12)).pack(pady=5)
        
        # Кнопки
        btn_frame = ttk.Frame(details_window)
        btn_frame.pack(pady=10)
        
        if order[4] == "active":
            ttk.Button(btn_frame, text="Оплатить", 
                      command=lambda: self.pay_order(order_id, details_window)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Печать чека", 
                      command=lambda: self.print_receipt(order_id)).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Закрыть", command=details_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def pay_order(self, order_id, window):
        """Обрабатывает оплату заказа"""
        query = "UPDATE orders SET status = 'paid' WHERE id = %s"
        if self.execute_query(query, (order_id,)):
            messagebox.showinfo("Успех", f"Заказ №{order_id} успешно оплачен")
            window.destroy()
            self.show_orders_screen()
        else:
            messagebox.showerror("Ошибка", "Не удалось оплатить заказ")
    
    def generate_receipt(self, order_id):
        """Генерирует чек для заказа"""
        # Получаем информацию о заказе
        order_query = """
            SELECT o.id, t.id, c.full_name, o.total, o.created_at
            FROM orders o
            JOIN tables t ON o.table_id = t.id
            JOIN users c ON o.client_id = c.id
            WHERE o.id = %s
        """
        order = self.execute_query(order_query, (order_id,), fetch=True)
        
        if not order:
            return None
            
        order = order[0]
        
        # Получаем элементы заказа с группировкой
        items_query = """
            SELECT d.name, oi.price, SUM(oi.quantity) as quantity, 
                SUM(oi.price * oi.quantity) as total
            FROM order_items oi
            JOIN dishes d ON oi.dish_id = d.id
            WHERE oi.order_id = %s
            GROUP BY d.name, oi.price
            ORDER BY d.name
        """
        items = self.execute_query(items_query, (order_id,), fetch=True) or []
        
        # Формируем чек
        receipt = f"""
            Ресторан "Гурман"
            ----------------------------
            Чек №{order[0]}
            Стол: №{order[1]}
            Клиент: {order[2]}
            Дата: {order[4].strftime('%Y-%m-%d %H:%M') if isinstance(order[4], datetime) else order[4]}
            ----------------------------
        """
        
        for item in items:
            receipt += f"{item[0]} - {item[1]} руб. x {item[2]} = {item[3]} руб.\n"
        
        receipt += f"""
            ----------------------------
            Итого: {order[3]} руб.
            Спасибо за посещение!
        """
        
        return receipt
    
    def print_receipt(self, order_id):
        """Печатает чек для заказа"""
        receipt = self.generate_receipt(order_id)
        if not receipt:
            messagebox.showerror("Ошибка", "Не удалось сформировать чек")
            return
        
        # Можно добавить реальную печать, здесь просто показываем в messagebox
        messagebox.showinfo("Чек", receipt)
        
        # Добавляем запись о печати чека в БД
        self.execute_query(
            "UPDATE orders SET receipt_printed = TRUE WHERE id = %s",
            (order_id,)
        )
    
    def show_menu_screen(self):
        """Показывает экран меню"""
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Меню ресторана", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Таблица меню
        columns = ("id", "name", "category", "price", "quantity")
        self.menu_tree = ttk.Treeview(self.content_area, columns=columns, show="headings")
        
        self.menu_tree.heading("id", text="№")
        self.menu_tree.heading("name", text="Название")
        self.menu_tree.heading("category", text="Категория")
        self.menu_tree.heading("price", text="Цена")
        self.menu_tree.heading("quantity", text="Доступно")
        
        self.menu_tree.column("id", width=50)
        self.menu_tree.column("name", width=200)
        self.menu_tree.column("category", width=150)
        self.menu_tree.column("price", width=100)
        self.menu_tree.column("quantity", width=100)
        
        self.menu_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Заполняем таблицу из БД
        query = """
            SELECT d.id, d.name, dc.name, d.price, d.quantity
            FROM dishes d
            JOIN dish_categories dc ON d.category_id = dc.id
            ORDER BY d.name
        """
        dishes = self.execute_query(query, fetch=True) or []
        
        for dish in dishes:
            self.menu_tree.insert("", tk.END, values=dish)
        
        # Кнопки действий (только для администратора)
        if self.current_user and self.current_user["role"] == "admin":
            btn_frame = ttk.Frame(self.content_area)
            btn_frame.pack(pady=10)
            
            ttk.Button(btn_frame, text="Добавить блюдо", command=self.show_add_dish_screen).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Редактировать", command=self.show_edit_dish_screen).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Удалить", command=self.delete_dish).pack(side=tk.LEFT, padx=5)
    
    def show_add_dish_screen(self):
        """Показывает экран добавления блюда"""
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Добавление блюда", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Форма добавления блюда
        form_frame = ttk.Frame(self.content_area)
        form_frame.pack(fill=tk.X, pady=10)
        
        # Название
        ttk.Label(form_frame, text="Название:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.dish_name_entry = ttk.Entry(form_frame)
        self.dish_name_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Категория
        ttk.Label(form_frame, text="Категория:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.dish_category_combobox = ttk.Combobox(form_frame, state="readonly")
        self.dish_category_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Заполняем список категорий
        categories_query = "SELECT id, name FROM dish_categories"
        categories = self.execute_query(categories_query, fetch=True) or []
        self.dish_categories = {name: id for id, name in categories}
        self.dish_category_combobox["values"] = list(self.dish_categories.keys())
        if self.dish_categories:
            self.dish_category_combobox.current(0)
        
        # Цена
        ttk.Label(form_frame, text="Цена:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.dish_price_entry = ttk.Entry(form_frame)
        self.dish_price_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Количество
        ttk.Label(form_frame, text="Количество:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.dish_quantity_entry = ttk.Entry(form_frame)
        self.dish_quantity_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        self.dish_quantity_entry.insert(0, "0")
        
        # Описание
        ttk.Label(form_frame, text="Описание:").grid(row=4, column=0, sticky=tk.E, padx=5, pady=5)
        self.dish_description_entry = ttk.Entry(form_frame)
        self.dish_description_entry.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Кнопки
        btn_frame = ttk.Frame(self.content_area)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Сохранить", command=self.save_dish).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отменить", command=self.show_menu_screen).pack(side=tk.LEFT, padx=5)
    
    def save_dish(self):
        """Сохраняет новое блюдо"""
        try:
            name = self.dish_name_entry.get()
            category = self.dish_category_combobox.get()
            price = float(self.dish_price_entry.get())
            quantity = int(self.dish_quantity_entry.get())
            description = self.dish_description_entry.get()
            
            if not all([name, category]) or price <= 0 or quantity < 0:
                messagebox.showerror("Ошибка", "Заполните все обязательные поля корректно")
                return
            
            category_id = self.dish_categories.get(category)
            if not category_id:
                messagebox.showerror("Ошибка", "Выберите корректную категорию")
                return
            
            query = """
                INSERT INTO dishes 
                (name, category_id, price, quantity, description) 
                VALUES (%s, %s, %s, %s, %s)
            """
            if self.execute_query(query, (name, category_id, price, quantity, description)):
                messagebox.showinfo("Успех", f"Блюдо '{name}' успешно добавлено")
                self.show_menu_screen()
        
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректные данные в полях")
    
    def show_edit_dish_screen(self):
        """Показывает экран редактирования блюда"""
        selected_item = self.menu_tree.selection()
        if not selected_item:
            messagebox.showerror("Ошибка", "Выберите блюдо для редактирования")
            return
        
        item = self.menu_tree.item(selected_item[0])
        dish_id = item["values"][0]
        
        # Получаем данные блюда из БД
        query = "SELECT name, category_id, price, quantity, description FROM dishes WHERE id = %s"
        dish = self.execute_query(query, (dish_id,), fetch=True)
        
        if not dish:
            messagebox.showerror("Ошибка", "Блюдо не найдено")
            return
            
        name, category_id, price, quantity, description = dish[0]
        
        # Получаем название категории
        category_query = "SELECT name FROM dish_categories WHERE id = %s"
        category = self.execute_query(category_query, (category_id,), fetch=True)
        category_name = category[0][0] if category else ""
        
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Редактирование блюда", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Форма редактирования блюда
        form_frame = ttk.Frame(self.content_area)
        form_frame.pack(fill=tk.X, pady=10)
        
        # Название
        ttk.Label(form_frame, text="Название:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.edit_dish_name_entry = ttk.Entry(form_frame)
        self.edit_dish_name_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.edit_dish_name_entry.insert(0, name)
        
        # Категория
        ttk.Label(form_frame, text="Категория:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.edit_dish_category_combobox = ttk.Combobox(form_frame, state="readonly")
        self.edit_dish_category_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Заполняем список категорий
        categories_query = "SELECT id, name FROM dish_categories"
        categories = self.execute_query(categories_query, fetch=True) or []
        self.edit_dish_categories = {name: id for id, name in categories}
        self.edit_dish_category_combobox["values"] = list(self.edit_dish_categories.keys())
        
        # Устанавливаем текущую категорию
        if category_name in self.edit_dish_categories:
            self.edit_dish_category_combobox.set(category_name)
        
        # Цена
        ttk.Label(form_frame, text="Цена:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.edit_dish_price_entry = ttk.Entry(form_frame)
        self.edit_dish_price_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        self.edit_dish_price_entry.insert(0, str(price))
        
        # Количество
        ttk.Label(form_frame, text="Количество:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.edit_dish_quantity_entry = ttk.Entry(form_frame)
        self.edit_dish_quantity_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        self.edit_dish_quantity_entry.insert(0, str(quantity))
        
        # Описание
        ttk.Label(form_frame, text="Описание:").grid(row=4, column=0, sticky=tk.E, padx=5, pady=5)
        self.edit_dish_description_entry = ttk.Entry(form_frame)
        self.edit_dish_description_entry.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        self.edit_dish_description_entry.insert(0, description or "")
        
        # Кнопки
        btn_frame = ttk.Frame(self.content_area)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Сохранить", 
                  command=lambda: self.update_dish(dish_id)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отменить", command=self.show_menu_screen).pack(side=tk.LEFT, padx=5)
    
    def update_dish(self, dish_id):
        """Обновляет данные блюда"""
        try:
            name = self.edit_dish_name_entry.get()
            category = self.edit_dish_category_combobox.get()
            price = float(self.edit_dish_price_entry.get())
            quantity = int(self.edit_dish_quantity_entry.get())
            description = self.edit_dish_description_entry.get()
            
            if not all([name, category]) or price <= 0 or quantity < 0:
                messagebox.showerror("Ошибка", "Заполните все обязательные поля корректно")
                return
            
            category_id = self.edit_dish_categories.get(category)
            if not category_id:
                messagebox.showerror("Ошибка", "Выберите корректную категорию")
                return
            
            query = """
                UPDATE dishes 
                SET name = %s, category_id = %s, price = %s, 
                    quantity = %s, description = %s
                WHERE id = %s
            """
            if self.execute_query(query, (name, category_id, price, quantity, description, dish_id)):
                messagebox.showinfo("Успех", f"Блюдо '{name}' успешно обновлено")
                self.show_menu_screen()
        
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректные данные в полях")
    
    def delete_dish(self):
        """Удаляет выбранное блюдо"""
        selected_item = self.menu_tree.selection()
        if not selected_item:
            messagebox.showerror("Ошибка", "Выберите блюдо для удаления")
            return
        
        item = self.menu_tree.item(selected_item[0])
        dish_id = item["values"][0]
        dish_name = item["values"][1]
        
        # Проверяем, есть ли это блюдо в заказах
        check_query = """
            SELECT COUNT(*) 
            FROM order_items 
            WHERE dish_id = %s
        """
        result = self.execute_query(check_query, (dish_id,), fetch=True)
        
        if result and result[0][0] > 0:
            messagebox.showerror("Ошибка", 
                f"Блюдо '{dish_name}' нельзя удалить, так как оно есть в заказах")
            return
        
        # Удаляем блюдо
        delete_query = "DELETE FROM dishes WHERE id = %s"
        if self.execute_query(delete_query, (dish_id,)):
            messagebox.showinfo("Успех", f"Блюдо '{dish_name}' успешно удалено")
            self.show_menu_screen()
    
    def show_stats_screen(self):
        """Показывает экран статистики (только для администратора)"""
        if not self.current_user or self.current_user["role"] != "admin":
            messagebox.showerror("Ошибка", "Доступ запрещен")
            return
        
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Статистика", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Вкладки для разных видов статистики
        notebook = ttk.Notebook(self.content_area)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Статистика по продажам блюд
        sales_frame = ttk.Frame(notebook)
        notebook.add(sales_frame, text="Продажи блюд")
        
        # Фильтры
        filter_frame = ttk.Frame(sales_frame)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Месяц:").pack(side=tk.LEFT)
        self.sales_month_combobox = ttk.Combobox(filter_frame, values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
        self.sales_month_combobox.pack(side=tk.LEFT, padx=5)
        self.sales_month_combobox.set(datetime.now().month)
        
        ttk.Label(filter_frame, text="Год:").pack(side=tk.LEFT)
        self.sales_year_entry = ttk.Entry(filter_frame, width=6)
        self.sales_year_entry.pack(side=tk.LEFT, padx=5)
        self.sales_year_entry.insert(0, datetime.now().year)
        
        ttk.Button(filter_frame, text="Показать", command=self.update_sales_stats).pack(side=tk.LEFT, padx=10)
        
        # Таблица статистики
        columns = ("category", "dish", "quantity", "total")
        self.sales_tree = ttk.Treeview(sales_frame, columns=columns, show="headings")
        
        self.sales_tree.heading("category", text="Категория")
        self.sales_tree.heading("dish", text="Блюдо")
        self.sales_tree.heading("quantity", text="Количество")
        self.sales_tree.heading("total", text="Сумма")
        
        self.sales_tree.column("category", width=150)
        self.sales_tree.column("dish", width=200)
        self.sales_tree.column("quantity", width=100)
        self.sales_tree.column("total", width=100)
        
        self.sales_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Статистика по бронированиям
        reservations_frame = ttk.Frame(notebook)
        notebook.add(reservations_frame, text="Бронирования")
        
        # Фильтры
        res_filter_frame = ttk.Frame(reservations_frame)
        res_filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(res_filter_frame, text="Месяц:").pack(side=tk.LEFT)
        self.res_month_combobox = ttk.Combobox(res_filter_frame, values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
        self.res_month_combobox.pack(side=tk.LEFT, padx=5)
        self.res_month_combobox.set(datetime.now().month)
        
        ttk.Label(res_filter_frame, text="Год:").pack(side=tk.LEFT)
        self.res_year_entry = ttk.Entry(res_filter_frame, width=6)
        self.res_year_entry.pack(side=tk.LEFT, padx=5)
        self.res_year_entry.insert(0, datetime.now().year)
        
        ttk.Button(res_filter_frame, text="Показать", command=self.update_reservations_stats).pack(side=tk.LEFT, padx=10)
        
        # Таблица статистики
        columns = ("table", "reservations")
        self.reservations_tree = ttk.Treeview(reservations_frame, columns=columns, show="headings")
        
        self.reservations_tree.heading("table", text="Стол")
        self.reservations_tree.heading("reservations", text="Количество броней")
        
        self.reservations_tree.column("table", width=150)
        self.reservations_tree.column("reservations", width=150)
        
        self.reservations_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Статистика по официантам
        waiters_frame = ttk.Frame(notebook)
        notebook.add(waiters_frame, text="Официанты")
        
        # Фильтры
        waiter_filter_frame = ttk.Frame(waiters_frame)
        waiter_filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(waiter_filter_frame, text="Месяц:").pack(side=tk.LEFT)
        self.waiter_month_combobox = ttk.Combobox(waiter_filter_frame, values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
        self.waiter_month_combobox.pack(side=tk.LEFT, padx=5)
        self.waiter_month_combobox.set(datetime.now().month)
        
        ttk.Label(waiter_filter_frame, text="Год:").pack(side=tk.LEFT)
        self.waiter_year_entry = ttk.Entry(waiter_filter_frame, width=6)
        self.waiter_year_entry.pack(side=tk.LEFT, padx=5)
        self.waiter_year_entry.insert(0, datetime.now().year)
        
        ttk.Button(waiter_filter_frame, text="Показать", command=self.update_waiters_stats).pack(side=tk.LEFT, padx=10)
        
        # Таблица статистики
        columns = ("waiter", "orders", "payments", "total", "tips")
        self.waiters_tree = ttk.Treeview(waiters_frame, columns=columns, show="headings")
        
        self.waiters_tree.heading("waiter", text="Официант")
        self.waiters_tree.heading("orders", text="Заказы")
        self.waiters_tree.heading("payments", text="Оплаты")
        self.waiters_tree.heading("total", text="Сумма")
        self.waiters_tree.heading("tips", text="Чаевые")
        
        self.waiters_tree.column("waiter", width=200)
        self.waiters_tree.column("orders", width=100)
        self.waiters_tree.column("payments", width=100)
        self.waiters_tree.column("total", width=100)
        self.waiters_tree.column("tips", width=100)
        
        self.waiters_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Обновляем данные
        self.update_sales_stats()
        self.update_reservations_stats()
        self.update_waiters_stats()
    
    def update_sales_stats(self):
        """Обновляет статистику продаж"""
        try:
            month = int(self.sales_month_combobox.get())
            year = int(self.sales_year_entry.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный месяц или год")
            return
        
        # Очищаем таблицу
        for item in self.sales_tree.get_children():
            self.sales_tree.delete(item)
        
        # Получаем статистику продаж из БД
        query = """
            SELECT dc.name, d.name, SUM(oi.quantity), SUM(oi.price * oi.quantity)
            FROM order_items oi
            JOIN dishes d ON oi.dish_id = d.id
            JOIN dish_categories dc ON d.category_id = dc.id
            JOIN orders o ON oi.order_id = o.id
            WHERE EXTRACT(MONTH FROM o.created_at) = %s 
            AND EXTRACT(YEAR FROM o.created_at) = %s
            GROUP BY dc.name, d.name
            ORDER BY dc.name, d.name
        """
        stats = self.execute_query(query, (month, year), fetch=True) or []
        
        # Заполняем таблицу
        for category, dish, quantity, total in stats:
            self.sales_tree.insert("", tk.END, values=(
                category,
                dish,
                quantity,
                f"{total} руб."
            ))
    
    def update_reservations_stats(self):
        """Обновляет статистику бронирований"""
        try:
            month = int(self.res_month_combobox.get())
            year = int(self.res_year_entry.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный месяц или год")
            return
        
        # Очищаем таблицу
        for item in self.reservations_tree.get_children():
            self.reservations_tree.delete(item)
        
        # Получаем статистику бронирований из БД
        query = """
            SELECT t.id, COUNT(r.id)
            FROM tables t
            LEFT JOIN reservations r ON t.id = r.table_id
            AND EXTRACT(MONTH FROM r.date::date) = %s
            AND EXTRACT(YEAR FROM r.date::date) = %s
            AND r.status = 'active'
            GROUP BY t.id
            ORDER BY t.id
        """
        stats = self.execute_query(query, (month, year), fetch=True) or []
        
        # Заполняем таблицу
        for table_id, count in stats:
            self.reservations_tree.insert("", tk.END, values=(
                f"Стол №{table_id}",
                count
            ))
    
    def update_waiters_stats(self):
        """Обновляет статистику по официантам"""
        try:
            month = int(self.waiter_month_combobox.get())
            year = int(self.waiter_year_entry.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный месяц или год")
            return
        
        # Очищаем таблицу
        for item in self.waiters_tree.get_children():
            self.waiters_tree.delete(item)
        
        # Исправленный запрос
        query = """
            SELECT 
                w.full_name,
                COUNT(o.id) as orders_count,
                COUNT(o.id) FILTER (WHERE o.status = 'paid') as paid_count,
                COALESCE(SUM(o.total) FILTER (WHERE o.status = 'paid'), 0) as total_sum,
                COALESCE(SUM(s.tips), 0) as tips_sum
            FROM users w
            LEFT JOIN orders o ON w.id = o.waiter_id
            AND EXTRACT(MONTH FROM o.created_at) = %s
            AND EXTRACT(YEAR FROM o.created_at) = %s
            LEFT JOIN shifts s ON w.id = s.waiter_id
            AND EXTRACT(MONTH FROM s.start_time) = %s
            AND EXTRACT(YEAR FROM s.start_time) = %s
            WHERE w.role_id = 2  -- Официанты
            GROUP BY w.full_name
            ORDER BY w.full_name
        """
        stats = self.execute_query(query, (month, year, month, year), fetch=True) or []
        
        # Заполняем таблицу
        for waiter, orders, payments, total, tips in stats:
            self.waiters_tree.insert("", tk.END, values=(
                waiter,
                orders,
                payments,
                f"{total} руб.",
                f"{tips:.2f} руб."
            ))
    

    def show_client_receipts(self):
        """Показывает чеки клиентов для официантов и админов"""
        if not self.current_user or self.current_user["role"] not in ["waiter", "admin"]:
            messagebox.showerror("Ошибка", "Доступно только для официантов и администраторов")
            return
        
        receipts_window = tk.Toplevel(self.root)
        receipts_window.title("Чеки клиентов")
        
        # Получаем список клиентов
        query = "SELECT id, full_name FROM users WHERE role_id = 3"  # 3 - роль client
        clients = self.execute_query(query, fetch=True) or []
        
        ttk.Label(receipts_window, text="Выберите клиента:").pack(pady=5)
        
        client_var = tk.StringVar()
        client_combobox = ttk.Combobox(receipts_window, textvariable=client_var, state="readonly")
        client_combobox["values"] = [f"{c[1]} (ID: {c[0]})" for c in clients]
        client_combobox.pack(pady=5)
        
        # Поля для периода
        ttk.Label(receipts_window, text="Период:").pack()
        period_frame = ttk.Frame(receipts_window)
        period_frame.pack(pady=5)
        
        ttk.Label(period_frame, text="С:").pack(side=tk.LEFT)
        start_entry = ttk.Entry(period_frame)
        start_entry.pack(side=tk.LEFT, padx=5)
        start_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        
        ttk.Label(period_frame, text="По:").pack(side=tk.LEFT)
        end_entry = ttk.Entry(period_frame)
        end_entry.pack(side=tk.LEFT, padx=5)
        end_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        text_area = tk.Text(receipts_window, height=20, width=60)
        text_area.pack(pady=10)
        
        def load_receipts():
            client_str = client_var.get()
            if not client_str:
                return
                
            client_id = int(client_str.split("ID: ")[1].rstrip(")"))
            start_date = start_entry.get()
            end_date = end_entry.get()
            
            query = """
                SELECT o.id, o.created_at, o.total, 
                    STRING_AGG(d.name || ' (' || oi.quantity || 'x' || oi.price || ' руб.)', ', ')
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN dishes d ON oi.dish_id = d.id
                WHERE o.client_id = %s 
                AND o.created_at::date BETWEEN %s AND %s
                GROUP BY o.id
                ORDER BY o.created_at
            """
            orders = self.execute_query(query, (client_id, start_date, end_date), fetch=True) or []
            
            text_area.delete(1.0, tk.END)
            if not orders:
                text_area.insert(tk.END, "Нет заказов за выбранный период")
                return
                
            text_area.insert(tk.END, f"Чеки клиента {client_str}\n")
            text_area.insert(tk.END, f"Период: с {start_date} по {end_date}\n\n")
            
            for order in orders:
                text_area.insert(tk.END, f"Заказ №{order[0]} от {order[1].strftime('%Y-%m-%d %H:%M')}\n")
                text_area.insert(tk.END, f"Блюда: {order[3]}\n")
                text_area.insert(tk.END, f"Сумма: {order[2]:.2f} руб.\n")
                text_area.insert(tk.END, "-"*50 + "\n")
        
        ttk.Button(receipts_window, text="Загрузить чеки", command=load_receipts).pack()

    def show_create_order_screen(self):
        """Показывает экран создания заказа"""
        if not self.current_user or self.current_user["role"] not in ["waiter", "admin", "client"]:
            messagebox.showerror("Ошибка", "Недостаточно прав для создания заказа")
            return
        
        # Проверяем, есть ли активная смена у официанта
        if self.current_user["role"] == "waiter" and not self.current_shift:
            messagebox.showerror("Ошибка", "Вы должны начать смену перед созданием заказа")
            return
        
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Создание заказа", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Форма заказа
        form_frame = ttk.Frame(self.content_area)
        form_frame.pack(fill=tk.X, pady=10)
        
        # Выбор стола
        ttk.Label(form_frame, text="Стол:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.order_table_combobox = ttk.Combobox(form_frame, state="readonly")
        self.order_table_combobox.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Заполняем список столов
        tables_query = "SELECT id, capacity FROM tables"
        tables = self.execute_query(tables_query, fetch=True) or []
        table_options = [f"№{t[0]} (мест: {t[1]})" for t in tables]
        self.order_table_combobox["values"] = table_options
        if table_options:
            self.order_table_combobox.current(0)
        
        # Клиент
        ttk.Label(form_frame, text="Клиент:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.order_client_entry = ttk.Entry(form_frame)
        self.order_client_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        if self.current_user:
            self.order_client_entry.insert(0, self.current_user["name"])
        
        # Список блюд
        ttk.Label(form_frame, text="Добавить блюдо:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.order_dish_combobox = ttk.Combobox(form_frame, state="readonly")
        self.order_dish_combobox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Заполняем список блюд
        dishes_query = "SELECT id, name, price FROM dishes WHERE quantity > 0"
        dishes = self.execute_query(dishes_query, fetch=True) or []
        dish_options = [f"{d[1]} ({d[2]} руб.)" for d in dishes]
        self.order_dish_combobox["values"] = dish_options
        if dish_options:
            self.order_dish_combobox.current(0)
        
        # Количество
        ttk.Label(form_frame, text="Количество:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.order_quantity_entry = ttk.Entry(form_frame)
        self.order_quantity_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        self.order_quantity_entry.insert(0, "1")
        
        # Кнопка добавления блюда
        ttk.Button(form_frame, text="Добавить в заказ", command=self.add_dish_to_order).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Текущий заказ (список блюд)
        ttk.Label(self.content_area, text="Текущий заказ:").pack(pady=5)
        
        self.current_order_items = ttk.Treeview(self.content_area, columns=("dish", "price", "quantity", "total"), show="headings")
        self.current_order_items.heading("dish", text="Блюдо")
        self.current_order_items.heading("price", text="Цена")
        self.current_order_items.heading("quantity", text="Количество")
        self.current_order_items.heading("total", text="Сумма")
        
        self.current_order_items.column("dish", width=200)
        self.current_order_items.column("price", width=100)
        self.current_order_items.column("quantity", width=100)
        self.current_order_items.column("total", width=100)
        
        self.current_order_items.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Итоговая сумма
        self.order_total_label = ttk.Label(self.content_area, text="Итого: 0 руб.", font=('Helvetica', 12))
        self.order_total_label.pack(pady=5)
        
        # Кнопки
        btn_frame = ttk.Frame(self.content_area)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Сохранить заказ", command=self.save_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отменить", command=self.show_orders_screen).pack(side=tk.LEFT, padx=5)
        
        # Инициализируем текущий заказ
        self.current_order = {
            "items": [],
            "total": 0
        }

    def show_client_receipts_for_client(self):
        """Показывает чеки для обычного клиента"""
        if not self.current_user or self.current_user["role"] != "client":
            return
        
        receipts_window = tk.Toplevel(self.root)
        receipts_window.title("Мои чеки")
        
        # Поля для периода
        ttk.Label(receipts_window, text="Период:").pack()
        period_frame = ttk.Frame(receipts_window)
        period_frame.pack(pady=5)
        
        ttk.Label(period_frame, text="С:").pack(side=tk.LEFT)
        start_entry = ttk.Entry(period_frame)
        start_entry.pack(side=tk.LEFT, padx=5)
        start_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        
        ttk.Label(period_frame, text="По:").pack(side=tk.LEFT)
        end_entry = ttk.Entry(period_frame)
        end_entry.pack(side=tk.LEFT, padx=5)
        end_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        text_area = tk.Text(receipts_window, height=20, width=60)
        text_area.pack(pady=10)
        
        def load_receipts():
            start_date = start_entry.get()
            end_date = end_entry.get()
            
            query = """
                SELECT o.id, o.created_at, o.total, 
                    STRING_AGG(d.name || ' (' || oi.quantity || 'x' || oi.price || ' руб.)', ', ')
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN dishes d ON oi.dish_id = d.id
                WHERE o.client_id = %s 
                AND o.created_at::date BETWEEN %s AND %s
                GROUP BY o.id
                ORDER BY o.created_at
            """
            orders = self.execute_query(query, (self.current_user["id"], start_date, end_date), fetch=True) or []
            
            text_area.delete(1.0, tk.END)
            if not orders:
                text_area.insert(tk.END, "Нет заказов за выбранный период")
                return
                
            text_area.insert(tk.END, f"Мои чеки\n")
            text_area.insert(tk.END, f"Период: с {start_date} по {end_date}\n\n")
            
            for order in orders:
                text_area.insert(tk.END, f"Заказ №{order[0]} от {order[1].strftime('%Y-%m-%d %H:%M')}\n")
                text_area.insert(tk.END, f"Блюда: {order[3]}\n")
                text_area.insert(tk.END, f"Сумма: {order[2]:.2f} руб.\n")
                text_area.insert(tk.END, "-"*50 + "\n")
        
        ttk.Button(receipts_window, text="Загрузить мои чеки", command=load_receipts).pack()

    def show_sessions_screen(self):
        """Показывает экран статистики по сессиям"""
        if not self.current_user or self.current_user["role"] != "admin":
            messagebox.showerror("Ошибка", "Доступ запрещен")
            return
        
        self.clear_content_area()
        
        title = ttk.Label(self.content_area, text="Статистика по сессиям", font=('Helvetica', 16))
        title.pack(pady=10)
        
        # Фильтры
        filter_frame = ttk.Frame(self.content_area)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Дата с:").pack(side=tk.LEFT)
        self.sessions_start_date = ttk.Entry(filter_frame)
        self.sessions_start_date.pack(side=tk.LEFT, padx=5)
        self.sessions_start_date.insert(0, (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        
        ttk.Label(filter_frame, text="Дата по:").pack(side=tk.LEFT)
        self.sessions_end_date = ttk.Entry(filter_frame)
        self.sessions_end_date.pack(side=tk.LEFT, padx=5)
        self.sessions_end_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        ttk.Button(filter_frame, text="Показать", command=self.update_sessions_stats).pack(side=tk.LEFT, padx=10)
        
        # Таблица сессий (удалены колонки orders и total)
        columns = ("client", "table", "start_time", "end_time", "duration")
        self.sessions_tree = ttk.Treeview(self.content_area, columns=columns, show="headings")
        
        # Настройка колонок
        self.sessions_tree.heading("client", text="Клиент")
        self.sessions_tree.heading("table", text="Стол")
        self.sessions_tree.heading("start_time", text="Начало")
        self.sessions_tree.heading("end_time", text="Конец")
        self.sessions_tree.heading("duration", text="Длительность")
        
        self.sessions_tree.column("client", width=200)
        self.sessions_tree.column("table", width=100)
        self.sessions_tree.column("start_time", width=150)
        self.sessions_tree.column("end_time", width=150)
        self.sessions_tree.column("duration", width=100)
        
        self.sessions_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Первоначальная загрузка данных
        self.update_sessions_stats()
    
    def update_sessions_stats(self):
        """Обновляет статистику по сессиям"""
        try:
            start_date = self.sessions_start_date.get()
            end_date = self.sessions_end_date.get()
            
            # Очищаем таблицу
            for item in self.sessions_tree.get_children():
                self.sessions_tree.delete(item)
            
            # Упрощенный запрос без информации о заказах и суммах
            query = """
                SELECT 
                    u.full_name as client,
                    t.id as table_id,
                    r.date + r.start_time as start_time,
                    r.date + r.end_time as end_time,
                    EXTRACT(EPOCH FROM (r.end_time - r.start_time))/60 as duration_min
                FROM reservations r
                JOIN users u ON r.client_id = u.id
                JOIN tables t ON r.table_id = t.id
                WHERE r.date BETWEEN %s AND %s
                AND r.status = 'active'
                ORDER BY r.date DESC, r.start_time DESC
            """
            stats = self.execute_query(query, (start_date, end_date), fetch=True) or []
            
            # Заполняем таблицу
            for row in stats:
                client, table, start, end, duration = row
                duration_str = f"{int(duration//60)}ч {int(duration%60)}м" if duration else "0м"
                
                self.sessions_tree.insert("", tk.END, values=(
                    client,
                    f"№{table}",
                    start.strftime("%Y-%m-%d %H:%M") if isinstance(start, datetime) else start,
                    end.strftime("%Y-%m-%d %H:%M") if isinstance(end, datetime) else end,
                    duration_str
                ))
                
            if not stats:
                messagebox.showinfo("Информация", "Нет данных о сессиях за выбранный период")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке сессий: {str(e)}")
            logging.error(f"Session stats error: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RestaurantApp(root)
    root.mainloop()