import os
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import date, timedelta

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- PROJE AYARLARI ---
DOWNLOAD_KLASORU = "Gunluk_TEIAS_Raporlari"
URL = "https://ytbsbilgi.teias.gov.tr/ytbsbilgi/frm_istatistikler.jsf"


# --- E-POSTA GÖNDERME FONKSİYONU (Değişiklik yok) ---
def eposta_gonder(dosya_yolu, dosya_adi):
    gonderen_mail = os.environ.get('GMAIL_ADDRESS')
    gonderen_sifre = os.environ.get('GMAIL_APP_PASSWORD')
    alici_mail = os.environ.get('RECIPIENT_EMAIL')

    if not all([gonderen_mail, gonderen_sifre, alici_mail]):
        print("❌ E-posta bilgileri GitHub Secrets'ta eksik!")
        return

    print(f"📬 E-posta hazırlanıyor: '{alici_mail}' adresine gönderilecek...")
    msg = MIMEMultipart()
    msg['From'] = gonderen_mail
    msg['To'] = alici_mail
    dunun_tarihi_str = (date.today() - timedelta(days=1)).strftime("%d-%m-%Y")
    msg['Subject'] = f"TEİAŞ Günlük Raporu ({dunun_tarihi_str})"
    body = f"Merhaba,\n\n{dunun_tarihi_str} tarihli TEİAŞ raporu ektedir.\n\nBu e-posta otomatik olarak gönderilmiştir."
    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(dosya_yolu, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {dosya_adi}")
        msg.attach(part)
        print(f"📎 '{dosya_adi}' dosyası e-postaya eklendi.")
    except Exception as e:
        print(f"❌ Dosya eklenirken hata oluştu: {e}")
        return

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gonderen_mail, gonderen_sifre)
        text = msg.as_string()
        server.sendmail(gonderen_mail, alici_mail, text)
        server.quit()
        print("✅ E-posta başarıyla gönderildi!")
    except Exception as e:
        print(f"❌ E-posta gönderilirken bir hata oluştu: {e}")


# --- ANA KOD BLOGU ---
def raporu_indir_ve_gonder():
    print("✅ Otomasyon başlatılıyor... (Nihai Stabil Sürüm)")
    dun = date.today() - timedelta(days=1)
    dunun_tarihi_str = dun.strftime("%d-%m-%Y")
    print(f"📅 Rapor tarihi olarak hesaplanan gün: {dunun_tarihi_str}")

    indirilecek_tam_yol = os.path.join(os.getcwd(), DOWNLOAD_KLASORU)
    if not os.path.exists(indirilecek_tam_yol):
        os.makedirs(indirilecek_tam_yol)

    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    prefs = {"download.default_directory": indirilecek_tam_yol}
    options.add_experimental_option("prefs", prefs)

    driver = None
    try:
        print("🚀 Tarayıcı hazırlanıyor...")
        # === DEĞİŞİKLİK BURADA: Kurulu Chrome'un yolunu manuel olarak belirtiyoruz ===
        # GitHub Actions'daki 'browser-actions/setup-chrome' adımı, tarayıcının yolunu
        # 'CHROME_PATH' adında bir ortam değişkenine yazar. Biz de bunu okuyoruz.
        chrome_yolu = os.environ.get('CHROME_PATH')

        if chrome_yolu:
            print(f"✔️ Chrome yolu bulundu: {chrome_yolu}")
            driver = uc.Chrome(options=options, browser_executable_path=chrome_yolu)
        else:
            print("⚠️ CHROME_PATH bulunamadı, standart yöntemle deneniyor.")
            driver = uc.Chrome(options=options)

        print("🌍 Tarayıcı başarıyla başlatıldı.")

        print(f"🔗 '{URL}' adresine gidiliyor...")
        driver.get(URL)
        wait = WebDriverWait(driver, 30)

        # "Kabul Et" butonu
        try:
            kabul_et_butonu = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[id$='btnKabul']")))
            kabul_et_butonu.click()
            time.sleep(2)
        except TimeoutException:
            pass

        # Diğer adımlar
        tarih_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[id$='bitisTarihi2_input']")))
        driver.execute_script(f"arguments[0].value='{dunun_tarihi_str}';", tarih_input)
        time.sleep(1)

        goster_butonu = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[id$='gunlukRapor']")))
        goster_butonu.click()
        time.sleep(5)

        excel_butonu = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='image'][src*='excel.png']")))
        excel_butonu.click()
        print("✔️ Rapor indirme işlemi başlatıldı.")

        print("📥 Dosyanın indirilmesi bekleniyor...")
        time.sleep(15)

        files = os.listdir(indirilecek_tam_yol)
        if files:
            indirilen_dosya_adi = sorted(files)[-1]
            indirilen_dosya_yolu = os.path.join(indirilecek_tam_yol, indirilen_dosya_adi)
            print(f"👍 Dosya başarıyla indirildi: {indirilen_dosya_adi}")
            eposta_gonder(indirilen_dosya_yolu, indirilen_dosya_adi)
        else:
            raise Exception("İndirme klasörü boş, dosya indirilemedi!")

    except Exception as e:
        print(f"❌ Rapor indirilirken bir hata oluştu: {e}")
    finally:
        if driver:
            driver.quit()
            print("✔️ Tarayıcı kapatıldı.")


if __name__ == "__main__":
    raporu_indir_ve_gonder()