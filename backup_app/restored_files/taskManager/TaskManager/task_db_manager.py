import sqlite3
from .task import Task


class TaskDbManager:
    def __init__(self, db_path: str):
        # zapisujemy ścieżkę do pliku bazy danych i od razu łączymy się z bazą SQLite
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)

        # tworzymy tabelę jeśli jeszcze nie istnieje
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority INTEGER,
                status TEXT
            )
            """
        )
        self.conn.commit()

    def add_task(self, task: Task):
        # dodaje nowe zadanie do bazy danych
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title, description, priority, status) VALUES (?, ?, ?, ?)",
            (task.title, task.description, task.priority, task.status),
        )
        self.conn.commit()

        # zapisujemy id wygenerowane przez bazę w obiekcie Task
        task.id = cursor.lastrowid
        return task.id

    def get_tasks(self):
        # pobiera wszystkie zadania z bazy danych
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, description, priority, status FROM tasks")
        rows = cursor.fetchall()

        tasks = []
        for row in rows:
            task_id, title, description, priority, status = row
            t = Task(title, description, priority, status)
            t.id = task_id
            tasks.append(t)

        return tasks

    def update_task(self, task: Task):
        # aktualizuje dane zadania w bazie jeśli zadanie nie ma id to nic nie robimy
        if task.id is None:
            return

        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, priority = ?, status = ?
            WHERE id = ?
            """,
            (task.title, task.description, task.priority, task.status, task.id),
        )
        self.conn.commit()

    def delete_task(self, task_id: int):
        # usuwa zadanie z bazy po id
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
