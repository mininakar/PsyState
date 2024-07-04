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


def load_word_list(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        word_list = [word.strip() for word in file.readlines()]
    return word_list
# функция для удаления  \n
def remove_newlines_from_posts(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
    # Обходим каждый пост и удаляем символы новой строки из текста
    for i, post in enumerate(data):
        if isinstance(post, str):
            post_without_newlines = post.replace('\n', ' ')  # Удаляем символы новой строки
            #post_without_newlines.replce('\\', '')
            data[i] = post_without_newlines  # Заменяем оригинальный текст поста на очищенный
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
#функция для получения постов со стены
def get_posts(user_id, access_token, count_per_request=100, total_count=1000):
    all_posts = []
    offset = 0
    while offset < total_count:
        params = {
            'owner_id': user_id,
            'filter': 'all',
            'count': count_per_request,
            'offset': offset,
            'access_token': access_token,
            'v': '5.131'
        }
        response = requests.get('https://api.vk.com/method/wall.get', params=params)
        posts = response.json().get('response', {}).get('items', [])
        all_posts.extend(posts)
        if not posts:
            break
        offset += count_per_request
    return all_posts
def get_post_info(post):
    repost_info = post['copy_history'][0]
    repost_owner_name = ''

    if 'from_id' in repost_info:
        repost_owner_id = repost_info['from_id']
        if repost_owner_id > 0:  # пользователь
            repost_owner_info = get_user_info(repost_owner_id)
            first_name = repost_owner_info.get('first_name', 'Unknown')
            last_name = repost_owner_info.get('last_name', 'Unknown')
            repost_owner_name = f"{first_name} {last_name}"
        else:  # группа
            repost_owner_id = abs(repost_owner_id)
            repost_owner_name = get_group_name(repost_owner_id)

    repost_text = repost_info.get('text', '')

    return repost_owner_name, repost_text
def get_user_info(user_id):
    params = {
        'user_ids': user_id,
        'fields': 'first_name,last_name',
        'v': '5.131'
    }
    response = requests.get('https://api.vk.com/method/users.get', params=params)
    user_info = response.json().get('response', [{}])[0]
    return user_info
def get_group_name(group_id):
    params = {
        'group_id': group_id,
        'fields': 'name',
        'v': '5.131'
    }
    response = requests.get('https://api.vk.com/method/groups.getById', params=params)
    group_info = response.json().get('response', [{}])[0]
    group_name = group_info.get('name')

    if group_name:
        return group_name
def is_grayscale(image):
    return image.mode == 'L'
def is_default_vk_image(image):
    return image.width == 400 and image.height == 400
def get_image_color_palette(image_url):
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))

    # Проверяем, является ли изображение используемым VK для отсутствующих изображений
    if is_default_vk_image(image):
        return None, 'Изображение отсутствует'

    if is_grayscale(image):
        # Return the grayscale image and type
        return image, 'Grayscale'
    else:
        # Return the original color image and type
        return image, 'Color'

