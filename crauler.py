#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
КРАУЛЕР ДЛЯ ПОИСКА В ПРОЕКТАХ GITLAB
Версия: 1.0 (ОПТИМАЛЬНЫЙ ГИБРИДНЫЙ ПОИСК)
================================================================================

ОПИСАНИЕ:
    Скрипт для поиска любых строк/терминов во всех текстовых файлах проектов GitLab.
    Использует гибридный подход: быстрый API Search для кода + глубокий поиск для конфигов.
    Результаты выводятся в формате, удобном для копирования в YouTrack и другие системы.

ОСОБЕННОСТИ ВЕРСИИ 1.0:
    - Гибридный подход: API Search (быстро) + Deep Search (точно)
    - Для кода (.py, .js, .go) → быстрый API Search
    - Для конфигов (.yml, .yaml, .json, .env) → глубокий поиск
    - Параллельная обработка проектов (до 3 одновременно)
    - Вывод в формате, удобном для копирования в YouTrack
    - Полный вывод всех найденных вхождений (без сокращений)
    - Детальные отчеты с прямыми ссылками на GitLab
    - Регистронезависимый поиск

ЛОГИКА РАБОТЫ:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ 1. Получает список всех проектов в группе (включая подгруппы)          │
    │ 2. Фильтрует архивированные и удаленные проекты                        │
    │ 3. Для каждого активного проекта:                                      │
    │    a) API Search для терминов в кодовых файлах (быстро, 1-3 сек)       │
    │    b) Глубокий поиск в конфигах (.yml, .yaml, .json, .env)            │
    │    c) Объединяет результаты из обоих источников                        │
    │ 4. Формирует детальный и суммарный отчеты                              │
    └─────────────────────────────────────────────────────────────────────────┘

ПОЧЕМУ ГИБРИДНЫЙ ПОДХОД:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Тип файлов           │ Метод          │ Скорость │ Точность │
    ├──────────────────────┼────────────────┼──────────┼──────────┤
    │ Код (.py, .js, .go)  │ API Search     │ ⚡ очень  │ ✓ высокая│
    │ Конфиги (.yml, .yaml)│ Deep Search    │ 🐢 средн. │ ✓✓ 100%  │
    │ Документация (.md)   │ API Search     │ ⚡ очень  │ ✓ высокая│
    │ Скрипты (.sh)        │ API Search     │ ⚡ очень  │ ✓ высокая│
    └─────────────────────────────────────────────────────────────────────────┘

КОГДА ИСПОЛЬЗОВАТЬ:
    ✓ Поиск API ручек в коде и конфигах
    ✓ Поиск названий БД (PostgreSQL, Redis, MySQL)
    ✓ Поиск URL и эндпоинтов
    ✓ Поиск переменных окружения
    ✓ Поиск библиотек и зависимостей
    ✓ Поиск любых текстовых строк в проектах

================================================================================
ИНСТРУКЦИЯ ПО НАСТРОЙКЕ
================================================================================

1. НАСТРОЙКА ПОИСКОВЫХ ТЕРМИНОВ
--------------------------------------------------------------------------------
   SEARCH_TERMS = []  # список слов/фраз для поиска

   ПРИМЕРЫ:

   # Поиск API ручек
   SEARCH_TERMS = [
       'example1',
       'example2',
       'example3'
   ]

2. НАСТРОЙКА ПОДКЛЮЧЕНИЯ К GITLAB
--------------------------------------------------------------------------------
   PRIVATE_TOKEN = ''     # Ваш персональный токен GitLab
   GITLAB_URL = 'https://gitlab.example.ru'  # URL GitLab сервера
   GROUP_ID = 0               # ID группы для поиска

   КАК ПОЛУЧИТЬ ТОКЕН:
     1. Зайдите в GitLab
     2. Нажмите на аватар → Settings → Access Tokens
     3. Создайте токен с правами read_api и read_repository
     4. Скопируйте токен и вставьте вместо ''

3. НАСТРОЙКА ПАРАМЕТРОВ СКАНИРОВАНИЯ
--------------------------------------------------------------------------------
   MAX_WORKERS = 3                # Количество параллельных проектов
                                  # (можно увеличить до 5-10)
   
   MAX_FILES_DEEP_SEARCH = 2000   # Максимум конфигов на проект для глубокого поиска
   PROJECT_TIMEOUT = 60           # Таймаут на проект в секундах

