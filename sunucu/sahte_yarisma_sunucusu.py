from flask import Flask, request
from datetime import datetime

app = Flask(__name__)
son_veri_zamanlari = {20: None}

takim_ipleri = dict()

def ucak_verisi_uret():
    raise NotImplemented

@app.route('/api/giris', methods=['POST'])
def login():
    global son_veri_zamanlari, takim_ipleri
    json_rq = request.json
    address = request.remote_addr
    if 'kadi' in json_rq and 'sifre' in json_rq and (address not in takim_ipleri):
        app.logger.info('Kullanici girisi basarili. Takim numarasi `20`')
    else:
        app.logger.error('Login hatasi ya daha once giris yaptiniz, ya da request hatali.')
        return '', 400
    takim_ipleri[address] = 20
    son_veri_zamanlari[20] = datetime.now()
    return '20', 200

@app.route('/api/kilitlenme_bilgisi')
def kilitlenme_bilgisi():
    kilitlenme_verisi = request.json
    app.logger.info(f'Kilitlenme verisi alindi. {kilitlenme_verisi}')
    return '', 200

@app.route('/api/sunucusaati')
def sunucu_saati():
    if request.remote_addr not in takim_ipleri:
        return "Kullanici oturum acmadi.", 401
    t = datetime.now()
    app.logger.debug(f"Sunucu saati istendi. {t}")
    return {'saat': t.hour, 'dakika': t.minute, 'saniye':t.second, 'milisaniye': t.microsecond / 1000} 

@app.route('/api/telemetri_gonder', methods=['POST'])
def telemetri_gonder():
    global takim_ipleri
    json_rq = request.json
    takim_no = json_rq['takim_numarasi']
    if request.remote_addr not in takim_ipleri:
        return "Kullanici oturum acmadi.", 401
    global son_veri_zamanlari
    t1 = son_veri_zamanlari[takim_no]
    t2 = datetime.now()
    son_veri_zamanlari[20] = t2
    if (t2 - t1).seconds > 2:
        app.logger.error("Telemetre verisi 2sn den gec gonderildi.")
        return 3, 400
    else:
        sistem_saati = sunucu_saati()
        return {'sistemSaati': sistem_saati, 
                    "konumBilgileri": [
                                    {
                                    "takim_numarasi": 1,
                                    "iha_enlem": 500,
                                    "iha_boylam": 500,
                                    "iha_irtifa": 500,
                                    "iha_dikilme": 5,
                                    "iha_yonelme": 256,
                                    "iha_yatis": 0,
                                    "zaman_farki": 93
                                    },
                                    {
                                    "takim_numarasi": 2,
                                    "iha_enlem": 500,
                                    "iha_boylam": 500,
                                    "iha_irtifa": 500,
                                    "iha_dikilme": 5,
                                    "iha_yonelme": 256,
                                    "iha_yatis": 0,
                                    "zaman_farki": 74
                                    },
                                    {
                                    "takim_numarasi": 3,
                                    "iha_enlem": 433.5,
                                    "iha_boylam": 222.3,
                                    "iha_irtifa": 222.3,
                                    "iha_dikilme": 5,
                                    "iha_yonelme": 256,
                                    "iha_yatis": 0,
                                    "zaman_farki": 43
                                    }
                                ]
                }

@app.route('/api/logout')
def logout():
    address = request.remote_addr
    del takim_ipleri[address]
    app.logger.info("Basarili sekilde cikis yapildi.")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=1234, threaded=True, debug=True)
