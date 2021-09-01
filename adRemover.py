import frida
from time import sleep
import psutil
from threading import Lock, Thread
import _thread
import subprocess,os
from pathlib import Path
import shutil
from filelock import Timeout, FileLock

class adRemover:
    def __init__(self, log=False):
        self.lockRunas = Lock() 
        self.log = log
        self.spotify = os.getenv('APPDATA') + r'\Spotify\Spotify.exe'
        self.cachePath = [
            os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\16562dee83627072da713c30e2a0f24c77dcb93d\Network Persistent State',
            os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Network Persistent State',
            os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Code Cache',
            os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\16562dee83627072da713c30e2a0f24c77dcb93d\Code Cache',
            os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Session Storage',
            os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\IndexedDB',
            os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Service Worker\CacheStorage'
        ]
		
    def mLog(self, text):
        if self.log == True: print(text)

    def clearCache(self):
        while(1):
            for path in self.cachePath:
                my_file = Path(path)
                if my_file.is_file():
                    os.remove(my_file)
                    self.mLog("[ClearCache] File: " + path)
                if my_file.is_dir():
                    shutil.rmtree(my_file, ignore_errors=True)
                    self.mLog("[ClearCache] Folder: " + path)

    def onMessage(self,message, data):
        self.mLog(message)

    def run(self):
        _thread.start_new_thread(self.clearCache, ())
        try:
            if Path(os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Cookies').is_file():
                os.remove(Path(os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Cookies'))
            lock = FileLock(Path(os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Cookies'),timeout=10)
            lock.acquire()
        except Timeout:
            self.mLog("[Run] Timeout")
        sleep(2)
        proc = subprocess.Popen([self.spotify])
        sleep(3)
        session = frida.attach(proc.pid)
        script = session.create_script("""
            const blackList = [
                "google",
                "doubleclick",
                "gstatic",
                "adeventtracker",
                "api-partner",
                "sentry",
                "mosaic",
                "scdn",
                "quicksilver",
                "adsafeprotected",
                "rubiconproject.com",
                "cloudfront.net",
                "spclient.",
                "https://spclient.wg.spotify.com/ad-logic/",
                "https://spclient.wg.spotify.com/ads/",
                "https://spclient.wg.spotify.com/gabo-receiver-service/"
            ];
            var hookParseUrl = Module.findExportByName("libcef.dll", 'cef_parse_url');
            var hookCreateUrl = Module.findExportByName("libcef.dll", 'cef_urlrequest_create');
            Interceptor.attach(hookParseUrl, {
                onEnter: function (args) {
                    var mptr = ptr(args[0]).readPointer().readUtf16String(-1);
                    if(!mptr.includes("spotify.com") || blackList.some(v => mptr.includes(v))){
                        args[0] = ptr(0x0);
                        send("[JS] Remove: " + mptr);
                    } else {
                        send("[JS] Load: " + mptr);
                    }
                },
                onLeave: function (args) {}
            });
            """)
        script.on('message', self.onMessage)
        script.load()
        self.WaitForRunAs()

    def WaitForRunAs(self):
        while True:
            if ("Spotify.exe" in (p.name() for p in psutil.process_iter())) and not self.lockRunas.locked():
                self.lockRunas.acquire()
                print("[+] Found RunAs")
                sleep(0.5)
            elif (not "Spotify.exe" in (p.name() for p in psutil.process_iter())) and self.lockRunas.locked():
                self.lockRunas.release()
                print("[+] Runas is dead releasing lock")
                break
            else:
                pass
            sleep(0.5)

if __name__ == "__main__":
    try :
        adRemover(log=True).run()
    except Exception as err:
        print("[Error]{}".format(err))
