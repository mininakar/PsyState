import re
import sys
import os
import pymorphy3
from pymorphy3 import MorphAnalyzer as PymorphyAnalyzer
import pymorphy3_dicts_ru
# import pymorphy2
# from pymorphy2 import MorphAnalyzer as PymorphyAnalyzer
# import pymorphy2_dicts_ru
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QProgressBar
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
import vk_api
from yargy2 import Parser, rule, or_
from yargy2.predicates import in_, dictionary
from threading import Thread
import torch
from aniemore.recognizers.text import TextRecognizer
from aniemore.models import HuggingFaceModel
import heapq
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QFont
from PIL import Image
import requests
from io import BytesIO
from collections import Counter
import datetime
import pytz
from langdetect import detect
from langcodes import Language
from googletrans import Translator
from pathlib import Path
import inspect
import inspect
from pymorphy2 import MorphAnalyzer


# if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
#     bundle_dir = Path(sys._MEIPASS)
#     bundle_dir = Path(sys._MEIPASS)
# if hasattr(sys, '_MEIPASS'):
#     pymorphy3_dicts_path = os.path.join(sys._MEIPASS, 'pymorphy3_dicts')

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    bundle_dir = Path(sys._MEIPASS)
    bundle_dir = Path(sys._MEIPASS)
if hasattr(sys, '_MEIPASS'):
    pymorphy2_dicts_path = os.path.join(sys._MEIPASS, 'pymorphy2_dicts')
#глобальная переменная для вычисления общей опасности страницы
global DANGER
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

#функция для определения активности на странице
def get_posts_activity(access_token, user_id):
    vk_session = vk_api.VkApi(token=access_token)
    vk = vk_session.get_api()

    # Получаем записи со стены пользователя (первые 100 записей)
    wall = vk.wall.get(owner_id=user_id, count=100)

    posts = []
    for item in wall['items']:
        # Получаем время публикации поста в формате UTC
        utc_time = datetime.datetime.utcfromtimestamp(item.get('date'))

        # Получаем часовой пояс пользователя (если известен)
        user_timezone = None
        if 'post_source' in item and 'data' in item['post_source'] and 'timezone' in item['post_source']['data']:
            user_timezone = item['post_source']['data']['timezone']

        # Преобразуем время в местное время пользователя
        if user_timezone:
            timezone = pytz.timezone(f"Etc/GMT{user_timezone}")
            local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(timezone)
        else:
            # Если часовой пояс неизвестен, выводим время в UTC
            local_time = utc_time.replace(tzinfo=pytz.utc)

        # Добавляем текст поста и местное время его публикации в список
        post_text = item.get('text')
        posts.append((post_text, local_time))

    # Собираем подсчет постов по часам в часовом поясе пользователя
    post_hours_counter = Counter()
    for post in posts:
        hour = post[1].hour
        post_hours_counter[hour] += 1

    # Возвращаем результаты анализа
    return post_hours_counter
def get_avatar_comments_count(vk, user_name):
    user_info = vk.users.get(user_ids=user_name, fields='photo_max_orig')[0]
    user_id = user_info['id']

    # Получение информации о фотографиях профиля пользователя
    photos = vk.photos.get(owner_id=user_id, album_id='profile', rev=1)

    # Выбор основной фотографии профиля (первая фотография)
    if photos['count'] > 0:
        main_photo = photos['items'][0]
        photo_id = main_photo['id']
        owner_id = main_photo['owner_id']

        # Получение комментариев к основной фотографии профиля
        avatar_comments_info = vk.photos.getComments(owner_id=owner_id, photo_id=photo_id, count=100)

        # Подсчет количества комментариев
        comments_count = avatar_comments_info['count']
        if comments_count>0:
            print('Человек социально активный')
        else:
            print('Человек не активный')
        return comments_count
    else:
        return 0
#tokenizer = MorphTokenizer()


