from .task_db_manager import TaskDbManager
from .task import Task


class TaskList:
    def __init__(self, db_manager: TaskDbManager):
        self.db = db_manager

    def add_task(self, title, description, priority):
        # tworzy nowe zadanie i zapisuje je w bazie danych
        task = Task(title, description, priority)
        self.db.add_task(task)
        return task

    def get_tasks(self):
        # zwraca wszystkie zadania z bazy
        return self.db.get_tasks()

    def edit_task(self, task_id, data: dict):
        # edytuje dane istniejcaego zadania szukamy zadania po ID
        tasks = self.db.get_tasks()
        for task in tasks:
            if task.id == task_id:
                # aktualizujemy tylko te pola ktore sa w solwniku 
                task.title = data.get("title", task.title)
                task.description = data.get("description", task.description)
                task.priority = data.get("priority", task.priority)
                task.status = data.get("status", task.status)

                # zapis zmian do bazy
                self.db.update_task(task)
                return True
        return False

    def delete_task(self, task_id):
        # usuwa zadanie z bazy danych po ID
        self.db.delete_task(task_id)

    def mark_done(self, task_id):
        # oznacza zadanie jako wykonane 
        tasks = self.db.get_tasks()
        for task in tasks:
            if task.id == task_id:
                task.mark_done()
                self.db.update_task(task)
                return True
        return False
