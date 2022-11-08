import pyautogui as pgui
import PySimpleGUI as sg
import numpy as np
import os, sys, re
from tkinter import filedialog
import time
import keyboard
import threading
import math
import codecs
import json
import webbrowser, urllib, requests
from bs4 import BeautifulSoup
import glob
from pathlib import Path
from zipmanager import ZipManager
from extract import Extractor
import rarfile

class UserSettings:
    def __init__(self, savefile='settings.json'):
        self.savefile = savefile
        self.params   = self.load_settings()
    def get_default_settings(self):
        ret = {
        'lx':0,'ly':0
        ,'dir_bms':'' # BMS置き場
        ,'dir_dl':'' # ブラウザのDownloadフォルダ
        }
        return ret
    def load_settings(self):
        default_val = self.get_default_settings()
        ret = {}
        try:
            with open(self.savefile) as f:
                ret = json.load(f)
                print(f"設定をロードしました。\n")
        except Exception:
            print(f"有効な設定ファイルなし。デフォルト値を使います。")

        ### 後から追加した値がない場合にもここでケア
        for k in default_val.keys():
            if not k in ret.keys():
                print(f"{k}が設定ファイル内に存在しません。デフォルト値({default_val[k]}を登録します。)")
                ret[k] = default_val[k]

        return ret

    def save_settings(self):
        with open(self.savefile, 'w') as f:
            json.dump(self.params, f, indent=2)

