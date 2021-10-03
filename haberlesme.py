from logging import getLogger
from threading import local
import requests
import asyncio
from time import sleep, time
from datetime import datetime, timedelta
from requests.compat import urljoin

from mavsdk_utils import get_gps_data

SYSTEM_START = time()
sess = requests.session()

logger = getLogger('JETSON')
logger.setLevel(-1)

def login(sunucu_url, kadi, sifre):
    data = {'kadi': kadi, 'sifre': sifre}
    resp = sess.post(urljoin(sunucu_url, '/api/giris'), json=data)
    if resp.status_code == 200:
        logger.info(" Login Olundu.")
        return int(resp.content.decode())
    elif resp.status_code == 204:
        raise Exception("Paket formati hatasi <204>")
    else:
        logger.info(resp.content) 
        raise Exception("Hata. Kod: <%d>" % (resp.status_code))

def logoff(sunucu_url):
    resp = sess.get(urljoin(sunucu_url, '/api/cikis'))
    if resp.status_code == 200:
        logger.info(" Basariyla cikis yapildi.")
    else:
        raise Exception("Cikis yapilamadi. hata kodu <%d>" % (resp.status_code))

def sunucu_saati_ogren(sunucu_url, server_saati_q):
    while True:
        sleep(0.10)
        sunucu_saati = requests.get(urljoin(sunucu_url, '/api/sunucusaati')).json()
        d = datetime.now()
        server_saati_q.put(datetime(year=d.year,
                                    month=d.month,
                                    day=d.day,
                                    hour=sunucu_saati['saat'], 
                                    minute=sunucu_saati['dakika'], 
                                    second=sunucu_saati['saniye'], 
                                    microsecond=int(sunucu_saati['milisaniye']*1000)))
                    

def telemetri_gonder_al(sunucu_url, ucak_verileri_q, rakip_ucak_verileri_q):
    while True:
        sleep(0.5)
        yeni_veri = ucak_verileri_q.get()
        try:
            alinan_ucak_verisi = sess.post(urljoin(sunucu_url, '/api/telemetri_gonder'), json=yeni_veri)
            print(alinan_ucak_verisi.content)
            if alinan_ucak_verisi.content == b'3':
                logger.warning('Çok hızlı bilgi gönderildi.')
                ucak_verileri_q.put(yeni_veri)
            else:
                alinan_ucak_verisi_json = alinan_ucak_verisi.json()
                print("ALINAN UCAK VERISI: ", alinan_ucak_verisi_json)
                rakip_ucak_verileri_q.put(alinan_ucak_verisi_json)
        except Exception as e:
            logger.error('Veri gonderilemedi ya da alinamadi. Hata:', e)
        
def kilitlenme_gonder(sunucu_url, start, end):
    # 5 snlik kilitlenme basarili olursa
    # Bu secenek gonderilmeli
    start = datetime.fromtimestamp(start)
    end = datetime.fromtimestamp(end)
    kilitlenme_verisi = {
                    "kilitlenmeBaslangicZamani": {
                    "saat": start.hour,
                    "dakika": start.minute,
                    "saniye": start.second,
                    "milisaniye": round(start.microsecond / 1000)
                    },
                    "kilitlenmeBitisZamani": {
                    "saat": end.hour,
                    "dakika": end.minute,
                    "saniye": end.second,
                    "milisaniye": round(end.microsecond / 1000)
                        },
                    "otonom_kilitlenme": 0
                    }
    sess.post(urljoin(sunucu_url, '/api/kilitlenme_bilgisi'), json=kilitlenme_verisi)

def gorev_yap(sunucu_url, dost_ucak_verileri_q, rakip_ucak_verileri_q, server_saati_q, dk_cli, mavsdk_cli, takim_numarasi):
    gorev_bitti = False
    kilitlenme = x = y = 0
    genislik = 200
    yukseklik = 100
    while True:
        start = time()
        yeni_telemetri_verisi = telemetri_oku(takim_numarasi, dk_cli, mavsdk_cli, server_saati_q, kilitlenme, x, y, genislik, yukseklik)
        dost_ucak_verileri_q.put(yeni_telemetri_verisi)
        logger.info(' Kilitlenme verisi alindi')
        kilitlenme = True #############SILINECEK
        while True: # time() - start < 5 and kilitlenme: ###################### EKLENECEK
            x, y, genislik, yukseklik, kilitlenme = telemetri_cevabi_isle(dk_cli, mavsdk_cli, rakip_ucak_verileri_q)
            yeni_telemetri_verisi = telemetri_oku(takim_numarasi, dk_cli, mavsdk_cli, server_saati_q, kilitlenme, x, y, genislik, yukseklik)
            logger.info(' Ucak verisi')
            dost_ucak_verileri_q.put(yeni_telemetri_verisi)
        end = time()
        if end - start >= 5:
            kilitlenme_gonder(sunucu_url, start, end)
            # burada yeni hedef bulunacak
        if gorev_bitti:
            break

