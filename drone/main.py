from haberlesme import telemetri_gonder_al
from multiprocessing import Process, Queue
from threading import Thread
from datetime import datetime
from logging import getLogger
import asyncio

from dronekit import connect
from mavsdk import System

from mavsdk_utils import get_mavlink_connection
from haberlesme import gorev_yap, kilitlenme_gonder, sunucu_saati_ogren, login, logoff

# yarisma alaninda bu degerler girilecek
KULLANICI_ADI = 'direkoikcu'
SIFRE = 'f7y459j3dk'
sunucu_url = 'http://212.174.75.78:64559'
logger = getLogger("JETSON")
logger.setLevel(-1)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    server_saati_q = Queue(maxsize=1)
    ucak_verileri_q = Queue(maxsize=2)
    rakip_ucak_verileri_q = Queue(maxsize=2)

    takim_numarasi = login(sunucu_url, KULLANICI_ADI, SIFRE)
    logger.info(" Basarili sekilde login olundu. Takim numarasi: %d" % takim_numarasi)
    dk_cli = connect('127.0.0.1:14550', wait_ready=True)
    logger.info(" DroneKit araç baglantisi yapildi.")
    mavsdk_cli = System()
    loop.run_until_complete(get_mavlink_connection(mavsdk_cli))
    logger.info(" MavSDK baglantisi yapildi.")
    haberlesme_process = Process(target=telemetri_gonder_al, args=(sunucu_url, ucak_verileri_q, rakip_ucak_verileri_q))
    haberlesme_process.start()
    logger.info(" Haberlesme process'i basladi.")
    sunucu_saati_process = Process(target=sunucu_saati_ogren, args=(sunucu_url, server_saati_q))
    sunucu_saati_process.start()
    logger.info(" Sunucu saati process'i basladi.")
    try:
        while True:
            gorev_yap(sunucu_url, ucak_verileri_q, rakip_ucak_verileri_q, server_saati_q, dk_cli, mavsdk_cli, takim_numarasi)
            # gorev bitti
            # kondisyonu yapilip
            # ucak indirilmeli
    except KeyboardInterrupt:
        logoff(sunucu_url)