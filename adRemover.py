import frida
from time import sleep
import psutil
from threading import Lock, Thread
import _thread
import subprocess, os, sys
from pathlib import Path
import shutil,requests,json, websocket
from filelock import Timeout, FileLock

class adRemover:
    def __init__(self, log=False):
        self.lockRunas = Lock() 
        self.log = log
        if sys.platform == "darwin":
            self.spotify = r'open /Applications/Spotify.app'
            self.pName = 'Spotify'
            self.moduleName = '"Chromium Embedded Framework"'
        else:
            self.spotify = os.getenv('APPDATA') + r'\Spotify\Spotify.exe'
            self.pName = 'Spotify.exe'
            self.moduleName = '"libcef.dll"'
            """
                ----- Inject Method -----
            """
            self.debuggerPort = "9229"
            self.remover_main = "setInterval(function(){try{Ads.clearSlot('video'),Ads.clearSlot('banner'),Ads.clearSlot('audio'),Ads.clearSlot('stream'),Ads.clearSlot('hpto'),Ads.clearSlot('leaderboard')}catch(e){}},1000),setInterval(function(){for(var e=document.querySelectorAll('iframe'),o=0;o<e.length;o++)console.log('RM'),e[o].parentNode.removeChild(e[o])},1);var originalFetch=window.fetch;window.fetch=function(e,o){return console.log('fetch: '+e),null==e||e.includes('spotify.com')?originalFetch.call(window,e,o):(console.log('RM2'),!1)};"
            self.remover_service = "var originalFetch=fetch;fetch=function(e,o){return console.log(e.url, e),originalFetch(e,o)}"
            self.cachePath = [
                os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\16562dee83627072da713c30e2a0f24c77dcb93d\Network Persistent State',
                os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Network Persistent State',
                os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Code Cache',
                os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\16562dee83627072da713c30e2a0f24c77dcb93d\Code Cache',
                os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Session Storage',
                os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\IndexedDB',
                os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Service Worker\CacheStorage'
            ]
            """
                ----- Inject Method -----
            """
		
    def request(self, uri):
        response = requests.get(uri)
        try:
            json_object = json.loads(response.content)
        except ValueError:
            raise Exception("[RQ] Json is Not Valid!")
        return json_object

    def mLog(self, text):
        if self.log == True: print(text)

    def clearCache(self):
        while(1):
            for path in self.cachePath:
                my_file = Path(path)
                if my_file.is_file():
                    os.remove(my_file)
                    self.mLog("[CH] File: " + path)
                if my_file.is_dir():
                    shutil.rmtree(my_file, ignore_errors=True)
                    self.mLog("[CH] Folder: " + path)

    def onMessage(self, message, data):
       self.mLog(message["payload"])

    def method_hook(self):
        proc = subprocess.Popen(self.spotify, shell=True)
        sleep(2)
        session = frida.attach(proc.pid+1)
        script = session.create_script("""
            const blackList = [
                "https://spclient.wg.spotify.com/ad-logic/",
                "https://spclient.wg.spotify.com/ads/",
                "https://spclient.wg.spotify.com/gabo-receiver-service/"
            ];
            var hookCreateUrl = Module.findExportByName(""" + self.moduleName + """, 'cef_string_utf8_to_utf16');
            Interceptor.attach(hookCreateUrl, {
                onEnter: function (args) {
                    var url = ptr(args[0]).readCString(-1);
                    if(blackList.some(v => url.includes(v))){
                        this.find = true;
                        this.ptr = args[2];
                        this.url = url;
                    }
                },
                onLeave: function (args) {
                    var mys = Memory.allocUtf16String("http://fku.com");
                   if(this.find){
                        send("[HM]" + this.url);
                        ptr(this.ptr).readPointer().writePointer(mys);
                   }
                }
            });
            """)
        script.on('message', self.onMessage)
        script.load()
        self.WaitForRunAs()

    def method_inject(self):
        _thread.start_new_thread(self.clearCache, ())
        try:
            if Path(os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Cookies').is_file():
                os.remove(Path(os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Cookies'))
            lock = FileLock(Path(os.getenv('LOCALAPPDATA') + r'\Spotify\Browser\Cookies'),timeout=10)
            lock.acquire()
        except Timeout:
            self.mLog("[Run] Timeout")
        sleep(2)
        subprocess.Popen([self.spotify, '--remote-debugging-port='+self.debuggerPort])
        sleep(2)
        self.ws()
        self.WaitForRunAs()

    def ws(self):
        resp = self.request("http://localhost:"+self.debuggerPort+"/json")
        def send(ws, inj):
            ws.send(r'{"id": 1355377, "method": "Runtime.evaluate", "params": {"expression": "' + inj + r'"}}')
        _thread.start_new_thread(lambda: websocket.WebSocketApp(resp[0]["webSocketDebuggerUrl"],
            on_message=lambda ws,msg : self.mLog("[WS_MN] " + msg),
            on_open=lambda ws: send(ws, self.remover_main)).run_forever(), ())

        _thread.start_new_thread(lambda: websocket.WebSocketApp(resp[1]["webSocketDebuggerUrl"],
            on_message=lambda ws,msg : self.mLog("[WS_SW] " + msg),
            on_open=lambda ws: send(ws, self.remover_service)).run_forever(), ())

    def WaitForRunAs(self):
        while True:
            if (self.pName in (p.name() for p in psutil.process_iter())) and not self.lockRunas.locked():
                self.lockRunas.acquire()
                print("[+] Found SP")
                sleep(0.5)
            elif (not self.pName in (p.name() for p in psutil.process_iter())) and self.lockRunas.locked():
                self.lockRunas.release()
                print("[+] SP is dead releasing lock")
                break
            else:
                pass
            sleep(0.5)

if __name__ == "__main__":
    try :
        adRemover(log=False).method_hook()
    except Exception as err:
        print("[Error]{}".format(err))