def telemetri_oku(takim_numarasi, dk_cli, mavsdk_cli, server_saati_q, kilitlenme=0, x=0, y=0, genislik=200, yukseklik=100):
    loop = asyncio.get_event_loop()
    gps_data = loop.run_until_complete(get_gps_data(mavsdk_cli))
    position, attitude, fixedwingmetrics, battery, flightmode = loop.run_until_complete(get_all_data(mavsdk_cli))
    gps_time = datetime.fromtimestamp(SYSTEM_START + (gps_data.timestamp_us / 1e6)) # timestamp_us is in ms, fromtimestamp is in seconds float
    server_saati = server_saati_q.get()
    # server saati 'sistemSaati' keyword u ile 'yeni_veri' ye eklenebilir. server_saati datetime dir.
    yeni_veri = {
        # "serverSaati": server_saati,
        "takim_numarasi": takim_numarasi,
        "IHA_enlem": position.latitude_deg,
        "IHA_boylam": position.longitude_deg,
        "IHA_irtifa": position.relative_altitude_m,
        "IHA_dikilme": attitude.pitch_deg,
        "IHA_yonelme": attitude.yaw_deg,
        "IHA_yatis": attitude.roll_deg,
        "IHA_hiz": gps_data.velocity_m_s,
        "IHA_batarya": int(battery.remaining_percent*100),
        "IHA_otonom": 1 if flightmode != "MANUAL" else 0,
        "IHA_kilitlenme": kilitlenme, # 1 ya da 0
        "Hedef_merkez_X": x, # sol = 0
        "Hedef_merkez_Y": y,  # ust = 0
        "Hedef_genislik": genislik,  
        "Hedef_yukseklik": yukseklik,  
        "GPSSaati": {
            "saat": gps_time.hour,
            "dakika": gps_time.minute,
            "saniye": gps_time.second,
            "milisaniye": round(gps_time.microsecond / 1000)
            }
        }
    return yeni_veri

async def print_position(drone):
    """
    Default print_position command seperated and taken from telemetry.py
    :param drone:
    :return:
    """

    async for position in drone.telemetry.position():
        #print(position)
        return position
        
async def print_attitude(drone):
    """
    Default print_position command seperated and taken from telemetry.py
    :param drone:
    :return:
    """

    async for attitude in drone.telemetry.attitude_euler():
        #print(attitude)
        return attitude
async def print_fixedwing_metrics(drone):
    """
    Default print_position command seperated and taken from telemetry.py
    :param drone:
    :return:
    """

    async for fixedwing in drone.telemetry.fixedwing_metrics():
        #print(fixedwing)
        return fixedwing
async def print_battery(drone):
    """
    Default print_position command seperated and taken from telemetry.py
    :param drone:
    :return:
    """

    async for battery in drone.telemetry.battery():
        #print(battery)
        return battery
async def print_flight_mode(drone):
    """
    Default print_position command seperated and taken from telemetry.py
    :param drone:
    :return:
    """
    async for flightmode in drone.telemetry.flight_mode():
        #print(flightmode)
        return flightmode

async def get_all_data(mavsdk_cli):
    position = await print_position(mavsdk_cli)
    attitude = await print_attitude(mavsdk_cli)
    fixedwingmetrics= await print_fixedwing_metrics(mavsdk_cli)
    battery = await print_battery(mavsdk_cli)
    flightmode = await print_flight_mode(mavsdk_cli)
    return position, attitude, fixedwingmetrics, battery, flightmode

def telemetri_cevabi_isle(dk_cli, mavsdk_cli, rakip_ucak_verileri_q):
    rakip_ucak_verileri = rakip_ucak_verileri_q.get()
    logger.info('Rakip ucak verileri alindi: ' +  str(rakip_ucak_verileri))
    dk_cli # dronekit drone
    mavsdk_cli # mavsdk drone
    ##############################
    #
    #
    #
    # Buraya kodunu yaz. x, y, genislik,
    # yukseklik ve kilitlenme olup olmadigi 
    # (0, 1)
    # verileri gelecek sekilde
    #
    #
    #
    ################################
    x = y = genislik = yukseklik = kilitlenme = 1
    return x,y,genislik,yukseklik, kilitlenme