#morph = pymorphy3.MorphAnalyzer()
#morph = PymorphyAnalyzer()

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

        self.img_label = QLabel("")
        self.layout.addWidget(self.img_label)

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


        self.max_hour_value = QLabel('')
        self.layout.addWidget(self.max_hour_value)

        self.insomnia_posts = QLabel('')
        self.layout.addWidget(self.insomnia_posts)

        self.result = QLabel("")
        self.layout.addWidget(self.result)
        self.result.setStyleSheet(
            "QLabel { font-size: 20px; color: #C40C0C;  }")

        self.back_button = QPushButton("Назад")
        self.back_button.setGeometry(QtCore.QRect(600, 480, 191, 61))
        self.back_button.setObjectName("pushButton")
        self.back_button.setStyleSheet(pushButton_StyleSheet)
        # self.back_button.setStyleSheet(
        #     "font-size: 18px; padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;")
        self.back_button.clicked.connect(self.close)
        self.back_button.clicked.connect(main_window.show)
        self.layout.addWidget(self.back_button)
        self.setLayout(self.layout)

    def reset(self):
        # Сброс всех меток на начальные значения
        self.info_label.setText("Идет сохранение постов в файл...")
        self.emot_label1.setText("Идет определение эмоций по странице...")
        self.words_label.setText("")

    def set_label_text(self, text):
        self.info_label.setText(text)

    def set_img_label(self, text):
        self.img_label.setText(text)

    def emot_label (self, text):
        self.emot_label.setText(text)

    def set_emot_label_text(self, text):
        self.emot_label1.setText(text)  # Update the text of emot_label1

    def set_status_analyze_text(self, text):
        self.status_analyze.setText(text)

    def set_result(self, text):
        self.result.setText(text)

    def set_max_hour_value(self, text):
        self.max_hour_value.setText(text)

    def set_insomnia_posts(self, text):
        self.insomnia_posts.setText(text)

    def set_words_label_text(self, text):
        self.words_label.setText(text)

    def display_user_info(self, first_name, last_name,status, image_url, matching_groups_count):
        self.name_label.setText(f"Имя: {first_name}")
        self.last_name_label.setText(f"Фамилия: {last_name}")

        self.status.setText(f"Статус: {status}")
        #self.img_label.setText(f"ССылка: {image_url}")

        if image_url:
            pixmap = QPixmap()
            pixmap.loadFromData(requests.get(image_url).content)
            self.image_label.setPixmap(pixmap)
            self.image_label.setAlignment(Qt.AlignCenter)

        self.matching_groups_label.setText(f"Количество групп, содержащих слова из файла groups.txt: {matching_groups_count}")

pushButton_StyleSheet ='''
#pushButton {
  font-size: 20px;
  color: #fff;
  background-color: #78a4e8;
  border: none;
  width: 191px;
  height: 61px;
  border-radius: 15px;

}

#pushButton:hover {background-color: #4483e4;}

#pushButton:pressed {
  background-color: #686c73;

}
'''

def is_grayscale(image):
    return image.mode == 'L'

