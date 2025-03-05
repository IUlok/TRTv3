import requests
import json
import yaml
import time
import os
import sys

from pathlib import Path
from datetime import datetime, timedelta
from numpy.random import normal
from collections import defaultdict

if __name__ == "__main__":
    print("Добро пожаловать в TRT v3 - (Town Raiding Tool 3). Авторы: Uberietzsche & Ulok & CrazyCat. \nЭта утилита ищет города, которые упадут в скором времени.\n"
          "Это также даст вам дополнительную информацию о городах: \n\n"
          "  1. Название города и ник владельца, координаты на карте; \n"
          "  2. Количество золота у мэра и в банке города; \n"
          "  3. Дату регистрации мэра и дата создания города; \n"
          "  4. Размер города в чанках; \n"
          "  5. Уведомление о том, открыт город или нет. \n"
          "\nКод работает от 10 до 20 минут. Иди налей чаю я не знаю блин...\n")
    print("\n ===[ ШАГ (0/2). ПРЕДЫДУЩАЯ ФАЙЛ С ГОРОДАМИ БУДЕТ ОЧИЩЕН! НАЖМИТЕ ЛЮБУЮ КНОПКУ ДЛЯ ЗАПУСКА СКРИПТА. ]=== \n")
    input("")

    server_api_towns = 'https://api.earthmc.net/v3/aurora/towns'
    main_info = 'https://api.earthmc.net/v3/aurora/'
    server_api_residents = 'https://api.earthmc.net/v3/aurora/players'
    fill_char='█'
    empty_char='-'
    elapsed_time = 0
    time_of_new_day = timedelta(hours=13)
    minimal_town_size = 5
    maximal_town_size: 940
    time_to_ruin = 42
    day_amount = 10
    sleep_time: 0.35
    number_of_get_retries = 10
    min_size_for_sort = 25
    opt_size_for_sort = 75
    towns = []
    town_list = []
    counter = 0

    progress_bar = requests.get(main_info)
    num_towns = progress_bar.json()
    numTowns = num_towns["stats"]["numTowns"]

    print("\n ===[ ШАГ (1/2). ПАРСИНГ ДАННЫХ О ГОРОДАХ. ПОЖАЛУЙСТА, ПОДОЖДИТЕ]=== \n")
    towns_header = requests.get(server_api_towns)
    townlist = towns_header.json()
    print("Получение списка всех городов...")

    def request_towns(town_list):
        while(1):
            try:
                response = requests.post(server_api_towns, json = {"query": town_list})
                towns.extend(response.json())
                break
            except Exception as E1: print("Кумтиокс сосал кста")

    for town in townlist:
        percent = int(elapsed_time / numTowns * 100)
        filled_width = int(percent / 100 * 100)
        bar = fill_char * filled_width + empty_char * (100 - filled_width)
        print(f"\r|{bar}| {percent}%", end="")
        elapsed_time += 1

        town_list.append(town["name"])
        counter += 1
        if counter == 50:
            counter = 0
            request_towns(town_list)
            town_list = []

    request_towns(town_list)

    def sort_key(town):
        if town['stats']['numTownBlocks'] < min_size_for_sort:
            return 940 + min_size_for_sort - town['stats']['numTownBlocks']
        else:
            return abs(opt_size_for_sort - town['stats']['numTownBlocks'])

    towns.sort(key = sort_key)

    print("\n ===[ПАРСИНГ ОКОНЧЕН. ШАГ (2/2). ОБРАБОТКА ФАЙЛА. ПОЖАЛУЙСТА, ПОДОЖДИТЕ. ]===")

    ruined_towns = []
    falling_towns = defaultdict(list)

    get_tries = 0
    get_number = 0
    towns_falling_number = 0
    towns_stand_number = 0
    towns_not_interesting_number = 0
    already_ruined_number = 0
    elapsed_time = 0

    for town in towns:
        percent = int(elapsed_time / numTowns * 100)
        filled_width = int(percent / 100 * 100)
        bar = fill_char * filled_width + empty_char * (100 - filled_width)
        print(f"\r|{bar}| {percent}%", end="")
        elapsed_time += 1

        get_tries += 1
        get_retries = 0
        if (town["perms"]["flags"]['pvp'] == "true") and (str(town['mayor']['name']).startswith('NPC')):
            get_number += 1
            already_ruined_number += 1
            ruined_towns.append(town)
            continue
        if (town['stats']['numTownBlocks'] < minimal_town_size):
            get_number += 1
            towns_not_interesting_number += 1
            continue

        while(1):
            try:
                mayor_name = town['mayor']['name']
                mayor_resp = requests.post(server_api_residents, json = {"query": [mayor_name]})
                if mayor_resp.content == b'Invalid API route :(':
                    print(f"{town['mayor']['name']} больше не мэр {town['name']}")
                    break

                mayor = mayor_resp.json()

                dt_object = datetime.fromtimestamp(mayor[0]['timestamps']['lastOnline'] // 1000)
                dt_object += timedelta(days=time_to_ruin)
                town['mayorMoney'] = mayor[0]['stats']['balance']
                town['mayorLastOnline'] = mayor[0]['timestamps']['lastOnline']
                town['mayorRegistred'] = mayor[0]['timestamps']['registered']
                if dt_object >= dt_object.replace(hour=0, minute=0, second=0, microsecond=0) + time_of_new_day:
                    maximal_dt_town_falls = dt_object.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                else:
                    maximal_dt_town_falls = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)
                if (maximal_dt_town_falls > (datetime.now() + timedelta(days=day_amount))):
                    get_number += 1
                    towns_stand_number += 1
                    break
                if (len(town["residents"]) == 1):
                    get_number += 1
                    falling_towns[int(round(maximal_dt_town_falls.timestamp()))].append(town)
                    towns_falling_number += 1
                    break
                if (len(town["residents"]) != 1):
                    for resident_name in town['residents']:
                        if resident_name["name"] == town['mayor']['name']:
                            continue
                        while(1):
                            try:
                                hier_resp = requests.post(server_api_residents, json = {"query": [resident_name['name']]})
                                if hier_resp.content == b'Invalid API route :(':
                                    print(f"{resident_name['name']} больше не житель города {town['name']}")
                                    break
                                hier = hier_resp.json()
                                dt_object = datetime.fromtimestamp(hier[0]['timestamps']['lastOnline'] // 1000)
                                dt_object += timedelta(days=time_to_ruin)
                                if dt_object >= dt_object.replace(hour=0, minute=0, second=0, microsecond=0) + time_of_new_day:
                                    current_dt_town_falls = dt_object.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                                else:
                                    current_dt_town_falls = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)
                                maximal_dt_town_falls = max(maximal_dt_town_falls, current_dt_town_falls)
                                break
                            except Exception as E:
                                print(E, "=> данные о мэре не получены (повторная попытка...)")
                        if (maximal_dt_town_falls > (datetime.now() + timedelta(days=day_amount))):
                            towns_stand_number += 1
                            break
                    if (maximal_dt_town_falls <= (datetime.now() + timedelta(days=day_amount))):
                        falling_towns[int(round(maximal_dt_town_falls.timestamp()))].append(town)
                        towns_falling_number += 1
                    break
                break

            except Exception as E2:
                get_retries += 1
                if get_retries == number_of_get_retries:
                    print("\nКумтиокс сосал кста")
                    break

    print(f"\n ===[ ЗАВЕРШЕНО! ЛИСТ ГОРОДОВ БУДЕТ ЗАПИСАН В ФАЙЛ]=== \n")
    fall_tsmps = list(falling_towns.keys())
    fall_tsmps.sort()
    falling_towns = {t: falling_towns[t] for t in fall_tsmps}

    with open("TOWNS", 'w') as f:
        def printl(s, l=21):
            print(s, " " * (l - len(str(s))), end="")
            f.write(str(s) + " " * (l - len(str(s))))

        for tsmp, towns_per_day in falling_towns.items():
            if (int(tsmp) <= 3618000):
                continue

            print("\n\nДЕНЬ ПАДЕНИЯ:", datetime.fromtimestamp(int(tsmp)))
            f.write("\n\nДЕНЬ ПАДЕНИЯ: " + str(datetime.fromtimestamp(int(tsmp))) + "\n")
            printl("НАЗВАНИЕ")
            printl("МЭР")
            printl("ДАТА СОЗДАНИЯ")
            printl("ДАТА РЕГИСТРАЦИИ МЭРА")
            printl("ТЕРРИТРИЯ", l=5)
            printl("ISOPEN ", l=7)
            printl("TOWN $", l=7)
            printl("MAYOR $", l=8)
            print("")
            f.write("\n")
            towns_per_day.sort(key = lambda t: t["timestamps"]["registered"])
            for town in towns_per_day:
                try:
                    printl(town['name'])
                    printl(town['mayor']['name'])
                    printl(datetime.fromtimestamp(town["timestamps"]["registered"] // 1000))
                    printl(datetime.fromtimestamp(town["mayorRegistred"] // 1000))
                    printl(town['stats']['numTownBlocks'], l=5)
                    if town["status"]["isOpen"]:
                        printl("YES", l=7)
                    else:
                        printl("---", l=7)
                    printl(town['stats']["balance"], l=7)
                    printl(town["mayorMoney"], l=8)
                    printl("&x=" + str(round(town["spawn"]["x"])) + "&z=" + str(round(town["spawn"]["z"])))
                    print("")
                    f.write("\n")
                except Exception as E:
                    pass

    print("\n ===[ ТЕПЕРЬ ОКНО МОЖНО ЗАКРЫТЬ. ]===")
    while(1):
        input("")
