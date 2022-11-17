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
import shutil

# TODO
# メニューバーに入れたい
# URL入力ボックスでの右クリック
# 完了したファイルを移動するモードの追加
# ファイル数を見て多すぎる場合はスキップできるようにする
# rar回避モードを入れる？

class UserSettings:
    def __init__(self, savefile='settings.json'):
        self.savefile = savefile
        self.params   = self.load_settings()
    def get_default_settings(self):
        ret = {
        'lx':0,'ly':0
        ,'dir_bms':'' # BMS置き場
        ,'dir_dl':'' # ブラウザのDownloadフォルダ
        ,'url':''
        ,'move_extracted_file':True # 処理済みファイルをDLフォルダ/doneに移動するかどうか
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
        sg.theme('SystemDefault')
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
            f.close()
        except urllib.error.URLError:
            print('Not found:', url)
            flag = False
        except urllib.request.HTTPError:
            print('Not found:', url)
            flag = False
        except ValueError:
            print('Not found:', url)
            flag = False

        return flag

    def read_table_json(self, url):
        ret = False
        print(url, 'check_url:',self.check_url(url))
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
        if self.window:
            self.window.close()
        layout = [
            [sg.Text('ブラウザのファイル保存先', font=self.FONT), sg.Button('変更', font=self.FONT, key='btn_select_dl')],
            [sg.Text('', key='dir_dl', font=self.FONT)],
            [sg.Text('BMSデータ保存先', font=self.FONT), sg.Button('変更', font=self.FONT, key='btn_select_bms')],
            [sg.Text('', key='dir_bms', font=self.FONT)],
            [sg.Checkbox('展開済みファイルをdoneフォルダに移動する', key='chk_done', font=self.FONT, default=self.settings.params['move_extracted_file'])],
            [sg.Button('close', key='btn_close_setting')],
            ]
        ico=self.ico_path('icon.ico')
        self.window = sg.Window('BMS導入支援君 - 設定', layout, grab_anywhere=True,return_keyboard_events=True,resizable=False,finalize=True,enable_close_attempted_event=True,icon=ico,location=(self.settings.params['lx'], self.settings.params['ly']))
        self.window['dir_dl'].update(self.settings.params['dir_dl'])
        self.window['dir_bms'].update(self.settings.params['dir_bms'])

    def gui_main(self): # テーブル表示用
        if self.window:
            self.window.close()
        self.mode = 'main'
        header=['LV','Title','Artist','Proposer','差分が別','sha256']
        layout = [
            [sg.Button('設定', key='btn_setting', font=self.FONT),sg.Button('難易度表読み込み', key='btn_read_table', font=self.FONT),sg.Button('DL', key='btn_download',font=self.FONT),sg.Button('parse', key='btn_parse', font=self.FONT)],
            [sg.Text('難易度表のURL', font=self.FONT)],
            [sg.Input(self.settings.params['url'], key='url_table', font=self.FONT)],
            [sg.Table([], key='table', headings=header, font=self.FONT, vertical_scroll_only=False, auto_size_columns=False, col_widths=[5,40,40,10,7,15], justification='left', size=(1,10))],
            [sg.Text('', key='txt_info', font=('Meiryo',10))],
            ]
        ico=self.ico_path('icon.ico')

        self.window = sg.Window('BMS導入支援君', layout, grab_anywhere=True,return_keyboard_events=True,resizable=True,finalize=True,enable_close_attempted_event=True,icon=ico,location=(self.settings.params['lx'], self.settings.params['ly']), size=(800,600))
        self.window['table'].expand(expand_x=True, expand_y=True)

    def update_table(self, url):
        try:
            url_header = re.sub(url.split('/')[-1], 'header.json', url)
            ### header情報から難易度名などを取得
            info = self.read_table_json(url_header)
            url_dst = re.sub(url.split('/')[-1], info['data_url'], url)
            self.songs = self.read_table_json(url_dst)

            self.name = info['name']
            self.symbol = info['symbol']

            data = []
            for s in self.songs:
                has_sabun = ''
                if s['url_diff'] != "":
                    has_sabun = '○'
                onesong = [self.symbol+s['level'], s['title'], s['artist'], s['proposer'], has_sabun, s['sha256']]
                data.append(onesong)
            self.window['table'].update(data)
            self.update_info('難易度表読み込み完了。')
        except: # URLがおかしい
            self.update_info('存在しないURLが入力されました。ご確認をお願いします。')

    def update_info(self, msg):
        print(msg)
        self.window['txt_info'].update(msg)

    def parse_all(self):
        if self.settings.params['move_extracted_file']: # 移動オプション有効時は移動先を作成しておく
            if not os.path.exists(self.settings.params['dir_dl']+'\done'):
                os.mkdir(self.settings.params['dir_dl']+'\done')

        self.window.write_event_value('-INFO-', f'展開モード開始。ファイル一覧を取得中。')
        extractor = Extractor(self.settings.params['dir_dl'], self.settings.params['dir_bms'])
        self.window.write_event_value('-INFO-', f'ファイル一覧取得完了。')
        flg_err = False
        cnt_bms = 0 # bms関連フォルダの数
        for z in extractor.ziplist:
            if z.is_for_bms:
                cnt_bms += 1
        # 本体を解凍
        for z in extractor.ziplist:
            if z.is_for_bms and not z.only_bms:
                self.window.write_event_value('-INFO-', f'本体を展開中: {z.filename}')
                z.extractall(self.settings.params['dir_bms'])
                if self.settings.params['move_extracted_file']:
                    z.close()
                    fff = str(z.filename).split('/')[-1].split('\\')[-1]
                    shutil.move(z.filename, self.settings.params['dir_dl']+f'\done\{fff}')
                try:
                    self.window.write_event_value('-INFO-', f'本体を展開中: {z.filename}')
                    err = z.extractall(self.settings.params['dir_bms'])
                    if self.settings.params['move_extracted_file']:
                        z.close()
                        fff = str(z.filename).split('/')[-1].split('\\')[-1]
                        shutil.move(z.filename, self.settings.params['dir_dl']+f'\done\{fff}')
                except:
                    flg_err = True
                    self.window.write_event_value('-INFO-', f'展開時にエラー: {z.filename}')

        # 差分を解凍
        for z in extractor.ziplist:
            if z.is_for_bms and z.only_bms:
                try:
                    self.window.write_event_value('-INFO-', f'差分を展開中: {z.filename}')
                    maxval = z.get_score_and_extract(self.settings.params['dir_bms'], 0.95)
                    if self.settings.params['move_extracted_file'] and (maxval >= 0.95):
                        z.close()
                        fff = str(z.filename).split('/')[-1].split('\\')[-1]
                        shutil.move(z.filename, self.settings.params['dir_bms']+f'\done\{fff}')
                except:
                    flg_err = True
                    self.window.write_event_value('-INFO-', f'展開時にエラー: {z.filename}')

        if flg_err:
            #sg.popup('一部ファイルの解凍時にエラーが発生しました。\n(rar解凍ソフトがインストールされていないかも?)\nWinRARのインストールをお願いします。\nhttps://github.com/dj-kata/bms_downloader')
            print('一部ファイルの解凍時にエラーが発生しました。\n(rar解凍ソフトがインストールされていないかも?)\nWinRARのインストールをお願いします。\nhttps://github.com/dj-kata/bms_downloader')
        self.update_info(f'DLフォルダ内ファイルの展開完了。')

    def main(self):
        self.gui_main()
        self.update_info('起動完了。')
        isValid = True
        th_parse = False
        while isValid:
            ev, val = self.window.read()
            #print(f"event='{ev}', values={val}, isValid={isValid}")
            # 設定を最新化
            if self.settings and val: # 起動後、そのまま何もせずに終了するとvalが拾われないため対策している
                self.settings.params['lx'] = self.window.current_location()[0]
                self.settings.params['ly'] = self.window.current_location()[1]
                if 'url_table'in val.keys():
                    self.settings.params['url'] = val['url_table']
                if 'chk_done'in val.keys():
                    self.settings.params['move_extracted_file'] = val['chk_done']
            
            if ev in (sg.WIN_CLOSED, 'Escape:27', '-WINDOW CLOSE ATTEMPTED-', 'btn_close_setting'): # 終了処理
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
            elif ev == '-INFO-':
                print('-INFO-:',val[ev].strip())
                self.window['txt_info'].update(val[ev])
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
                #self.gui_table(url)
                self.update_table(url)
            elif ev == 'btn_download':
                for idx in val['table']:
                    print(f"selected: {self.songs[idx]['title']}, sha256: {self.songs[idx]['sha256']}")
                    if self.songs[idx]['url'] != '':
                        webbrowser.open(self.songs[idx]['url'])
                    if self.songs[idx]['url_diff'] != '':
                        webbrowser.open(self.songs[idx]['url_diff'])
                self.update_info('選択した曲の本体・差分のURLを開きました。ブラウザからDLをお願いします。')
                
            elif ev == 'btn_parse':
                if th_parse:
                    th_parse.join()
                th_parse = threading.Thread(target=self.parse_all, daemon=True)
                th_parse.start()

if __name__ == '__main__':
    a = GUIManager()
    a.main()