class OutputWindow(QWidget):
    def __init__(self,main_window):
        super().__init__()
        #self.initUI()
        self.setWindowTitle("Данные пользователя")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon('D:\Учеба\patent\icon.ico'))
        self.setBackgroundColor(QColor(243, 247, 236))

        self.layout = QVBoxLayout()

        self.name_label = QLabel("Имя: ")
        self.name_label.setStyleSheet(
            "QLabel { font-size: 17px;font-weight: bold; }")
        self.layout.addWidget(self.name_label)

        self.last_name_label = QLabel("Фамилия: ")
        self.last_name_label.setStyleSheet(
            "QLabel { font-size: 17px; font-weight: bold;}")
        self.layout.addWidget(self.last_name_label)


        self.image_label = QLabel()
        self.matching_groups_label = QLabel()

    # Горизонтальная компоновка для текста и изображения
    #     self.text_and_image_layout = QHBoxLayout()
    #     self.text_and_image_layout.addWidget(self.name_label)
    #     self.text_and_image_layout.addWidget(self.last_name_label)
    #     self.text_and_image_layout.addWidget(self.image_label)

        #self.layout.addLayout(self.text_and_image_layout)
        self.layout.addWidget(self.matching_groups_label)
        self.matching_groups_label.setStyleSheet(
        "QLabel { font-size: 16px; }")

        self.info_label = QLabel("Идет сохранение постов в файл...")
        self.layout.addWidget(self.info_label)
        self.info_label.setStyleSheet(
        "QLabel { font-size: 16px; }")

        self.emot_label1 = QLabel("Идет определение эмоций по странице...")
        self.layout.addWidget(self.emot_label1)
        self.emot_label1.setStyleSheet(
        "QLabel { font-size: 16px; }")

        self.words_label = QLabel("")
        self.layout.addWidget(self.words_label)
        self.words_label.setStyleSheet(
        "QLabel { font-size: 16px; }")

        self.max_hour_value = QLabel('')
        self.layout.addWidget(self.max_hour_value)
        self.max_hour_value.setStyleSheet(
        "QLabel { font-size: 16px; }")

        self.insomnia_posts = QLabel('')
        self.layout.addWidget(self.insomnia_posts)
        self.insomnia_posts.setStyleSheet(
        "QLabel { font-size: 16px; }")

        self.justtext = QLabel("Вывод по странице:")
        self.layout.addWidget(self.justtext)
        self.justtext.setStyleSheet(
        "QLabel { font-size: 24px; color: #000000;  }")

    # self.result = QLabel("")
    # self.layout.addWidget(self.result)
    # self.result.setStyleSheet(
    #     "QLabel { font-size: 18px;  }")

        self.analyze = QLabel("")
        self.layout.addWidget(self.analyze)
        self.analyze.setStyleSheet(
        "QLabel { font-size: 18px; }")

        self.back_button = QPushButton("Назад")
        self.back_button.setGeometry(QtCore.QRect(600, 480, 191, 61))
        self.back_button.setObjectName("pushButton")
        self.back_button.setStyleSheet(pushButton_StyleSheet)
    # self.back_button.setStyleSheet(pushButton_StyleSheet)

        self.back_button.clicked.connect(self.close)
        self.back_button.clicked.connect(main_window.show)
        self.layout.addWidget(self.back_button)
        self.setLayout(self.layout)

    def setBackgroundColor(self, color):
        # Создаем палитру и устанавливаем цвет фона
        palette = self.palette()
        palette.setColor(QPalette.Window, color)
        self.setPalette(palette)
    def reset(self):
    # Сброс всех меток на начальные значения
        self.info_label.setText("Идет сохранение постов в файл...")
        self.emot_label1.setText("Идет определение эмоций по странице...")
        self.insomnia_posts.setText("")
        self.words_label.setText("")
    # self.result = QLabel("")
    # self.analyze = QLabel("")


    def set_label_text(self, text):
        self.info_label.setText(text)


    def set_img_label(self, text):
        self.image_label.setText(text)


    def emot_label(self, text):
        self.emot_label.setText(text)


    def set_emot_label_text(self, text):
        self.emot_label1.setText(text)

    def set_analyze(self, text):
        self.analyze.setText(text)
    def set_max_hour_value(self, text):
        self.max_hour_value.setText(text)
    def set_insomnia_posts(self, text):
        self.insomnia_posts.setText(text)
    def set_words_label_text(self, text):
        self.words_label.setText(text)
        self.words_label.setText(text)
    def initUI(self):
        self.setWindowTitle('Output')
        self.setGeometry(200, 200, 400, 300)
        self.name_label = QLabel('Имя: ')
        self.last_name_label = QLabel('Фамилия: ')
        self.matching_groups_label = QLabel(' ')

        layout = QVBoxLayout()
        layout.addWidget(self.name_label)
        layout.addWidget(self.last_name_label)
        layout.addWidget(self.matching_groups_label)
        self.setLayout(layout)

    def display_user_info(self, first_name, last_name, matching_groups_count):
        self.name_label.setText(f"Имя: {first_name}")
        self.last_name_label.setText(f"Фамилия: {last_name}")
        self.matching_groups_label.setText(f"Количество групп, содержащих слова из файла groups.txt: <b>{matching_groups_count}</b>")

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

