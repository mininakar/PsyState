import requests
import re
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QProgressBar
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
import vk_api
from yargy import Parser, rule, or_
from yargy.predicates import in_, dictionary
from yargy.tokenizer import MorphTokenizer
from threading import Thread
import torch
from aniemore.recognizers.text import TextRecognizer
from aniemore.models import HuggingFaceModel
import heapq
from langdetect import detect
from langcodes import Language
from googletrans import Translator

#глобальная переменная для вычисления общей опасности страницы
DANGER = 0


#функция для загрузки файла
def load_word_list(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        word_list = [word.strip() for word in file.readlines()]
    return word_list

# функция для удаления  \n
def remove_newlines_from_posts(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Обходим каждый пост и удаляем символы новой строки из текста
    for post in data:
        if isinstance(post, str):
            post_without_newlines = post.replace('\n', ' ')  # Удаляем символы новой строки
            data[data.index(post)] = post_without_newlines  # Заменяем оригинальный текст поста на очищенный
        # Записываем очищенные данные обратно в файл
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

#функция для очистки json
def clean_json(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
    # Удаляем пустые строки и символы новой строки
    cleaned_data = [line.strip() for line in data if line.strip()]
    # Записываем очищенные данные обратно в файл
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(cleaned_data, file, ensure_ascii=False, indent=4)

tokenizer = MorphTokenizer()

class OutputWindow(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.setWindowTitle("Данные пользователя")
        self.setGeometry(100, 100, 600, 600)
        self.setStyleSheet("background-color: #FFFFFF;")

        self.layout = QVBoxLayout()

        self.name_label = QLabel("Имя: ")
        self.last_name_label = QLabel("Фамилия: ")

        self.image_label = QLabel()
        self.matching_groups_label = QLabel()

        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.last_name_label)

        self.status = QLabel("Статус: ")
        self.layout.addWidget(self.status)

        self.status_analyze = QLabel(" ")
        self.layout.addWidget(self.status_analyze)

        self.layout.addWidget(self.image_label)
        self.layout.addWidget(self.matching_groups_label)

        self.info_label = QLabel("Идет сохранение постов в файл...")
        self.layout.addWidget(self.info_label)

        # self.emot_label = QLabel("Эмоции:")
        # self.layout.addWidget(self.emot_label)

        self.emot_label1 = QLabel("Идет определение эмоций по странице...")
        self.layout.addWidget(self.emot_label1)

        self.words_label = QLabel("")
        self.layout.addWidget(self.words_label)
        # self.analyze_thread = threading.Thread(target=self.analyze_user_posts, args=(user_id,))
        # self.analyze_thread.start()

        # self.progress_bar = QProgressBar()
        # self.layout.addWidget(self.progress_bar)

        self.back_button = QPushButton("Назад")
        self.back_button.setStyleSheet(
            "font-size: 18px; padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;")
        self.back_button.clicked.connect(self.close)
        self.back_button.clicked.connect(main_window.show)
        self.layout.addWidget(self.back_button)
        self.setLayout(self.layout)

    def set_label_text(self, text):
        self.info_label.setText(text)

    def emot_label (self, text):
        self.emot_label.setText(text)

    def set_emot_label_text(self, text):
        self.emot_label1.setText(text)  # Update the text of emot_label1

    def set_status_analyze_text(self, text):
        self.status_analyze.setText(text)

    def set_words_label_text(self, text):
        self.words_label.setText(text)

    def display_user_info(self, first_name, last_name,status, image_url, matching_groups_count):
        self.name_label.setText(f"Имя: {first_name}")
        self.last_name_label.setText(f"Фамилия: {last_name}")

        self.status.setText(f"Статус: {status}")

        if image_url:
            pixmap = QPixmap()
            pixmap.loadFromData(requests.get(image_url).content)
            self.image_label.setPixmap(pixmap)
            self.image_label.setAlignment(Qt.AlignCenter)

        self.matching_groups_label.setText(f"Количество групп, содержащих слова из файла groups.txt: {matching_groups_count}")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Главное окно")

        self.label = QLabel("Введите id пользователя:")
        self.label.setStyleSheet("font-size: 24px; color: #333;")
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet("font-size: 20px; padding: 5px; border: 2px solid #ccc; border-radius: 5px;")
        self.submit_button = QPushButton("Вывести данные")
        self.submit_button.setStyleSheet(
            "font-size: 18px; padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;")
        self.submit_button.clicked.connect(self.open_output_window)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.submit_button)
        self.setLayout(self.layout)

        self.output_window = OutputWindow(self)


    def open_output_window(self):
        user_id = self.input_field.text()
        user_info = self.fetch_user_info(user_id)
        if user_info:
            matching_groups_count = self.fetch_user_groups(user_id)
            self.output_window.display_user_info(user_info['response'][0]['first_name'],
                                                 user_info['response'][0]['last_name'],
                                                 user_info['response'][0]['status'],
                                                 user_info['response'][0]['photo_max_orig'],
                                                 matching_groups_count)
        Thread(target=self.fetch_user_wall, args=(user_id,)).start()

        self.output_window.show()

    def fetch_user_info(self, user_id):
        params = {
            'user_ids': user_id,
            'fields': 'photo_max_orig, first_name, last_name, status, about, activities, books, career, counters, country, interests, movies, personal, relatives, relation',
            'access_token': access_token,
            'v': '5.131'
        }
        try:
            if not re.match(r'^[a-zA-Z0-9_]+$', user_id):
                QMessageBox.warning(self, 'Ошибка', 'Некорректно введен id.')
                return

            response = requests.get('https://api.vk.com/method/users.get', params=params)
            user_info = response.json()
            if 'error' in user_info:
                QMessageBox.warning(self, 'Ошибка', 'Такой страницы не существует.')
                return

            if 'response' in user_info and user_info['response']:
                user_data = user_info['response'][0]
                if 'deactivated' in user_data:
                    QMessageBox.warning(self, 'Ошибка', 'Страница забанена или удалена')
                    return

                if 'is_closed' in user_data and user_data['is_closed']:
                    QMessageBox.warning(self, 'Ошибка', 'Страница закрыта')
                    return

            if 'status' in user_data and user_data['status'] != "":
                translator = Translator()

                status = user_data['status']
                print("Статус: ", user_data['status'])
                print("Анализ статуса: ")

                try:
                    language_code = detect(status)
                    language_name = Language.get(language_code).display_name()
                    print("Определенный язык:", language_name)

                    # Если язык статуса не русский, выполняем перевод
                    if language_code != 'ru':
                        translated_status = translator.translate(status, dest='ru').text
                        print("Переведенный статус на русский:", translated_status)
                except Exception as e:
                    print("Ошибка при анализе или переводе статуса:", e)


                model = HuggingFaceModel.Text.Bert_Tiny
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                tr = TextRecognizer(model=model, device=device)
                status_result = tr.recognize(status, return_single_label=False)

                self.output_window.set_status_analyze_text(
                    "Анализ статуса: \n" + '\n'.join(heapq.nlargest(3, status_result, key=status_result.get)))

                print(heapq.nlargest(3, status_result, key=status_result.get))
            return user_info
        except Exception as e:
            print("Error fetching user info:", e)
            return None

    def fetch_user_groups(self, user_id):
        vk_session = vk_api.VkApi(token=access_token)
        vk = vk_session.get_api()

        # Получение списка подписок пользователя
        try:
            other_user_id = vk.users.get(user_ids=user_id)[0]['id']
            subscriptions = vk.users.getSubscriptions(user_id=other_user_id)
            group_names = []
            for item in subscriptions['groups']['items']:
                if isinstance(item, int):
                    group_info = vk.groups.getById(group_id=item)
                    group_names.append(group_info[0]['name'])
                elif isinstance(item, dict):
                    group_names.append(item.get('name', 'Unknown'))

            # Загрузка списка слов из файла groups.txt
            with open('groups.txt', 'r', encoding='utf-8') as file:
                groups_word_list = [line.strip() for line in file]

            # Сравнение групп пользователя с словами из groups.txt
            matching_groups_count = sum(
                1 for group_name in group_names if any(word in group_name for word in groups_word_list))

            return matching_groups_count

        except Exception as e:
            print("Error fetching user groups:", e)
            return 0

    def fetch_user_wall(self, user_id):
        vk_session = vk_api.VkApi(token=access_token)
        vk = vk_session.get_api()

        count_per_request = 100
        total_count = 1000
        all_posts = []
        offset = 0

        while offset < total_count:
            posts = vk.wall.get(owner_id=user_id, count=count_per_request, offset=offset)
            all_posts.extend(posts['items'])
            offset += count_per_request

        with open('user_wall.json', 'w', encoding='utf-8') as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=4)

        self.output_window.set_label_text("Все посты успешно записаны в файл 'user_wall.json'.")

        with open('user_wall.json', 'r', encoding='utf-8') as f:
            posts_data = json.load(f)

        user_posts_text = []

        for post in posts_data:
            text = post.get('text', '')
            user_posts_text.append(text)

        with open('user_posts.json', 'w', encoding='utf-8') as f:
            json.dump(user_posts_text, f, ensure_ascii=False, indent=4)

        #self.output_window.set_label_text("Все текста постов успешно записаны в файл 'user_posts.json'.")

        clean_json('user_posts.json')
        #self.output_window.set_label_text("'user_posts.json' очищены пустые строки.")
        #print("'user_posts.json' очищены пустые строки.")

        remove_newlines_from_posts('user_posts.json')
        self.output_window.set_label_text("Все текста постов успешно записаны в файл 'user_posts.json'.")
        #print("'user_posts.json' заменяем enter на пробелы.")

        with open('user_posts.json', 'r', encoding='utf-8') as file:
            data = json.load(file)

        model = HuggingFaceModel.Text.Bert_Tiny
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        tr = TextRecognizer(model=model, device=device)

        # Получаем первый элемент из списка пользователей
        for line in data:
            result = tr.recognize(line, return_single_label=False)
            #self.output_window.emot_label(heapq.nlargest(3, result, key=result.get))
            # print(heapq.nlargest(3, result, key=result.get))

            # Путь к файлам с положительным и отрицательным списком слов
            positive_file_path = "positive_list.txt"
            negative_file_path = "negative_list.txt"

            # Загрузка списков слов из файлов
            positive_word_list = load_word_list(positive_file_path)
            # positive_word_list = [word for word in positive_word_list if isinstance(word, str)]

            negative_word_list = load_word_list(negative_file_path)

            positive_rule = or_(
                rule(in_(positive_word_list)))

            negative_rule = or_(
                rule(in_(negative_word_list)))

            positive_parser = Parser(positive_rule, tokenizer=tokenizer)
            negative_parser = Parser(negative_rule, tokenizer=tokenizer)

            positive_count = 0
            negative_count = 0

            for word in line.split():
                if word.lower() in positive_word_list:
                    positive_count += 1
                elif word.lower() in negative_word_list:
                    negative_count += 1
            positive_matches = positive_parser.findall(line)
            negative_matches = negative_parser.findall(line)
            total_words = len(line.split())

            positive_words_count = len(list(positive_parser.findall(line)))
            negative_words_count = len(list(negative_parser.findall(line)))

            if total_words != 0:
                positive_percentage = (positive_words_count / total_words) * 100
                negative_percentage = (negative_words_count / total_words) * 100
            else:
                positive_percentage = 0
                negative_percentage = 0
        with open('data2.json', 'r', encoding='utf-8') as file:
            data2 = json.load(file)
        emotion_counts = {}
        model = HuggingFaceModel.Text.Bert_Tiny
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        tr = TextRecognizer(model=model, device=device)
        for line in data2:
            result = tr.recognize(line, return_single_label=False)
            top_emotions = heapq.nlargest(3, result, key=result.get)
            for emotion in top_emotions:
                if emotion in emotion_counts:
                    emotion_counts[emotion] += 1
                else:
                    emotion_counts[emotion] = 1

        # Выводим топ-3 наиболее часто встречающихся эмоции
        # top_emotions = heapq.nlargest(3, emotion_counts, key=emotion_counts.get)
        # for i, emotion in enumerate(top_emotions, 1):
        #     self.output_window.emot_label1(f"Топ-{i} эмоция: {emotion}, количество вхождений: {emotion_counts[emotion]}")
        #     print(f"Топ-{i} эмоция: {emotion}, количество вхождений: {emotion_counts[emotion]}")

        top_emotions = heapq.nlargest(3, emotion_counts, key=emotion_counts.get)
        emot_label_text = ""
        for i, emotion in enumerate(top_emotions, 1):
            emot_label_text += f"Топ-{i} эмоция: {emotion}, количество вхождений: {emotion_counts[emotion]}\n"
            #print(f"Топ-{i} эмоция: {emotion}, количество вхождений: {emotion_counts[emotion]}")
        self.output_window.set_emot_label_text(emot_label_text)  # Call the method to update the label text

        negative_words_used = set()
        # Проходимся по всем постам и ищем слова из negative_list.txt
        for line in data:
            for word in line.split():
                if word.lower() in negative_word_list:
                    negative_words_used.add(word.lower())

        # Выводим список слов из negative_list.txt, которые использовались в постах
        #print("Слова из negative_list.txt, использованные во всех постах:")
        self.output_window.set_words_label_text(
            'Слова из negative_list.txt, использованные во всех постах:\n' + '\n'.join(negative_words_used))
        # for word in negative_words_used:
        #     print(word)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