def get_image_color_palette(image_url):

    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))

    if is_grayscale(image):
        # Return the grayscale image and type
        return image, 'Grayscale'
    else:
        # Return the original color image and type
        return image, 'Color'

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Главное окно")
        self.setGeometry(100, 100, 600, 600)

        self.label = QLabel("Введите id пользователя:")
        self.label.setStyleSheet("font-size: 24px; color: #333;")

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText('Введите id')
        self.input_field.setStyleSheet("font-size: 20px; padding: 10px; border: 2px solid #4CAF50; border-radius: 5px;")
        layout = QVBoxLayout()

        #Кнопка
        self.submit_button = QPushButton("Вывести данные")
        self.submit_button.setGeometry(QtCore.QRect(600, 480, 191, 61))
        self.submit_button.setObjectName("pushButton")
        self.submit_button.setStyleSheet(pushButton_StyleSheet)
        self.submit_button.clicked.connect(self.open_output_window)


        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.submit_button)
        self.setLayout(self.layout)

        self.output_window = OutputWindow(self)
        self.input_field.returnPressed.connect(self.open_output_window)



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

            self.output_window.reset()  # Сброс состояния окна
            self.output_window.show()
        else:
            print("Matching groups count is None")


    def fetch_user_info(self, user_id):
        global DANGER

        params = {
            'user_ids': user_id,
            'fields': 'photo_max_orig, first_name, last_name, status, about, activities, books, career, counters, country, interests, movies, personal, relatives, relation',
            'access_token': access_token,
            'v': '5.131'
        }
        try:
            if not re.match(r'^[a-zA-Z0-9_]+$', user_id):
                msg_box = QMessageBox()
                msg_box.setWindowTitle('Ошибка')
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setStandardButtons(QMessageBox.Ok)


                # Установка текста с новым стилем
                msg_box.setText("<span style='font-size: 24px; color: #333;'>Некорректно введен id.</span>")

                msg_box.setStyleSheet(
                    "QPushButton {"
                    "font-size: 20px;"
                    "color: #fff;"
                    "background-color: #78a4e8;"
                    "border: none;"
                    "border-radius: 7px;"
                    "width: 75px;"
                    "height: 30px;"
                    "}"
                    "QPushButton:hover {"
                    "background-color: #4483e4;"
                    "}"
                    "QPushButton:pressed {"
                    "background-color: #686c73;"
                    "}"
                )
                msg_result = msg_box.exec_()

                if msg_result == QMessageBox.Ok:
                    # Закрыть текущее окно
                    #self.close()
                    # Создать и показать новое главное окно
                    new_main_window = MainWindow()
                    new_main_window.show()
                    return

            response = requests.get('https://api.vk.com/method/users.get', params=params)
            user_info = response.json()
            print (user_info)
            if 'response' in user_info and user_info['response']==[]:
                msg_box = QMessageBox()
                msg_box.setWindowTitle('Ошибка')
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText("<span style='font-size: 24px; color: #333;'>Такой страницы не существует.</span>")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.setStyleSheet(
                    "QPushButton {"
                    "font-size: 20px;"
                    "color: #fff;"
                    "background-color: #78a4e8;"
                    "border: none;"
                    "border-radius: 7px;"
                    "width: 75px;"
                    "height: 30px;"
                    "}"
                    "QPushButton:hover {"
                    "background-color: #4483e4;"
                    "}"
                    "QPushButton:pressed {"
                    "background-color: #686c73;"
                    "}"
                )
                msg_result = msg_box.exec_()

                if msg_result == QMessageBox.Ok:
                    # Закрыть текущее окно
                    # self.close()
                    # Создать и показать новое главное окно
                    new_main_window = MainWindow()
                    new_main_window.show()
                    return

            if 'response' in user_info and user_info['response']:
                user_data = user_info['response'][0]
                if 'deactivated' in user_data:
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle('Ошибка')
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setText("<span style='font-size: 24px; color: #333;'>Страница забанена или удалена</span>")
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.setStyleSheet(
                        "QPushButton {"
                        "font-size: 20px;"
                        "color: #fff;"
                        "background-color: #78a4e8;"
                        "border: none;"
                        "border-radius: 7px;"
                        "width: 75px;"
                        "height: 30px;"
                        "}"
                        "QPushButton:hover {"
                        "background-color: #4483e4;"
                        "}"
                        "QPushButton:pressed {"
                        "background-color: #686c73;"
                        "}"
                    )
                    msg_result = msg_box.exec_()

                    if msg_result == QMessageBox.Ok:
                        # Закрыть текущее окно
                        # self.close()
                        # Создать и показать новое главное окно
                        new_main_window = MainWindow()
                        new_main_window.show()
                        return

                if 'is_closed' in user_data and user_data['is_closed']:
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle('Ошибка')
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setText("<span style='font-size: 24px; color: #333;'>Страница закрыта</span>")
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.setStyleSheet(
                        "QPushButton {"
                        "font-size: 20px;"
                        "color: #fff;"
                        "background-color: #78a4e8;"
                        "border: none;"
                        "border-radius: 7px;"
                        "width: 75px;"
                        "height: 30px;"
                        "}"
                        "QPushButton:hover {"
                        "background-color: #4483e4;"
                        "}"
                        "QPushButton:pressed {"
                        "background-color: #686c73;"
                        "}"
                    )
                    msg_result = msg_box.exec_()

                    if msg_result == QMessageBox.Ok:
                        # Закрыть текущее окно
                        # self.close()
                        # Создать и показать новое главное окно
                        new_main_window = MainWindow()
                        new_main_window.show()
                        return

            if 'response' in user_info and user_info['response']:
                user_data = user_info['response'][0]
                if 'counters' in user_data:
                    counters = user_data['counters']
                    if 'friends' in counters:
                        friends_count = counters['friends']
                        if (friends_count < 10):
                            DANGER = DANGER + 0.5
                            print('друзья', DANGER)
                        elif (friends_count > 1000):
                            DANGER = DANGER + 0.2
                            print('друзья', DANGER)
                    if 'photos' in counters:
                        photos_count = counters['photos']
                        if (photos_count == 0):
                            DANGER = DANGER + 0.5
                            print('кол-во фото', DANGER)
                if 'photo_max_orig' in user_data:
                    image_url = user_data['photo_max_orig']
                    print(image_url)
                    #color_palette = get_image_color_palette(image_url)
                    result_image, image_type = get_image_color_palette(image_url)
                    if image_type == 'Grayscale':
                        img_label = "Изображение ЧБ"
                        #self.output_window.set_img_label(img_label)
                        DANGER+=0.5
                        print("Изображение ЧБ")
                    else:
                        img_label = " Изображение цветное"
                        #self.output_window.set_img_label(img_label)
                        print("Изображение цветное")
                    #print (color_palette)
                    print('фото', DANGER)

            print('итог', DANGER)

            return user_info
        except Exception as e:
            print("Ошибка при получении информации о пользователе:", e)
            return None

    def fetch_user_groups(self, user_id):
        global DANGER
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

            if matching_groups_count >0:
                DANGER+=0.5
                print('группа', DANGER)
            return matching_groups_count

        except Exception as e:
            print("Error fetching user groups:", e)
            return 0

    def fetch_user_wall(self, user_id):
        self.output_window.set_label_text("")
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

        clean_json('user_posts.json')
        remove_newlines_from_posts('user_posts.json')
        self.output_window.set_label_text("Все текста постов успешно записаны в файл 'user_posts.json'.")

        with open('user_posts.json', 'r', encoding='utf-8') as file:
            data = json.load(file)

        model = HuggingFaceModel.Text.Bert_Tiny
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        tr = TextRecognizer(model=model, device=device)

        # Получаем первый элемент из списка пользователей
        for line in data:
            result = tr.recognize(line, return_single_label=False)

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

            positive_parser = Parser(positive_rule)
            negative_parser = Parser(negative_rule)

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

        # Сбрасываем переменные перед новым запросом
        self.output_window.set_words_label_text("")  # Очищаем текст

        with open('user_posts.json', 'r', encoding='utf-8') as file:
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
        print(emotion_counts)

        top_emotions = heapq.nlargest(3, emotion_counts, key=emotion_counts.get)
        emot_label_text = ""
        for i, emotion in enumerate(top_emotions, 1):
            emot_label_text += f"Топ-{i} эмоция: {emotion}, количество вхождений: {emotion_counts[emotion]}\n"

        self.output_window.set_emot_label_text(emot_label_text)  # Call the method to update the label text

        negative_words_used = set()
        # Проходимся по всем постам и ищем слова из negative_list.txt
        for line in data:
            for word in line.split():
                if word.lower() in negative_word_list:
                    negative_words_used.add(word.lower())

        # Выводим список слов из negative_list.txt, которые использовались в постах
        self.output_window.set_words_label_text(
            'Слова из negative_list.txt, использованные в постах:\n' + '\n'.join(negative_words_used))

        #Вычисляем время постов
        posts_activity = get_posts_activity(access_token, user_id)
        print("Активность пользователя по часам:")
        for hour, count in sorted(posts_activity.items()):
            print(f"В {hour} часов (местное время): {count} постов")
        max_hour, max_count = posts_activity.most_common(1)[0]
        print(f"Чаще всего посты появляются в {max_hour} часов: {max_count} постов")
        self.output_window.set_max_hour_value(f"Чаще всего посты появляются в {max_hour} часов: {max_count} постов")

        # Проверяем наличие постов между 3 и 5 утра. бессоница
        insomnia_posts = [(hour, count) for hour, count in posts_activity.items() if 3 <= hour <= 5]
        if insomnia_posts:
            total_insomnia_posts = sum(count for hour, count in insomnia_posts)
            print(f"У человека существует риск бессоницы, так как количество постов между 3 и 5 утра: {total_insomnia_posts}")
            self.output_window.set_insomnia_posts(f"У человека существует риск бессоницы, так как количество постов между 3 и 5 утра: {total_insomnia_posts}")

        comments_count = get_avatar_comments_count(vk, user_id)
        print(f"Количество комментариев под аватаркой: {comments_count}")

        #Общий вывод по странице
        self.output_window.set_result(f'Страница опасна на {DANGER} по 5-балльной шкале')


if __name__ == "__main__":

    # import sys
    # if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    #     os.environ["PYMORPHY3_DICT_PATH"] = str(pathlib.Path(sys._MEIPASS).joinpath('pymorphy3_dicts_ru/data'))

    app = QApplication(sys.argv)
    font = QFont()
    font.setFamily("Century Gothic")
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
