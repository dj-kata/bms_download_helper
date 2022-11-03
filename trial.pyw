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

    def gui_setting(self):
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
        layout = [
            [sg.Button('設定', key='btn_setting', font=self.FONT),sg.Button('難易度表読み込み', key='btn_read_table', font=self.FONT)],
            [sg.Text('難易度表のURL', font=self.FONT)],
            [sg.Input('', key='url_table', font=self.FONT)],
            #[sg.Output(size=(63,8), key='output', font=('Meiryo',9))] # ここを消すと標準出力になる
            ]
        ico=self.ico_path('icon.ico')
        self.window = sg.Window('BMS導入支援君', layout, grab_anywhere=True,return_keyboard_events=True,resizable=False,finalize=True,enable_close_attempted_event=True,icon=ico,location=(self.settings.params['lx'], self.settings.params['ly']))

    def main(self):
        self.mode = 'main' # main, setting
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
                    self.window.close()
                    self.gui_main()
                    self.mode = 'main'
            elif ev == 'btn_setting':
                self.mode = 'setting'
                self.window.close()
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
                self.mode = 'table'
                self.window.close()
                self.gui_table()

if __name__ == '__main__':
    a = GUIManager()
    a.main()
