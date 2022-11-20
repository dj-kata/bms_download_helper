import glob, os
from pathlib import Path
from zipmanager import ZipManager

"""
### このクラスでやりたいこと
- ブラウザ用DLフォルダを監視し、増えたファイルを自動で解凍
- 差分フォルダを検出し、適切な本体フォルダに移動
  - 差分ファイルに対してsha256ハッシュを計算
  - 差分ファイルのみのディレクトリかどうかを検出(一括で差分のhash値リストを出すのが良いか？)
  - 上位側からhash値、差分もDLしたかなどの情報はもらう？

  sha256のリストいらなくない？差分と本体を確認して適切な本体フォルダに入れるだけでいい気がする

  処理順はこんな感じ?
  1. is_for_bms == True かつ only_bms != Falseのフォルダ(本体)をすべて解凍
  2. それ以外のis_for_bms == True(差分)について、本体を見つけて同じフォルダに解凍する
"""

class Extractor:
    def __init__(self, dir_dl, dir_bms, skip_threshold):
        self.dir_dl = dir_dl
        self.dir_bms = dir_bms
        self.ziplist = []
        self.skip_threshold = skip_threshold
        self.update_ziplist()

    def update_ziplist(self): # ブラウザのDLフォルダを監視
        # ブラウザ用ディレクトリのファイルを古いものから表示
        paths = list(Path(self.dir_dl).glob(r'*.*'))
        paths.sort(key=os.path.getmtime)
        for f in paths:
            if ('.zip' in str(f)) or ('.rar' in str(f)):
                print('reading:', f)
                zp = ZipManager(f)
                self.ziplist.append(zp)
                #zp.disp()

    def extract_test(self): # beyond the alice[14N]
        target_hash = '46e0afa589a02f91f9da7b25c9ecb5d3790f797a1e64d65d7ead7a6546cfadb0'
        paths = list(Path(self.dir_dl).glob(r'*.*'))
        paths.sort(key=os.path.getmtime)
        zp = ZipManager(paths[-1])
        zp.extractall(self.dir_bms)
        wavlist_sabun = []
        print(paths[-1], f"only_bms={zp.only_bms}, is_for_bms={zp.is_for_bms}")
        if target_hash in zp.hashes.keys(): # 所望の譜面が含まれている
            print(f"sl0 Beyond the aliceを検出 => {zp.hashes[target_hash]}")
            ### TODO 譜面の中身を見て判定
            wavlist_sabun = zp.get_wavelist(zp.hashes[target_hash])
        zp = ZipManager(paths[-2])
        zp.extractall(self.dir_bms)
        chk = zp.get_score_wavelist(wavlist_sabun) # bme内の全wavで本体内に含まれているものの数を数える
        print(paths[-2], f"only_bms={zp.only_bms}, is_for_bms={zp.is_for_bms}")
        print(f"上記差分の一致スコア: {chk:.2f}")

    def main(self):
        ### TODO
        pass

if __name__ == "__main__":
    a = Extractor('C:/Users/katao/Downloads', './bms')
    a.extract_test()
    a.update_ziplist()