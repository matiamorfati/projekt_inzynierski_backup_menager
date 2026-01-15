import unittest
from TaskManager.task_list import TaskList
from TaskManager.task import Task


# Atrapa bazy danych zamiast prawdziwej bazy SQLite, dzięki temu testujemy tylko logikę TaskList
class FakeTaskDbManager:
    def __init__(self):
        self.tasks = []
        self.next_id = 1

    def add_task(self, task):
        # Symulujemy nadawanie ID jak w bazie danych
        task.id = self.next_id
        self.next_id += 1
        self.tasks.append(task)
        return task.id

    def get_tasks(self):
        # Zwracamy kopię listy zadań
        return list(self.tasks)

    def update_task(self, task):
        # Nadpisujemy zadanie o tym samym ID
        for i, t in enumerate(self.tasks):
            if t.id == task.id:
                self.tasks[i] = task

    def delete_task(self, task_id):
        # Usuwamy zadanie po ID
        self.tasks = [t for t in self.tasks if t.id != task_id]


class TestTaskList(unittest.TestCase):

    def setUp(self):
        # Każdy test dostaje świeżą atrapę bazy i TaskList
        self.fake_db = FakeTaskDbManager()
        self.task_list = TaskList(self.fake_db)

    def test_add_task_saves_task(self):
        # Sprawdzamy czy dodanie zadania faktycznie zapisuje je w bazie
        self.task_list.add_task("Trening", "Siłownia", 2)
        tasks = self.task_list.get_tasks()

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, "Trening")

    def test_mark_done_changes_status(self):
        # Sprawdzamy czy zmiana statusu ustawia done poprawnie
        self.task_list.add_task("Trening", "Siłownia", 2)
        task_id = self.task_list.get_tasks()[0].id

        self.task_list.mark_done(task_id)

        self.assertEqual(self.task_list.get_tasks()[0].status, "done")

    def test_delete_task_removes_task(self):
        # Sprawdzamy czy usunięcie zadania faktycznie je kasuje
        self.task_list.add_task("Trening", "Siłownia", 2)
        task_id = self.task_list.get_tasks()[0].id

        self.task_list.delete_task(task_id)

        self.assertEqual(len(self.task_list.get_tasks()), 0)


if __name__ == "__main__":
    unittest.main()