class GUIManager:
    def __init__(self, savefile='settings.json'):
        self.settings = UserSettings(savefile)
        sg.theme('DarkAmber')
        self.FONT = ('Meiryo',12)
        self.window = False

    # icon用
    def ico_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def check_url(self, url):
        flag = True
        try:
            f = urllib.request.urlopen(url)
            #print('OK:', url)
            f.close()
        except urllib.request.HTTPError:
            #print('Not found:', url)
            flag = False

        return flag

    def read_table_json(self, url):
        ret = False
        if self.check_url(url):
            tmp = urllib.request.urlopen(url).read()
            ret = json.loads(tmp)
        return ret

    # 1曲分のjsonデータを受け取ってdownload
    def get_onesong(self, js):
        #print(js)
        print(f"{self.symbol}{js['level']} {js['sha256']}")
        print(js['title'], js['artist'])
        if js['url']:
            print(js['url'], end='')
        if js['url_diff']:
            print(f"\njs['url_diff']")
        else:
            print(f" (同梱譜面)")

    def gui_setting(self):
        self.mode = 'setting'
        self.window.close()
        layout = [
            [sg.Text('ブラウザのファイル保存先', font=self.FONT), sg.Button('変更', font=self.FONT, key='btn_select_dl')],
            [sg.Text('', key='dir_dl', font=self.FONT)],
            [sg.Text('BMSデータ保存先', font=self.FONT), sg.Button('変更', font=self.FONT, key='btn_select_bms')],
            [sg.Text('', key='dir_bms', font=self.FONT)],
            ]
        ico=self.ico_path('icon.ico')
        self.window = sg.Window('BMS導入支援君 - 設定', layout, grab_anywhere=True,return_keyboard_events=True,resizable=False,finalize=True,enable_close_attempted_event=True,icon=ico,location=(self.settings.params['lx'], self.settings.params['ly']))
        self.window['dir_dl'].update(self.settings.params['dir_dl'])
        self.window['dir_bms'].update(self.settings.params['dir_bms'])

    def gui_main(self): # GUI設定
        self.mode = 'main' # main, setting
        if self.window:
            self.window.close()
        layout = [
            [sg.Button('設定', key='btn_setting', font=self.FONT),sg.Button('難易度表読み込み', key='btn_read_table', font=self.FONT),sg.Button('parse', key='btn_parse', font=self.FONT)],
            [sg.Text('難易度表のURL', font=self.FONT)],
            #[sg.Input('', key='url_table', font=self.FONT)],
            [sg.Input('https://stellabms.xyz/dp/table.html', key='url_table', font=self.FONT)],
            #[sg.Output(size=(63,8), key='output', font=('Meiryo',9))] # ここを消すと標準出力になる
            ]
        ico=self.ico_path('icon.ico')
        self.window = sg.Window('BMS導入支援君', layout, grab_anywhere=True,return_keyboard_events=True,resizable=False,finalize=True,enable_close_attempted_event=True,icon=ico,location=(self.settings.params['lx'], self.settings.params['ly']))

    def gui_table(self, url): # テーブル表示用
        self.mode = 'table'
        url_header = re.sub(url.split('/')[-1], 'header.json', url)
        ### header情報から難易度名などを取得
        info = self.read_table_json(url_header)
        url_dst = re.sub(url.split('/')[-1], info['data_url'], url)
        header=['LV','title','artist']
        self.songs = self.read_table_json(url_dst)

        self.name = info['name']
        self.symbol = info['symbol']

        data = []
        for s in self.songs:
            onesong = [self.symbol+s['level'], s['title'], s['artist']]
            data.append(onesong)

        layout = [
            [sg.Table(data, headings=header, vertical_scroll_only=False, auto_size_columns=False, col_widths=[5,40,40], justification='left', size=(1,20))],
            [sg.Button('DL', key='btn_download'),sg.Button('parse', key='btn_parse')],
            ]
        ico=self.ico_path('icon.ico')

        self.window.close()
        self.window = sg.Window('BMS導入支援君 - 難易度表モード', layout, grab_anywhere=True,return_keyboard_events=True,resizable=False,finalize=True,enable_close_attempted_event=True,icon=ico,location=(self.settings.params['lx'], self.settings.params['ly']), size=(800,400))

    def parse_all(self):
        try:
            extractor = Extractor(self.settings.params['dir_dl'], self.settings.params['dir_bms'])
            # 本体を解凍
            for z in extractor.ziplist:
                if z.is_for_bms and not z.only_bms:
                    print(f'unpacking {z.filename} (has_folder:{z.has_folder})')
                    z.extractall(self.settings.params['dir_bms'])
            # 差分を解凍
            for z in extractor.ziplist:
                if z.is_for_bms and z.only_bms:
                    z.get_score_and_extract(self.settings.params['dir_bms'], 0.95)
        except rarfile.RarCannotExec:
            sg.popup('error! rar解凍ソフトがインストールされていません')

    def main(self):
        self.gui_main()
        isValid = True
        while isValid:
            ev, val = self.window.read()
            #print(f"event='{ev}', values={val}, isValid={isValid}")
            # 設定を最新化
            if self.settings and val: # 起動後、そのまま何もせずに終了するとvalが拾われないため対策している
                self.settings.params['lx'] = self.window.current_location()[0]
                self.settings.params['ly'] = self.window.current_location()[1]
            
            if ev in (sg.WIN_CLOSED, 'Escape:27', '-WINDOW CLOSE ATTEMPTED-'): # 終了処理
                if self.mode == 'main':
                    self.settings.params['lx'] = self.window.current_location()[0]
                    self.settings.params['ly'] = self.window.current_location()[1]
                    self.settings.save_settings()
                    self.window.close()
                    isValid = False # 終了
                    break
                else:
                    self.settings.params['lx'] = self.window.current_location()[0]
                    self.settings.params['ly'] = self.window.current_location()[1]
                    self.gui_main()
                    self.mode = 'main'
            elif ev == 'btn_setting':
                self.gui_setting()
            elif ev.startswith('btn_select_'):
                target = ev.split('_')[-1]
                #tmp = sg.popup_get_folder('ブラウザのファイル保存先を指定してください。')
                tmp = filedialog.askdirectory()
                if tmp != '':
                    self.window[f'dir_{target}'].update(tmp)
                    self.settings.params[f'dir_{target}'] = tmp
            elif ev == 'btn_read_table':
                url = val['url_table']
                self.gui_table(url)
            elif ev == 'btn_download':
                for idx in val[0]:
                    print(f"selected: {self.songs[idx]['title']}, sha256: {self.songs[idx]['sha256']}")
                    #print(f"{self.songs[idx]}")
                    if self.songs[idx]['url'] != '':
                        webbrowser.open(self.songs[idx]['url'])
                    if self.songs[idx]['url_diff'] != '':
                        webbrowser.open(self.songs[idx]['url_diff'])
            elif ev == 'btn_parse':
                self.parse_all()

if __name__ == '__main__':
    a = GUIManager()
    a.main()
