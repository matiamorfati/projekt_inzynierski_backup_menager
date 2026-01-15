import unittest
from TaskManager.task import Task


class TestTask(unittest.TestCase):

    def test_init_sets_attributes(self):
        # Test sprawdza, czy przy tworzeniu zadania
        # pola obiektu są poprawnie ustawione
        task = Task("Trening", "Siłownia", 2)

        self.assertEqual(task.title, "Trening")
        self.assertEqual(task.description, "Siłownia")
        self.assertEqual(task.priority, 2)
        self.assertEqual(task.status, "todo") 

    def test_mark_done_changes_status(self):
        # Test sprawdza czy metoda mark_done()
        # zmienia status zadania na done
        task = Task("Trening", "Siłownia", 2)
        task.mark_done()

        self.assertEqual(task.status, "done")

    def test_as_dict_returns_expected_keys(self):
        # Test sprawdza czy metoda as_dict()
        # zwraca poprawne dane w formie słownika
        task = Task("Trening", "Siłownia", 2, status="done")
        data = task.as_dict()

        self.assertEqual(data["title"], "Trening")
        self.assertEqual(data["description"], "Siłownia")
        self.assertEqual(data["priority"], 2)
        self.assertEqual(data["status"], "done")

    def test_format_for_console_contains_title(self):
        # Test sprawdza czy tekst wyświetlany w konsoli
        # zawiera tytuł zadania
        task = Task("Trening", "Siłownia", 2)
        text = task.format_for_console()

        self.assertIn("Trening", text)


if __name__ == "__main__":
    unittest.main()