4. ФАЙЛЫ РЕЗУЛЬТАТОВ
--------------------------------------------------------------------------------
   hybrid_search_results.txt      - Детальные результаты по каждому проекту
   hybrid_search_summary.txt      - Суммарный отчет по терминам
   hybrid_search_errors.txt       - Проекты с ошибками

================================================================================
ФОРМАТ ВЫВОДА (ДЛЯ КОПИРОВАНИЯ В YOUTRACK)
================================================================================

Детальный отчет (hybrid_search_results.txt):

   🔴 ПРОЕКТ: project1
      Путь: /project1/

     📍 'example1': 1 вхождений
         - deploy/all/base-values.yml:14 [Deep]
           Строка 14: example1: '{{ .Helm.Release.Cluster }}'
           Ссылка: https://gitlab.example.ru/

 

Суммарный отчет (hybrid_search_summary.txt):

   📍 'example1':
      Проекты (3):
         - project1 (ID: ) - 1 вхождений
         - project2 (ID: ) - 2 вхождений
         - project3 (ID: ) - 2 вхождений

================================================================================
"""

# ==============================================================================
# НАСТРОЙКА ПОИСКА - ЗАМЕНИТЕ НА НУЖНЫЕ ВАМ СЛОВА
# ==============================================================================

SEARCH_TERMS = [
    'example1',
    'example2',
    'example3'
]

# ==============================================================================
# НАСТРОЙКА ПОДКЛЮЧЕНИЯ К GITLAB
# ==============================================================================

PRIVATE_TOKEN = ''                     # Ваш персональный токен
GITLAB_URL = 'https://gitlab.example.ru'  # URL GitLab сервера
GROUP_ID = 0               # ID группы для поиска

# ==============================================================================
# НАСТРОЙКА ПАРАМЕТРОВ СКАНИРОВАНИЯ
# ==============================================================================

MAX_WORKERS = 3                      # Параллельных проектов (3-5 оптимально)
MAX_FILES_DEEP_SEARCH = 2000         # Максимум конфигов на проект для глубокого поиска
PROJECT_TIMEOUT = 60                 # Таймаут на проект в секундах
CASE_SENSITIVE = False               # Чувствительность к регистру (False = ищем везде)

# ==============================================================================
# НАСТРОЙКА РАСШИРЕНИЙ ФАЙЛОВ
# ==============================================================================

# Файлы кода (используем API Search)
CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.kt', '.groovy',
    '.go', '.rs', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb',
    '.swift', '.m', '.mm', '.scala', '.sh', '.bash', '.zsh', '.ps1',
    '.md', '.txt', '.rst', '.adoc', '.html', '.htm', '.css', '.scss',
    '.vue', '.svelte', '.tf', '.gitlab-ci.yml', '.dockerfile'
}

# Конфиги (используем Deep Search - так как API может пропустить)
CONFIG_EXTENSIONS = {
    '.yml', '.yaml', '.json', '.xml', '.toml', '.ini', '.cfg',
    '.conf', '.config', '.properties', '.env', '.hcl', '.tfvars'
}

# Бинарные файлы (пропускаем)
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp',
    '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z', '.exe', '.dll',
    '.so', '.pyc', '.pyo', '.class', '.jar', '.war', '.min.js', '.min.css',
    '.ttf', '.woff', '.woff2', '.eot', '.mp3', '.mp4', '.avi', '.mov'
}

# ==============================================================================
# ФАЙЛЫ РЕЗУЛЬТАТОВ
# ==============================================================================

RESULT_FILE = 'hybrid_search_results.txt'
SUMMARY_FILE = 'hybrid_search_summary.txt'
ERRORS_FILE = 'hybrid_search_errors.txt'

# ==============================================================================
# КОД СКРИПТА (НЕ МЕНЯТЬ)
# ==============================================================================

import gitlab
import logging
import os
import time
from typing import Dict, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def api_search(gl, project_id: int, search_terms: List[str]) -> Dict[str, List[dict]]:
    """Быстрый поиск через GitLab API Search (для кода)"""
    results = {term: [] for term in search_terms}
    
    for term in search_terms:
        try:
            blobs = gl.search('blobs', term, project_id=project_id)
            for blob in blobs:
                file_path = blob.get('path', '')
                file_ext = os.path.splitext(file_path)[1].lower()
                
                # Проверяем, что это файл кода, а не конфиг
                if file_ext in CODE_EXTENSIONS or file_ext == '':
                    results[term].append({
                        'path': file_path,
                        'filename': blob.get('basename', ''),
                        'url': blob.get('web_url', '#'),
                        'term': term,
                        'found_by': 'API'
                    })
        except Exception as e:
            logging.debug(f"API search error for '{term}': {e}")
    
    return results


def deep_search_configs(gl, project_id: int, search_terms: List[str]) -> Dict[str, List[dict]]:
    """Глубокий поиск в конфигах (.yml, .yaml, .json, .env)"""
    results = {term: [] for term in search_terms}
    
    try:
        project = gl.projects.get(project_id)
        
        # Проверяем ветку
        try:
            project.branches.get('master')
        except:
            return results
        
        # Получаем все файлы
        all_files = []
        page = 1
        while page <= 20:  # до 2000 файлов
            try:
                files = project.repository_tree(
                    recursive=True, 
                    ref='master', 
                    per_page=100, 
                    page=page
                )
                if not files:
                    break
                all_files.extend(files)
                page += 1
            except:
                break
        
        files_scanned = 0
        
        for file in all_files:
            if file['type'] != 'blob':
                continue
            
            file_ext = os.path.splitext(file['name'])[1].lower()
            
            # Сканируем только конфиги
            if file_ext not in CONFIG_EXTENSIONS:
                continue
            
            files_scanned += 1
            if files_scanned > MAX_FILES_DEEP_SEARCH:
                break
            
            try:
                content = project.files.get(file_path=file['path'], ref='master').decode()
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
                
                # Ищем каждый термин
                for term in search_terms:
                    # Проверяем вхождение
                    search_content = content.lower() if not CASE_SENSITIVE else content
                    search_term = term.lower() if not CASE_SENSITIVE else term
                    
                    if search_term in search_content:
                        # Находим строку с совпадением
                        lines = content.splitlines()
                        line_num = None
                        line_content = ""
                        for i, line in enumerate(lines, 1):
                            check_line = line.lower() if not CASE_SENSITIVE else line
                            if search_term in check_line:
                                line_num = i
                                line_content = line.strip()[:200]
                                break
                        
                        results[term].append({
                            'path': file['path'],
                            'filename': file['name'],
                            'line': line_num,
                            'line_content': line_content,
                            'url': f"{GITLAB_URL}/{project.path_with_namespace}/-/blob/master/{file['path']}#L{line_num}" if line_num else "#",
                            'term': term,
                            'found_by': 'Deep'
                        })
                        
            except Exception:
                continue
                
    except Exception as e:
        logging.debug(f"Ошибка глубокого поиска для {project_id}: {e}")
    
    return results


def process_one_project(gl, project) -> dict:
    """Обработка одного проекта гибридным методом"""
    start_time = time.time()
    
    try:
        # Пропускаем архивированные
        if project.archived:
            return {
                'status': 'archived',
                'name': project.name,
                'id': project.id,
                'time': time.time() - start_time
            }
        
        # Пропускаем удаленные
        if 'deleted' in project.name.lower():
            return {
                'status': 'deleted',
                'name': project.name,
                'id': project.id,
                'time': time.time() - start_time
            }
        
        # Получаем полный объект проекта
        try:
            full_project = gl.projects.get(project.id)
        except:
            return {
                'status': 'error',
                'name': project.name,
                'id': project.id,
                'error': 'Не удалось получить проект',
                'time': time.time() - start_time
            }
        
        # Проверяем ветку master
        try:
            full_project.branches.get('master')
        except:
            return {
                'status': 'no_branch',
                'name': project.name,
                'id': project.id,
                'time': time.time() - start_time
            }
        
        # ШАГ 1: API Search (для кода)
        api_results = api_search(gl, project.id, SEARCH_TERMS)
        
        # ШАГ 2: Deep Search (для конфигов)
        deep_results = deep_search_configs(gl, project.id, SEARCH_TERMS)
        
        # Объединяем результаты
        all_results = {}
        api_found_count = 0
        deep_found_count = 0
        
        for term in SEARCH_TERMS:
            combined = []
            if api_results.get(term):
                combined.extend(api_results[term])
                api_found_count += len(api_results[term])
            if deep_results.get(term):
                combined.extend(deep_results[term])
                deep_found_count += len(deep_results[term])
            all_results[term] = combined
        
        # Проверяем наличие совпадений
        found_terms = {term: matches for term, matches in all_results.items() if matches}
        
        return {
            'status': 'found' if found_terms else 'ok',
            'name': project.name,
            'id': project.id,
            'path': full_project.path_with_namespace,
            'results': all_results,
            'api_found_count': api_found_count,
            'deep_found_count': deep_found_count,
            'time': time.time() - start_time
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'name': project.name,
            'id': project.id,
            'error': str(e)[:200],
            'time': time.time() - start_time
        }


def save_results(results_list: List[dict]):
    """Сохраняет результаты поиска в удобном для копирования формате"""
    
    # Детальный отчет
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("РЕЗУЛЬТАТЫ ГИБРИДНОГО ПОИСКА (версия 3.0)\n")
        f.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n")
        f.write(f"\nИскомые термины ({len(SEARCH_TERMS)} шт.):\n")
        for term in SEARCH_TERMS:
            f.write(f"  - {term}\n")
        f.write("\n")
        
        found_projects = [r for r in results_list if r['status'] == 'found']
        
        if not found_projects:
            f.write("\n СОВПАДЕНИЙ НЕ НАЙДЕНО\n")
        
        for r in found_projects:
            # Упрощенный вывод: только имя проекта и путь
            f.write(f"\n ПРОЕКТ: {r['name']}\n")
            f.write(f"   Путь: {r['path']}\n")
            f.write("\n")
            
            for term, matches in r['results'].items():
                if matches:
                    f.write(f"    '{term}': {len(matches)} вхождений\n")
                    # Показываем ВСЕ вхождения (без ограничений)
                    for match in matches:
                        method = match.get('found_by', 'Unknown')
                        if 'line' in match and match.get('line'):
                            f.write(f"      - {match['path']}:{match['line']} [{method}]\n")
                            if match.get('line_content'):
                                f.write(f"        Строка {match['line']}: {match['line_content']}\n")
                            f.write(f"        {match['url']}\n")
                        else:
                            f.write(f"      - {match['path']} [{method}]\n")
                            f.write(f"        {match['url']}\n")
                    f.write("\n")
    
    # Суммарный отчет
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("СУММАРНЫЙ ОТЧЕТ ГИБРИДНОГО ПОИСКА (версия 3.0)\n")
        f.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")
        
        found_projects = [r for r in results_list if r['status'] == 'found']
        
        f.write(f" ОБЩАЯ СТАТИСТИКА:\n")
        f.write(f"   Найдено проектов с совпадениями: {len(found_projects)}\n")
        f.write(f"   Всего искомых терминов: {len(SEARCH_TERMS)}\n\n")
        
        # Группируем по терминам
        by_term = {}
        for r in found_projects:
            for term, matches in r['results'].items():
                if matches:
                    if term not in by_term:
                        by_term[term] = []
                    by_term[term].append({
                        'project': r['name'],
                        'id': r['id'],
                        'path': r['path'],
                        'count': len(matches),
                        'api_count': sum(1 for m in matches if m.get('found_by') == 'API'),
                        'deep_count': sum(1 for m in matches if m.get('found_by') == 'Deep')
                    })
        
        f.write(" СТАТИСТИКА ПО ТЕРМИНАМ:\n")
        f.write("-"*80 + "\n")
        
        for term in SEARCH_TERMS:
            if term in by_term:
                total_occurrences = sum(p['count'] for p in by_term[term])
                total_api = sum(p['api_count'] for p in by_term[term])
                total_deep = sum(p['deep_count'] for p in by_term[term])
                f.write(f"\n '{term}':\n")
                f.write(f"   Всего вхождений: {total_occurrences} (API: {total_api}, Deep: {total_deep})\n")
                f.write(f"   Проекты ({len(by_term[term])}):\n")
                for p in sorted(by_term[term], key=lambda x: x['count'], reverse=True):
                    f.write(f"      - {p['project']} (ID: {p['id']}) - {p['count']} вхождений\n")
            else:
                f.write(f"\n '{term}':  НЕ НАЙДЕН\n")
    
    # Файл с ошибками
    error_projects = [r for r in results_list if r['status'] == 'error']
    if error_projects:
        with open(ERRORS_FILE, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("ПРОЕКТЫ С ОШИБКАМИ\n")
            f.write("="*80 + "\n\n")
            for r in error_projects:
                f.write(f"❌ {r['name']} (ID: {r['id']})\n")
                f.write(f"   Ошибка: {r.get('error', 'Неизвестная ошибка')}\n")
                f.write(f"   Время: {r['time']:.2f} сек\n\n")


def main():
    """Основная функция"""
    gl = gitlab.Gitlab(GITLAB_URL, private_token=PRIVATE_TOKEN)
    
    logging.info("="*80)
    logging.info("КРАУЛЕР ДЛЯ ПОИСКА В ПРОЕКТАХ GITLAB (версия 3.0 - оптимальный гибрид)")
    logging.info("="*80)
    logging.info(f"Режим: API Search (код) + Deep Search (конфиги)")
    logging.info(f"Параллельных потоков: {MAX_WORKERS}")
    logging.info(f"Искомых терминов: {len(SEARCH_TERMS)}")
    logging.info(f"Регистр: {'чувствительный' if CASE_SENSITIVE else 'нечувствительный'}")
    logging.info("="*80)
    
    # Получаем все проекты
    group = gl.groups.get(GROUP_ID)
    all_projects = group.projects.list(include_subgroups=True, all=True)
    
    # Фильтруем активные
    active_projects = []
    archived_count = 0
    deleted_count = 0
    
    for p in all_projects:
        if p.archived:
            archived_count += 1
        elif 'deleted' in p.name.lower():
            deleted_count += 1
        else:
            active_projects.append(p)
    
    logging.info(f"Всего проектов: {len(all_projects)}")
    logging.info(f"  - Активных: {len(active_projects)} (будут проверены)")
    logging.info(f"  - Архивированных: {archived_count} (пропущены)")
    logging.info(f"  - Удаленных: {deleted_count} (пропущены)")
    logging.info("="*80)
    
    results_list = []
    
    # Параллельная обработка
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_one_project, gl, p): p for p in active_projects}
        
        for idx, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results_list.append(result)
            
            # Вывод в консоль
            if result['status'] == 'found':
                logging.info(f"[{idx}/{len(active_projects)}] 🔴 {result['name']} - НАЙДЕНО! (API: {result['api_found_count']}, Deep: {result['deep_found_count']}) [{result['time']:.1f}с]")
            elif result['status'] == 'ok':
                logging.info(f"[{idx}/{len(active_projects)}] ✅ {result['name']} - OK [{result['time']:.1f}с]")
            elif result['status'] == 'archived':
                logging.info(f"[{idx}/{len(active_projects)}] 📦 {result['name']} - архивирован")
            elif result['status'] == 'deleted':
                logging.info(f"[{idx}/{len(active_projects)}] 🗑️ {result['name']} - удален")
            elif result['status'] == 'no_branch':
                logging.info(f"[{idx}/{len(active_projects)}] 🔀 {result['name']} - нет ветки master")
            elif result['status'] == 'error':
                logging.error(f"[{idx}/{len(active_projects)}] ❌ {result['name']} - Ошибка: {result.get('error', 'Unknown')[:50]}")
    
    # Сохраняем результаты
    save_results(results_list)
    
    # Итоговая статистика
    found_count = len([r for r in results_list if r['status'] == 'found'])
    error_count = len([r for r in results_list if r['status'] == 'error'])
    ok_count = len([r for r in results_list if r['status'] == 'ok'])
    
    logging.info("="*80)
    logging.info(f" ПОИСК ЗАВЕРШЕН!")
    logging.info(f"   Проверено проектов: {len(active_projects)}")
    logging.info(f"   Найдено проектов с совпадениями: {found_count}")
    logging.info(f"   Проектов без совпадений: {ok_count}")
    logging.info(f"   Ошибок: {error_count}")
    logging.info(f"\n Детальный отчет: {RESULT_FILE}")
    logging.info(f" Суммарный отчет: {SUMMARY_FILE}")
    if error_count > 0:
        logging.info(f"⚠️  Ошибки: {ERRORS_FILE}")
    logging.info("="*80)
    
    if found_count > 0:
        logging.warning(f"\n⚠️ ВНИМАНИЕ! Найдено {found_count} проектов с искомыми терминами!")
        logging.warning("Проверьте детальный отчет для получения списка проектов.")


if __name__ == '__main__':
    main()
