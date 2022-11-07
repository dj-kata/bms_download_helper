import zipfile
import sys, re
import hashlib # hashlib.sha256(data).hexdigest()

# TODO
### 将来的に、lzh, rarあたりへの対応は必要か

# 圧縮ファイル管理クラス
# 1つの圧縮ファイルに対して1つインスタンス化する
class ZipManager:
    def __init__(self, filename):
        self.filename = filename
        self.zipfile  = zipfile.ZipFile(filename)
        self.filelist = self.zipfile.namelist() # 中身のリスト、lst[0]がディレクトリならそのまま解凍できそう
        self.wavelist = []
        self.has_folder = False
        self.only_bms   = True # bmsファイルしかないかのフラグ、将来消すかも
        self.hashes = {} # 同梱bmsファイルのsha256ハッシュ値一覧
        self.update_has_folder()
        self.update_hashes()
        self.update_only_bms()
        self.update_wavelist()
        self.is_for_bms = len(self.hashes.keys()) > 0 # BMS用の圧縮ファイルであるかどうかを示す

    def disp(self):
        print(f"{self.filename}, only_bms:{self.only_bms}, has_folder:{self.has_folder}, is_for_bms:{self.is_for_bms}")

    def update_has_folder(self):
        self.has_folder = self.filelist[0][-1] == '/'

    def get_dst_folder(self):
        ret = False
        if self.has_folder:
            ret = self.filelist[0]
        else:
            ret = str(self.filename).split('\\')[-1].split('/')[-1].split('.')[0]
        return ret

    # このzipfile内に含まれるwaveファイルの一覧を作成
    # ogg/wavへの対応のため、拡張子は消す
    def update_wavelist(self):
        for f in self.filelist:
            if f.lower().endswith('.wav') or f.lower().endswith('.ogg'):
                self.wavelist.append(f[:-4].split('/')[-1])

    def update_only_bms(self):
        for f in self.filelist:
            if f[-1] != '/': # フォルダは除外
                if f[-4:] not in ['.bms', '.bme'] and f[-4:].lower() in ['.ogg', '.wav']: # 音声ファイルがあれば本体とみなす
                    self.only_bms = False
                    break

    def update_hashes(self):
        for f in self.filelist: # ファイル一覧から1つずつ確認
            if ('.bms' in f) or ('.bme' in f): # BMS譜面ならハッシュ値計算
                with zipfile.ZipFile(self.filename) as myzip:
                    with myzip.open(f) as myfile:
                        hashval = hashlib.sha256(myfile.read()).hexdigest()
                        self.hashes[hashval] = f
    
    # 譜面のファイル名を受け取り、bme内で使っているwav/oggのリストを生成して返す
    def get_wavelist(self, filename):
        ret = []
        with zipfile.ZipFile(self.filename) as myzip:
            with myzip.open(filename) as f:
                while 1:
                    line = f.readline()
                    if not line:
                        break
                    else:
                        line = line.decode('cp932').strip()
                        if line.startswith('#WAV'):
                            tmp = re.findall('\S+', line)[-1].split('.')[0].split('/')[-1] # ogg/wavに対応するため、拡張子はここで消す
                            ret.append(tmp)
        return ret

    # wave一覧を受け取り、このzipfile内に含まれる物の割合を計算する
    # 基本的に本体と差分は別ファイルなので、引数のwavelistも別ファイルのものである点に注意
    def get_score_wavelist(self, _wavelist):
        ret = 0

        for wav in _wavelist:
            if wav in self.wavelist:
                ret += 1

        return ret / len(_wavelist)

    def extractall(self, target_dir):
        dst = target_dir
        if not self.has_folder:
            # WindowsPathで取得したスペース入りのファイル名がパースできない
            # F文字列ではどうやらバックスラッシュが使えないらしい
            tmp = str(self.filename).split('\\')[-1].split('/')[-1].split('.')[0]
            dst += f"/{tmp}"
        self.zipfile.extractall(dst)

    # 差分の解凍用。サブフォルダに入っていても譜面だけ解凍したいので別関数とする
    def extract_sabun(self, target_dir):
        for fumen in self.hashes.values():
            self.zipfile.extract(fumen, target_dir)

if __name__ == '__main__':
    a = ZipManager('ziptest/with_dir.zip')
    a.disp()
    #a.extract('./dst')
    b = ZipManager('ziptest/no_dir.zip')
    b.disp()
    b.extract('./dst')