class SignUpApp(QWidget):
    def __init__(self):
        super().__init__()
        #self.output_window = OutputWindow()
        self.initUI()

    def initUI(self):
        mainLayout = QHBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)  # Remove padding
        mainLayout.setSpacing(0)  # Remove spacing

        leftPanel = QWidget()
        leftPanel.setAutoFillBackground(True)
        palette = leftPanel.palette()
        palette.setColor(QPalette.Window, QColor(131, 180, 255))
        leftPanel.setPalette(palette)

        leftPanelLayout = QVBoxLayout()
        leftPanelLayout.setContentsMargins(0, 0, 0, 0)  # Remove padding
        leftPanelLayout.setSpacing(10)  # Set spacing between widgets

        signUpLabel = QLabel("PsyState")
        signUpLabel.setStyleSheet("font-size: 32px; color: white; paddin-top: 30px;")
        signUpLabel.setFont(QFont('Century Gothic', 32))
        textLabel = QLabel("Приложение для оценки эмоционального состояния ползователя по его странице в ВКонтакте")
        textLabel.setWordWrap(True)
        textLabel.setStyleSheet("font-size: 20px; color: white; padding-top: 50px;")
        textLabel.setFont(QFont('Century Gothic', 20))

        leftPanelLayout.addWidget(signUpLabel)
        leftPanelLayout.addWidget(textLabel)
        leftPanelLayout.addStretch(1)
        leftPanel.setLayout(leftPanelLayout)

        rightPanel = QWidget()
        rightPanel.setAutoFillBackground(True)  # Enable auto-fill background
        rightPanelLayout = QVBoxLayout()
        rightPanelLayout.setAlignment(Qt.AlignCenter)

        # Setting the background color of the right panel
        palette1 = rightPanel.palette()
        palette1.setColor(QPalette.Window, QColor(243, 247, 236))
        rightPanel.setPalette(palette1)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText('Enter ID here...')
        self.input_field.setFont(QFont('Century Gothic', 14))
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 20px; 
                border: none;
                border-radius: 12px;
                background-color: #393E46;
                color: #EEEEEE;
            }
        """)

        submitButton = QPushButton('Submit')
        submitButton.setFont(QFont('Century Gothic', 12))
        submitButton.clicked.connect(self.open_output_window)
        submitButton.setStyleSheet("""
            QPushButton {
                background-color: #83B4FF;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #5A72A0;
            }
        """)

        formLayout = QFormLayout()
        formLayout.addRow(self.input_field)
        formLayout.addRow(submitButton)

        rightPanelLayout.addStretch(1)
        rightPanelLayout.addLayout(formLayout)
        rightPanelLayout.addStretch(1)

        rightPanel.setLayout(rightPanelLayout)

        mainLayout.addWidget(leftPanel)
        mainLayout.addWidget(rightPanel)
        self.setLayout(mainLayout)
        self.setWindowTitle("Sign Up Form")
        self.setGeometry(100, 100, 800, 400)

        self.output_window = OutputWindow(self)
        self.input_field.returnPressed.connect(self.open_output_window)

    def open_output_window(self):
        user_id = self.input_field.text()
        print(f"Submit clicked, user_id: {user_id}")  # Debug output
        user_info = self.fetch_user_info(user_id)
        print(f"Fetched user info: {user_info}")  # Debug output
        if user_info and 'response' in user_info and user_info['response']:
            matching_groups_count = self.fetch_user_groups(user_id)
            self.output_window.display_user_info(
                user_info['response'][0]['first_name'],
                user_info['response'][0]['last_name'],
                matching_groups_count
            )
            Thread(target=self.fetch_user_wall, args=(user_id,)).start()
            self.output_window.reset()  # Сброс состояния окна
            self.output_window.show()
        else:
            print("User info not found.")

    def fetch_user_info(self, user_id):
        print(f"Fetching user info for: {user_id}")  # Debug output
        params = {
            'user_ids': user_id,
            'fields': 'photo_max_orig,first_name,last_name,about,activities,books,career,counters,country,interests,movies,personal,relatives,relation',
            'access_token': access_token,
            'v': '5.131'
        }
        try:
            if not re.match(r'^[a-zA-Z0-9_]+$', user_id):
                self.show_error_message("Некорректно введен id.")
                return None

            response = requests.get('https://api.vk.com/method/users.get', params=params)
            user_info = response.json()
            print('Мы зашли сюда', user_info)

            if 'response' not in user_info or not user_info['response']:
                self.show_error_message("Такой страницы не существует.")
                return None

            user_data = user_info['response'][0]

            if 'deactivated' in user_data:
                self.show_error_message("Страница забанена или удалена")
                return None

            if 'is_closed' in user_data and user_data['is_closed']:
                self.show_error_message("Страница закрыта")
                return None

            self.analyze_user_data(user_data)

            with open('user_info.json', 'w', encoding='utf-8') as f:
                json.dump(user_info, f, ensure_ascii=False, indent=4)

            return user_info  # Убедитесь, что возвращаем данные после всех проверок

        except Exception as e:
            print("Exception occurred while fetching user info:", e)  # Debug output
            return None

    def show_error_message(self, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle('Ошибка')
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(f"<span style='font-size: 24px; color: #333;'>{message}</span>")
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
        msg_box.exec_()

    def analyze_user_data(self, user_data):
        self.ANALYZE = ''
        self.DANGER = 0
        if 'counters' in user_data:
            counters = user_data['counters']
            if 'friends' in counters:
                friends_count = counters['friends']
                if friends_count < 10:
                    self.DANGER += 1
                    self.ANALYZE += 'У пользователя мало друзей, возможно, он асоциальный \n'
                elif friends_count > 1000:
                    self.DANGER += 1
                    self.ANALYZE += 'У пользователя слишком много друзей, возможно, он пытается восполнить и коллекционирует друзей \n'
            if 'photos' in counters:
                photos_count = counters['photos']
                if photos_count == 0:
                    self.DANGER += 1
                    self.ANALYZE += 'У пользователя нет изображений, это показывает, что человек скрытный \n'
        if 'photo_max_orig' in user_data:
            image_url = user_data['photo_max_orig']
            result_image, image_type = get_image_color_palette(image_url)
            if image_type == 'Grayscale':
                img_label = "Изображение ЧБ"
                self.output_window.set_img_label(img_label)
                self.DANGER += 1
                self.ANALYZE += 'ЧБ изображение пользователя показывает депрессивные эпизоды человека \n'
            elif image_type == 'Изображение отсутствует':
                self.DANGER += 1
                self.ANALYZE += 'Отсутствие изображения показывает, что человек скрытный \n'
                img_label = "Изображение отсутствует"
                #self.output_window.set_img_label(img_label)
            elif result_image is None:
                print("Ошибка загрузки изображения")

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
            with open('groups.json', 'w', encoding='utf-8') as f:
                json.dump(group_names, f, ensure_ascii=False, indent=4)


            # Загрузка списка слов из файла groups.txt
            with open('groups.txt', 'r', encoding='utf-8') as file:
                groups_word_list = [line.strip() for line in file]

            # Сравнение групп пользователя с словами из groups.txt
            matching_groups_count = sum(
                1 for group_name in group_names if any(word in group_name for word in groups_word_list))

            if matching_groups_count >0:
                self.DANGER+=1
                self.ANALYZE += 'У человека есть подписки на провакационные группы \n'
                #print('группа', self.DANGER)

            return matching_groups_count

        except Exception as e:
            #print("Error fetching user groups:", e)
            return 0

    def fetch_user_wall(self, user_id):
        # global DANGER
        # global ANALYZE
        # Получение всех постов пользователя
        all_posts = get_posts(user_id, access_token)
        user_posts = []
        repost_posts = []
        for post in all_posts:
            if 'copy_history' in post:
                repost_owner_name, repost_text = get_post_info(post)
                if repost_owner_name != "Unknown Unknown" and repost_text != "Запись удалена":
                    repost_posts.append({'repost_owner_name': repost_owner_name, 'repost_text': repost_text})
            else:
                post_text = post.get('text', '')
                if post_text:
                    user_posts.append(post_text)

        # Сохранение текстов постов пользователя
        with open('user_posts.json', 'w', encoding='utf-8') as f:
            json.dump(user_posts, f, ensure_ascii=False, indent=4)
        clean_json('user_posts.json')
        remove_newlines_from_posts('user_posts.json')

        with open('user_posts.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        # Сохранение репостов пользователя
        with open('repost_posts.json', 'w', encoding='utf-8') as f:
            json.dump(repost_posts, f, ensure_ascii=False, indent=4)
        self.output_window.set_label_text("Все текста постов успешно записаны в файл 'user_posts.json'.")
        print("Все текста постов успешно записаны в файл 'user_posts.json'.")

        #проводим анализ
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
        total_posts = len(data2)
        model = HuggingFaceModel.Text.Bert_Tiny
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        tr = TextRecognizer(model=model, device=device)

        for line in data2:
            result = tr.recognize(line, return_single_label=False)

            # Получение вероятностей для каждой эмоции
            emotions_probabilities = {emotion: result[emotion] for emotion in result}

            # Нахождение наиболее вероятной эмоции
            top_emotion = max(emotions_probabilities, key=emotions_probabilities.get)

            # Обновление счетчика для наиболее вероятной эмоции
            if top_emotion in emotion_counts:
                emotion_counts[top_emotion] += 1
            else:
                emotion_counts[top_emotion] = 1

        top_emotions = heapq.nlargest(3, emotion_counts, key=emotion_counts.get)
        emot_label_text = ""
        for i, emotion in enumerate(top_emotions, 1):
            emot_label_text += f"Топ-{i} эмоция: {emotion}, количество вхождений: <b>{emotion_counts[emotion]}</b>\n"

        self.output_window.set_emot_label_text(emot_label_text)

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
        #print("Активность пользователя по часам:")
        # for hour, count in sorted(posts_activity.items()):
        #     print(f"В {hour} часов (местное время): {count} постов")
        max_hour, max_count = posts_activity.most_common(1)[0]
        #print(f"Чаще всего посты появляются в {max_hour} часов: {max_count} постов")
        self.output_window.set_max_hour_value(f"Чаще всего посты появляются в {max_hour} часов: {max_count} постов")

            # Проверяем наличие постов между 3 и 5 утра. бессоница
        insomnia_posts = [(hour, count) for hour, count in posts_activity.items() if 3 <= hour <= 5]
        if insomnia_posts:
            total_insomnia_posts = sum(count for hour, count in insomnia_posts)
            self.DANGER+=1
            #print(f"У человека существует риск бессоницы, так как количество постов между 3 и 5 утра: {total_insomnia_posts}")
            self.ANALYZE += 'У человека существует риск бессоницы, так как количество постов между 3 и 5 утра'
            self.output_window.set_insomnia_posts(f"У человека существует риск бессоницы, так как количество постов между 3 и 5 утра: {total_insomnia_posts}")
        #Общий вывод по странице
        #self.output_window.set_result(f'Страница опасна на {self.DANGER} по 5-балльной шкале')
        self.output_window.set_analyze(self.ANALYZE)
        #print(self.ANALYZE)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    font = QFont()
    font.setFamily("Century Gothic")
    app.setFont(font)
    ex = SignUpApp()
    ex.show()
    sys.exit(app.exec_())
