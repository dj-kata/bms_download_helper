import zipfile, rarfile # winrarインストール必須?
import sys, re
import hashlib # hashlib.sha256(data).hexdigest()
import glob
# winrarインストールしないとダメかも?
# https://visatch.medium.com/python-rarfile-package-error-rarfile-rarcannotexec-cannot-find-working-tool-window-only-630ff25f4ef8

# TODO
### 将来的に、lzh, rarあたりへの対応は必要か

# 圧縮ファイル管理クラス
# 1つの圧縮ファイルに対して1つインスタンス化する
class ZipManager:
    def __init__(self, filename):
        self.filename = filename
        self.is_rar_file = False
        if str(self.filename)[-4:] == '.rar':
            self.is_rar_file = True
            self.zipfile  = rarfile.RarFile(filename)
        else:
            self.zipfile  = zipfile.ZipFile(filename)
        self.filelist = self.zipfile.namelist() # 中身のリスト、lst[0]がディレクトリならそのまま解凍できそう
        self.wavelist = [] # このzipファイルに含まれる音声ファイル一覧
        self.has_folder = False
        self.only_bms   = True # bmsファイルしかないかのフラグ、将来消すかも
        self.hashes = {} # 同梱bmsファイルのsha256ハッシュ値一覧
        self.update_has_folder()
        self.update_hashes()
        self.update_only_bms()
        self.update_wavelist()
        self.is_for_bms = len(self.hashes.keys()) > 0 # BMS用の圧縮ファイルであるかどうかを示す

    def disp(self):
        print(f"{self.filename}, only_bms:{self.only_bms}, has_folder:{self.has_folder}, is_for_bms:{self.is_for_bms}, is_rar_file:{self.is_rar_file}")

    def update_has_folder(self):
        self.has_folder = (len(self.filelist[0].split('/')) == 2) or (self.filelist[0][-1] == '/')

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
                if self.is_rar_file:
                    with rarfile.RarFile(self.filename) as rf:
                        hashval = hashlib.sha256(rf.read(f)).hexdigest()
                        self.hashes[hashval] = f
                else:
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
                            tmp = line[7:-4] # ogg/wavに対応するため、拡張子はここで消す
                            #tmp = re.findall('\S+', line)[-1].split('.')[0].split('/')[-1] # ogg/wavに対応するため、拡張子はここで消す
                            ret.append(tmp)
        return ret

    # wave一覧を受け取り、このzipfile内に含まれる物の割合を計算する
    # 基本的に本体と差分は別ファイルなので、引数のwavelistも別ファイルのものである点に注意
    def get_score_wavelist(self, _wavelist):
        ret = 0

        for wav in self.wavelist:
            if wav in _wavelist:
                ret += 1

        return ret / len(self.wavelist)

    # 譜面zipに対して実行、BMSフォルダ内の各サブフォルダを走査し、
    # 譜面をスコアが高いサブフォルダに解凍する。こちらに一本化したい
    def get_score_and_extract(self, dir_dst, threshold=0.95):
        # 1番目の譜面のwavリストを作成
        this_wavelist = self.get_wavelist(list(self.hashes.values())[0])
        for subdir in glob.glob(dir_dst+'/*'):
            subdir_wavelist = []
            for f in glob.glob(subdir+'/*'):
                if f.lower()[-4:] in ['.wav', '.ogg']:
                    subdir_wavelist.append(f.split('.')[0].split('/')[-1].split('\\')[-1])
            val = 0

            for wav in this_wavelist:
                if wav in subdir_wavelist:
                    val += 1
            val = val / len(this_wavelist)
            if val >= threshold:
                print(f"{self.filename} -> {subdir} (score:{val:.2f})")
                for fumen in self.hashes.values():
                    if len(fumen.split('/')) == 1:
                        self.zipfile.extract(fumen, subdir)
                    else: # 譜面zipにサブフォルダが含まれる場合、ファイルの中身を直接書き込む(APIが用意されていない)
                        with open(subdir+f"/{fumen.split('/')[1]}", 'wb') as outbms:
                            outbms.write(self.zipfile.open(fumen).read())


    def extractall(self, target_dir):
        dst = target_dir
        error = ''
        if not self.has_folder:
            # WindowsPathで取得したスペース入りのファイル名がパースできない
            # F文字列ではどうやらバックスラッシュが使えないらしい
            tmp = str(self.filename).split('\\')[-1].split('/')[-1].split('.')[0]
            dst += f"/{tmp}"
        print(self.filename, self.is_rar_file, self.filelist[0])
        if self.is_rar_file:
            for f in self.zipfile.infolist():
                try:
                    self.zipfile.extract(f.filename, dst)
                except:
                    error += f'解凍エラー; {f.filename}\n'
        else:
            self.zipfile.extractall(dst)
        if error != '':
            print(error)
        return error

if __name__ == '__main__':
    a = ZipManager('ziptest/with_dir.zip')
    a.disp()
    #a.extract('./dst')
    b = ZipManager('ziptest/no_dir.zip')
    b.disp()
    b.extract('./dst')